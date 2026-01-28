"""
语音识别模块

基于 sherpa-onnx 的语音识别和声纹识别功能。
支持中英日韩粤语音识别，以及情感和事件检测。
"""

import json
import os
import wave
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

# 模块所在目录的父目录（backend）
_MODULE_DIR = Path(__file__).parent.parent.parent
# 模型路径配置（相对于 backend 目录）
ASR_MODEL_PATH: Optional[str] = str(_MODULE_DIR / "model/ASR/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17")
VP_MODEL_PATH: Optional[str] = str(_MODULE_DIR / "model/SpeakerID/3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx")

# 音频配置
FORMAT = "paInt16"  # PyAudio 格式（实际使用时需导入 pyaudio）
CHANNELS = 1
RATE = 16000
CHUNK = 1024

# 灵敏度配置
SILENCE_DURATION_MAP = {"高": 1, "中": 2, "低": 3}
SILENCE_DURATION: int = 2  # 默认中等灵敏度
SILENCE_CHUNKS = SILENCE_DURATION * RATE / CHUNK  # 静音持续的帧数

# 缓存路径
CACHE_PATH = "data/cache/cache_record.wav"

# 全局变量（延迟初始化）
_pyaudio_instance = None
_stream = None
_recognizer = None
_vp_extractor = None
_vp_config = None
_reference_embedding = None


def rms(data: bytes) -> float:
    """计算音频数据的均方根（Root Mean Square）"""
    return np.sqrt(np.mean(np.frombuffer(data, dtype=np.int16) ** 2))


def dbfs(rms_value: float) -> float:
    """将均方根转换为分贝满量程（dBFS）"""
    return 20 * np.log10(rms_value / (2 ** 15))  # 16位音频


def record_audio(
    mic_index: Optional[int] = None,
    silence_duration: float = SILENCE_DURATION
) -> bytes:
    """
    录音功能，通过检测静音自动停止录音。

    Args:
        mic_index: 麦克风设备索引，None 表示使用默认设备
        silence_duration: 静音持续时间（秒），超过此时间后停止录音

    Returns:
        录音数据的字节流

    Raises:
        RuntimeError: 当 PyAudio 未安装或无法打开音频设备时
    """
    global _pyaudio_instance, _stream

    try:
        import pyaudio
    except ImportError:
        raise RuntimeError("PyAudio 未安装，请先安装: pip install pyaudio")

    frames = []
    recording = True
    silence_counter = 0
    silence_chunks = silence_duration * RATE / CHUNK

    if _pyaudio_instance is None:
        _pyaudio_instance = pyaudio.PyAudio()

    if _stream is None or not _stream.is_active():
        _stream = _pyaudio_instance.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            input_device_index=mic_index
        )

    while recording:
        data = _stream.read(CHUNK)
        frames.append(data)
        current_rms = rms(data)
        current_dbfs = dbfs(current_rms)

        # 检测是否为静音
        if not np.isnan(current_dbfs) and current_dbfs < -40:  # -40dBFS 作为静音阈值
            silence_counter += 1
            if silence_counter > silence_chunks:
                recording = False
        else:
            silence_counter = 0

    return b''.join(frames)


def verify_speakers(
    reference_audio_path: str,
    target_audio_path: str,
    threshold: float = 0.85
) -> Tuple[bool, float]:
    """
    声纹识别，验证两个音频是否为同一说话人。

    Args:
        reference_audio_path: 参考音频文件路径（已注册的声纹）
        target_audio_path: 待验证音频文件路径
        threshold: 相似度阈值，默认 0.85

    Returns:
        (is_same_speaker, similarity): 是否为同一说话人及相似度分数

    Raises:
        RuntimeError: 当声纹模型未配置时
    """
    global _vp_extractor, _vp_config, _reference_embedding

    if VP_MODEL_PATH is None:
        raise RuntimeError("声纹模型未配置，请设置 VP_MODEL_PATH")

    try:
        import sherpa_onnx
        import soundfile as sf
    except ImportError:
        raise RuntimeError(" sherpa-onnx 或 soundfile 未安装，请先安装")

    def load_audio(filename: str) -> Tuple[np.ndarray, int]:
        """加载音频文件"""
        audio, sample_rate = sf.read(filename, dtype="float32", always_2d=True)
        audio = audio[:, 0]
        return audio, sample_rate

    def extract_speaker_embedding(audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """提取说话人嵌入向量"""
        if _vp_config is None:
            _vp_config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                model=VP_MODEL_PATH,
                debug=False,
                provider="cpu",
                num_threads=max(1, int(os.cpu_count()) - 1)
            )
            _vp_extractor = sherpa_onnx.SpeakerEmbeddingExtractor(_vp_config)

        vp_stream = _vp_extractor.create_stream()
        vp_stream.accept_waveform(sample_rate=sample_rate, waveform=audio)
        vp_stream.input_finished()
        embedding = _vp_extractor.compute(vp_stream)
        return np.array(embedding)

    def cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        return dot_product / (norm1 * norm2) if (norm1 * norm2) != 0 else 0.0

    # 加载并提取参考音频嵌入
    if _reference_embedding is None:
        audio1, sample_rate1 = load_audio(reference_audio_path)
        _reference_embedding = extract_speaker_embedding(audio1, sample_rate1)

    # 加载并提取目标音频嵌入
    audio2, sample_rate2 = load_audio(target_audio_path)
    embedding2 = extract_speaker_embedding(audio2, sample_rate2)

    # 计算相似度
    similarity = cosine_similarity(_reference_embedding, embedding2)

    return similarity >= threshold, similarity


def recognize_audio(
    audio_data: bytes,
    enable_voiceprint: bool = False,
    voiceprint_threshold: float = 0.85,
    reference_audio_path: Optional[str] = None
) -> str:
    """
    语音识别，将音频转换为文本。

    支持情感检测（开心、伤心、愤怒、厌恶、惊讶）和事件检测
    （鼓掌、大笑、哭、打喷嚏、咳嗽、深呼吸）。

    Args:
        audio_data: 音频数据的字节流
        enable_voiceprint: 是否启用声纹验证
        voiceprint_threshold: 声纹验证阈值
        reference_audio_path: 参考音频路径（声纹验证时使用）

    Returns:
        识别结果文本，包含情感和事件标记

    Raises:
        RuntimeError: 当 ASR 模型未配置时
    """
    global _recognizer

    if ASR_MODEL_PATH is None:
        raise RuntimeError("ASR 模型未配置，请设置 ASR_MODEL_PATH")

    try:
        import sherpa_onnx
        import soundfile as sf
    except ImportError:
        raise RuntimeError("sherpa-onnx 或 soundfile 未安装，请先安装")

    # 保存音频到缓存文件
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with wave.open(CACHE_PATH, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit = 2 bytes
        wf.setframerate(RATE)
        wf.writeframes(audio_data)

    # 检查音频时长
    with wave.open(CACHE_PATH, 'rb') as wf:
        n_frames = wf.getnframes()
        duration = n_frames / RATE

    if duration < SILENCE_DURATION + 0.5:
        return ""

    # 声纹验证
    if enable_voiceprint and reference_audio_path:
        is_verified, _ = verify_speakers(reference_audio_path, CACHE_PATH, voiceprint_threshold)
        if not is_verified:
            return ""

    # 初始化识别器
    if _recognizer is None:
        model = f"{ASR_MODEL_PATH}/model.int8.onnx"
        tokens = f"{ASR_MODEL_PATH}/tokens.txt"
        _recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=model,
            tokens=tokens,
            use_itn=True,
            num_threads=max(1, int(os.cpu_count()) - 1)
        )

    # 执行识别
    audio, sample_rate = sf.read(CACHE_PATH, dtype="float32", always_2d=True)
    asr_stream = _recognizer.create_stream()
    asr_stream.accept_waveform(sample_rate, audio[:, 0])
    _recognizer.decode_stream(asr_stream)
    result = json.loads(str(asr_stream.result))

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


def configure_models(asr_model_path: str, vp_model_path: Optional[str] = None) -> None:
    """
    配置语音识别和声纹识别模型路径。

    Args:
        asr_model_path: Sherpa-ONNX SenseVoice 模型目录路径
        vp_model_path: 声纹识别模型文件路径（可选）
    """
    global ASR_MODEL_PATH, VP_MODEL_PATH

    ASR_MODEL_PATH = asr_model_path
    VP_MODEL_PATH = vp_model_path


def cleanup() -> None:
    """清理资源，关闭音频流。"""
    global _pyaudio_instance, _stream, _recognizer, _vp_extractor

    if _stream:
        try:
            _stream.close()
        except Exception:
            pass
        _stream = None

    if _pyaudio_instance:
        try:
            _pyaudio_instance.terminate()
        except Exception:
            pass
        _pyaudio_instance = None

    _recognizer = None
    _vp_extractor = None
