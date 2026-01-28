"""
语音合成模块

基于 sherpa-onnx 和 pyttsx3 的文本转语音功能。
支持 VITS 本地模型和系统自带 TTS。
"""

import glob
import os
import re
from pathlib import Path
from typing import Optional

# 模块所在目录的父目录（backend）
_MODULE_DIR = Path(__file__).parent.parent.parent
# 模型路径配置（相对于 backend 目录）
VITS_MODEL_PATH: Optional[str] = str(_MODULE_DIR / "model/TTS/vits-zh-hf-bronya")

# 音频配置
SAMPLE_RATE = 22050
CHANNELS = 1

# 缓存路径
VOICE_CACHE_DIR = "data/cache"
VOICE_CACHE_PATH = os.path.join(VOICE_CACHE_DIR, "cache_voice.wav")

# VITS 模型配置
NUM_THREADS = max(1, int(os.cpu_count()) - 1)

# 全局变量（延迟初始化）
_vits_tts = None
_vits_config = None
_pyttsx3_engine = None

# 播放控制标志
_play_tts_flag = 0


def _preprocess_text(text: str) -> str:
    """
    预处理文本，移除不适合朗读的符号和内容。

    Args:
        text: 原始文本

    Returns:
        处理后的文本
    """
    # 移除 Markdown 标记
    text = text.replace("#", "").replace("*", "")

    # 移除括号内的内容（包括中文和英文括号）
    text = re.sub(r'[(（].*?[)）]', '', text)

    # 移除多余的空白字符
    text = text.strip()

    return text


def _split_text(text: str) -> list[str]:
    """
    将文本按标点符号分割成多个片段。

    Args:
        text: 输入文本

    Returns:
        文本片段列表
    """
    segments = re.split(r'([\n:：!！?？;；。])', text)
    combined = []
    for i in range(0, len(segments), 2):
        if i + 1 < len(segments):
            combined.append(segments[i] + segments[i + 1])
        elif segments[i].strip():
            combined.append(segments[i])
    return [seg.strip() for seg in combined if seg.strip()]


def _init_vits_model() -> None:
    """初始化 VITS 模型。"""
    global _vits_tts, _vits_config

    if VITS_MODEL_PATH is None or not os.path.exists(VITS_MODEL_PATH):
        raise RuntimeError(f"VITS 模型路径不存在: {VITS_MODEL_PATH}")

    try:
        import sherpa_onnx
    except ImportError:
        raise RuntimeError("sherpa-onnx 未安装，请先安装: pip install sherpa-onnx")

    # 查找模型文件
    model_files = glob.glob(os.path.join(VITS_MODEL_PATH, "*.onnx"))
    if not model_files:
        raise RuntimeError(f"在 {VITS_MODEL_PATH} 中未找到 .onnx 模型文件")

    vits_model_path = model_files[0]
    vits_tokens_path = os.path.join(VITS_MODEL_PATH, "tokens.txt")
    vits_lexicon_path = os.path.join(VITS_MODEL_PATH, "lexicon.txt")
    vits_dict_dir = os.path.join(VITS_MODEL_PATH, "dict")

    # 检查必要文件是否存在
    if not os.path.exists(vits_tokens_path):
        raise RuntimeError(f"tokens.txt 不存在于 {VITS_MODEL_PATH}")

    # 创建配置
    _vits_config = sherpa_onnx.OfflineTtsConfig(
        model=sherpa_onnx.OfflineTtsModelConfig(
            vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                model=vits_model_path,
                lexicon=vits_lexicon_path if os.path.exists(vits_lexicon_path) else "",
                tokens=vits_tokens_path,
                dict_dir=vits_dict_dir if os.path.exists(vits_dict_dir) else ""
            ),
            provider="cpu",
            num_threads=NUM_THREADS
        )
    )

    # 创建 TTS 实例
    _vits_tts = sherpa_onnx.OfflineTts(_vits_config)


def _init_pyttsx3_engine() -> None:
    """初始化 pyttsx3 引擎。"""
    global _pyttsx3_engine

    try:
        import pyttsx3
        _pyttsx3_engine = pyttsx3.init()
    except ImportError:
        raise RuntimeError("pyttsx3 未安装，请先安装: pip install pyttsx3")
    except Exception as e:
        raise RuntimeError(f"pyttsx3 初始化失败: {e}")


def synthesize_vits(text: str, output_path: Optional[str] = None) -> str:
    """
    使用 VITS 模型进行语音合成。

    Args:
        text: 要合成的文本
        output_path: 输出音频文件路径，None 则使用默认缓存路径

    Returns:
        生成的音频文件路径

    Raises:
        RuntimeError: 当 VITS 模型未配置或初始化失败时
    """
    global _vits_tts

    if _vits_tts is None:
        _init_vits_model()

    try:
        import soundfile as sf
        import numpy as np
    except ImportError:
        raise RuntimeError("soundfile 或 numpy 未安装，请先安装: pip install soundfile numpy")

    # 预处理文本
    processed_text = _preprocess_text(text)
    if not processed_text:
        return ""

    # 生成音频
    audio = _vits_tts.generate(processed_text, sid=0, speed=1.0)

    # 设置输出路径
    if output_path is None:
        os.makedirs(VOICE_CACHE_DIR, exist_ok=True)
        output_path = VOICE_CACHE_PATH

    # 保存音频
    samples = np.array(audio.samples, dtype=np.float32)

    # 对特定模型进行音量放大
    if "sherpa-onnx-vits-zh-ll" in VITS_MODEL_PATH:
        amplified_samples = samples * 4  # 音量放大4倍
        amplified_samples = np.clip(amplified_samples, -1.0, 1.0)
        samples_int16 = (amplified_samples * 32767).astype(np.int16)
    else:
        samples_int16 = (samples * 32767).astype(np.int16)

    sf.write(output_path, samples_int16, samplerate=audio.sample_rate, subtype="PCM_16", format="wav")

    return output_path


def synthesize_pyttsx3(text: str, output_path: Optional[str] = None) -> str:
    """
    使用 pyttsx3 进行语音合成。

    Args:
        text: 要合成的文本
        output_path: 输出音频文件路径，None 则使用默认缓存路径

    Returns:
        生成的音频文件路径

    Raises:
        RuntimeError: 当 pyttsx3 初始化失败时
    """
    global _pyttsx3_engine

    if _pyttsx3_engine is None:
        _init_pyttsx3_engine()

    # 预处理文本
    processed_text = _preprocess_text(text)
    if not processed_text:
        return ""

    # 设置输出路径
    if output_path is None:
        os.makedirs(VOICE_CACHE_DIR, exist_ok=True)
        output_path = VOICE_CACHE_PATH

    # 保存音频
    _pyttsx3_engine.save_to_file(processed_text, output_path)
    _pyttsx3_engine.runAndWait()

    return output_path


def synthesize(
    text: str,
    engine: str = "vits",
    output_path: Optional[str] = None,
    split_sentences: bool = False
) -> str:
    """
    文本转语音合成。

    Args:
        text: 要合成的文本
        engine: TTS 引擎，支持 "vits" 或 "pyttsx3"
        output_path: 输出音频文件路径，None 则使用默认缓存路径
        split_sentences: 是否按标点符号分割文本（VITS 模式下有效）

    Returns:
        生成的音频文件路径，如果文本为空则返回空字符串

    Raises:
        RuntimeError: 当模型未配置或初始化失败时
        ValueError: 当指定的引擎不支持时
    """
    global _play_tts_flag
    _play_tts_flag = 1

    # 预处理文本
    processed_text = _preprocess_text(text)
    if not processed_text:
        return ""

    if engine == "vits":
        if split_sentences:
            # 分割文本并逐段合成
            segments = _split_text(processed_text)
            if not segments:
                segments = [processed_text]
            # 这里只返回最后一段的路径，实际应用可能需要合并音频
            for segment in segments:
                if _play_tts_flag == 0:
                    break
                synthesize_vits(segment, output_path)
            return output_path or VOICE_CACHE_PATH
        else:
            return synthesize_vits(processed_text, output_path)

    elif engine == "pyttsx3":
        return synthesize_pyttsx3(processed_text, output_path)

    else:
        raise ValueError(f"不支持的 TTS 引擎: {engine}，仅支持 'vits' 或 'pyttsx3'")


def stop_synthesis() -> None:
    """停止当前的语音合成任务。"""
    global _play_tts_flag
    _play_tts_flag = 0


def configure_models(vits_model_path: Optional[str] = None) -> None:
    """
    配置 TTS 模型路径。

    Args:
        vits_model_path: VITS 模型目录路径（可选）
    """
    global VITS_MODEL_PATH, _vits_tts, _vits_config

    if vits_model_path is not None:
        VITS_MODEL_PATH = vits_model_path

    # 重置已初始化的模型
    _vits_tts = None
    _vits_config = None


def cleanup() -> None:
    """清理资源。"""
    global _vits_tts, _vits_config, _pyttsx3_engine

    _vits_tts = None
    _vits_config = None

    if _pyttsx3_engine:
        try:
            _pyttsx3_engine.stop()
        except Exception:
            pass
        _pyttsx3_engine = None
