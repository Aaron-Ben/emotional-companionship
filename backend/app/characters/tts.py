"""
语音合成模块

基于 Genie-TTS (GPT-SoVITS ONNX) 的文本转语音功能。
支持中英日韩语音合成。
"""

import os
import re
from pathlib import Path
from typing import Optional

# 模块所在目录的父目录（backend）
_MODULE_DIR = Path(__file__).parent.parent.parent

# 缓存路径
VOICE_CACHE_DIR = "data/cache"
VOICE_CACHE_PATH = os.path.join(VOICE_CACHE_DIR, "cache_voice.wav")

# Genie-TTS 配置
GENIE_DATA_DIR: Optional[str] = str(_MODULE_DIR / "model/GenieData")

# 当前加载的角色
_loaded_characters = set()

# 导出常量
__all__ = [
    "synthesize",
    "load_character",
    "load_predefined_character",
    "get_available_characters",
    "configure_models",
    "cleanup",
    "DEFAULT_CHARACTER",
    "GENIE_DATA_DIR",
    "VOICE_CACHE_PATH",
]

# 默认角色配置
DEFAULT_CHARACTER = "feibi"  # 菲比 - 中文角色


def _init_genie():
    """初始化 Genie-TTS，设置资源目录。"""
    if GENIE_DATA_DIR and os.path.exists(GENIE_DATA_DIR):
        os.environ["GENIE_DATA_DIR"] = GENIE_DATA_DIR


def load_character(
    character_name: str,
    onnx_model_dir: Optional[str] = None,
    language: str = "zh"
) -> None:
    """
    加载角色语音模型。

    Args:
        character_name: 角色名称
        onnx_model_dir: ONNX 模型目录路径（如果使用自定义模型）
        language: 语言代码 ('zh', 'en', 'jp', 'ko')

    Raises:
        RuntimeError: 当 Genie-TTS 未安装或加载失败时
    """
    global _loaded_characters

    _init_genie()

    try:
        import genie_tts as genie
    except ImportError:
        raise RuntimeError("genie-tts 未安装，请先安装: pip install genie-tts")

    try:
        if onnx_model_dir:
            # 加载自定义模型
            genie.load_character(
                character_name=character_name,
                onnx_model_dir=onnx_model_dir,
                language=language
            )
        else:
            # 加载预定义角色
            genie.load_predefined_character(character_name)

        _loaded_characters.add(character_name)
    except Exception as e:
        raise RuntimeError(f"加载角色模型失败: {e}")


def synthesize(
    text: str,
    character_name: str = DEFAULT_CHARACTER,
    output_path: Optional[str] = None,
    reference_audio: Optional[str] = None,
    reference_text: Optional[str] = None,
    language: str = "zh",
    engine: str = "genie"
) -> str:
    """
    文本转语音合成。

    Args:
        text: 要合成的文本
        character_name: 角色名称
        output_path: 输出音频文件路径，None 则使用默认缓存路径
        reference_audio: 参考音频路径（用于情感和语调克隆）
        reference_text: 参考音频对应的文本
        language: 语言代码
        engine: TTS 引擎，目前仅支持 "genie"

    Returns:
        生成的音频文件路径

    Raises:
        RuntimeError: 当模型未加载或合成失败时
        ValueError: 当指定的引擎不支持时
    """
    _init_genie()

    if engine != "genie":
        raise ValueError(f"不支持的 TTS 引擎: {engine}，目前仅支持 'genie'")

    try:
        import genie_tts as genie
    except ImportError:
        raise RuntimeError("genie-tts 未安装，请先安装: pip install genie-tts")

    # 预处理文本
    processed_text = _preprocess_text(text)
    if not processed_text:
        return ""

    # 设置输出路径
    if output_path is None:
        os.makedirs(VOICE_CACHE_DIR, exist_ok=True)
        output_path = VOICE_CACHE_PATH

    # 确保角色已加载
    if character_name not in _loaded_characters:
        load_character(character_name, language=language)

    # 设置参考音频（如果提供）
    if reference_audio and reference_text:
        genie.set_reference_audio(
            character_name=character_name,
            audio_path=reference_audio,
            audio_text=reference_text
        )

    # 执行合成
    try:
        genie.tts(
            character_name=character_name,
            text=processed_text,
            save_path=output_path,
            play=False
        )
    except Exception as e:
        raise RuntimeError(f"TTS 合成失败: {e}")

    return output_path


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


def load_predefined_character(character_name: str) -> None:
    """
    加载预定义角色。

    可用的预定义角色：
    - mika: 聖園ミカ (Blue Archive) - 日语
    - 37: ThirtySeven (Reverse: 1999) - 英语
    - feibi: 菲比 (Wuthering Waves) - 中文

    Args:
        character_name: 预定义角色名称

    Raises:
        RuntimeError: 当加载失败时
    """
    load_character(character_name)


def get_available_characters() -> list[str]:
    """
    获取可用的预定义角色列表。

    Returns:
        预定义角色名称列表
    """
    return ["mika", "37", "feibi"]


def configure_models(genie_data_dir: Optional[str] = None) -> None:
    """
    配置 Genie-TTS 资源目录。

    Args:
        genie_data_dir: GenieData 目录路径（可选）
    """
    global GENIE_DATA_DIR, _loaded_characters

    if genie_data_dir is not None:
        GENIE_DATA_DIR = genie_data_dir

    # 重置已加载的角色
    _loaded_characters = set()


def cleanup() -> None:
    """清理资源。"""
    global _loaded_characters

    _loaded_characters = set()
    # Genie-TTS 会自动管理资源
