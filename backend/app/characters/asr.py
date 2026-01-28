"""
语音识别模块

基于 sherpa-onnx 的语音识别功能。
支持中英日韩粤语音识别，以及情感和事件检测。
"""

import json
import os
import wave
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 模块所在目录的父目录（backend）
_MODULE_DIR = Path(__file__).parent.parent.parent
# 模型路径配置（相对于 backend 目录）
ASR_MODEL_PATH: Optional[str] = str(_MODULE_DIR / "model/ASR/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17")

# 音频配置
CHANNELS = 1
RATE = 16000

# 缓存路径
CACHE_PATH = "data/cache/cache_record.wav"

# 全局变量（延迟初始化）
_recognizer = None


def recognize_audio(audio_data: bytes) -> str:
    """
    语音识别，将音频转换为文本。

    支持情感检测（开心、伤心、愤怒、厌恶、惊讶）和事件检测
    （鼓掌、大笑、哭、打喷嚏、咳嗽、深呼吸）。

    Args:
        audio_data: 音频数据的字节流

    Returns:
        识别结果文本，包含情感和事件标记

    Raises:
        RuntimeError: 当 ASR 模型未配置时
    """
    global _recognizer
    total_start = time.time()

    if ASR_MODEL_PATH is None:
        raise RuntimeError("ASR 模型未配置，请设置 ASR_MODEL_PATH")

    try:
        import sherpa_onnx
        import soundfile as sf
    except ImportError:
        raise RuntimeError("sherpa-onnx 或 soundfile 未安装，请先安装")

    # 保存音频到缓存文件
    write_start = time.time()
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with wave.open(CACHE_PATH, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(RATE)
        wf.writeframes(audio_data)
    write_time = (time.time() - write_start) * 1000

    # 检查音频时长
    check_start = time.time()
    with wave.open(CACHE_PATH, 'rb') as wf:
        n_frames = wf.getnframes()
        duration = n_frames / RATE
    check_time = (time.time() - check_start) * 1000

    logger.info(f"[ASR] 写入文件: {write_time:.0f}ms, 检查时长: {check_time:.0f}ms, 音频时长: {duration:.1f}s")

    # 降低最小时长限制，支持短语识别
    if duration < 0.3:
        logger.info(f"[ASR] 音频太短（<0.3s），跳过识别")
        return ""

    # 初始化识别器
    if _recognizer is None:
        init_start = time.time()
        model = f"{ASR_MODEL_PATH}/model.int8.onnx"
        tokens = f"{ASR_MODEL_PATH}/tokens.txt"
        _recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=model,
            tokens=tokens,
            use_itn=True,
            num_threads=max(1, int(os.cpu_count()) - 1)
        )
        init_time = (time.time() - init_start) * 1000
        logger.info(f"[ASR] 模型初始化: {init_time:.0f}ms")

    # 执行识别
    infer_start = time.time()
    audio, sample_rate = sf.read(CACHE_PATH, dtype="float32", always_2d=True)
    asr_stream = _recognizer.create_stream()
    asr_stream.accept_waveform(sample_rate, audio[:, 0])
    _recognizer.decode_stream(asr_stream)
    result = json.loads(str(asr_stream.result))
    infer_time = (time.time() - infer_start) * 1000

    total_time = (time.time() - total_start) * 1000
    logger.info(f"[ASR] 读取音频+推理: {infer_time:.0f}ms, 总耗时: {total_time:.0f}ms")

    # 解析结果
    emotion_key = result.get('emotion', '').strip('<|>')
    event_key = result.get('event', '').strip('<|>')
    text = result.get('text', '')

    # 情感映射
    emotion_dict = {
        "HAPPY": "[开心]",
        "SAD": "[伤心]",
        "ANGRY": "[愤怒]",
        "DISGUSTED": "[厌恶]",
        "SURPRISED": "[惊讶]",
        "NEUTRAL": "",
        "EMO_UNKNOWN": ""
    }

    # 事件映射
    event_dict = {
        "BGM": "",
        "Applause": "[鼓掌]",
        "Laughter": "[大笑]",
        "Cry": "[哭]",
        "Sneeze": "[打喷嚏]",
        "Cough": "[咳嗽]",
        "Breath": "[深呼吸]",
        "Speech": "",
        "Event_UNK": ""
    }

    emotion = emotion_dict.get(emotion_key, "")
    event = event_dict.get(event_key, "")
    result_text = event + text + emotion

    # 过滤无效结果
    if result_text in ("The.", ""):
        return ""

    return result_text


def configure_models(asr_model_path: str) -> None:
    """
    配置语音识别模型路径。

    Args:
        asr_model_path: Sherpa-ONNX SenseVoice 模型目录路径
    """
    global ASR_MODEL_PATH, _recognizer

    ASR_MODEL_PATH = asr_model_path
    _recognizer = None  # 重置识别器以使用新模型


def cleanup() -> None:
    """清理资源。"""
    global _recognizer
    _recognizer = None
