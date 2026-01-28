/**
 * Voice input service for audio recording and speech recognition.
 */

import { API_ENDPOINTS } from './api';

export interface VoiceInputOptions {
  characterId?: string;
}

export interface VoiceRecognitionResult {
  text: string;
  emotion?: string;
  event?: string;
  success: boolean;
  error?: string;
}

export interface VoiceChatOptions extends VoiceInputOptions {
  conversationHistory?: Array<{ role: string; content: string }>;
  stream?: boolean;
}

/**
 * 录音控制器 - 用于手动控制录音的开始和停止
 */
export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: BlobPart[] = [];
  private stream: MediaStream | null = null;
  private startTime: number = 0;

  /**
   * 开始录音
   */
  async start(): Promise<void> {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Microphone access not supported in this browser');
    }

    // Get microphone access
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });

    // Create MediaRecorder
    const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
    this.mediaRecorder = new MediaRecorder(this.stream, { mimeType });
    this.audioChunks = [];

    // Store audio chunks
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        this.audioChunks.push(event.data);
      }
    };

    // Start recording
    this.mediaRecorder.start();
    this.startTime = Date.now();
    console.log('[ASR] 开始录音');
  }

  /**
   * 停止录音并返回音频数据
   */
  async stop(): Promise<Blob> {
    if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') {
      throw new Error('No active recording');
    }

    return new Promise((resolve) => {
      const mimeType = this.mediaRecorder!.mimeType;

      this.mediaRecorder!.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: mimeType });

        // Clean up
        if (this.stream) {
          this.stream.getTracks().forEach((track) => track.stop());
        }

        const duration = (Date.now() - this.startTime) / 1000;
        console.log(`[ASR] 停止录音，时长: ${duration.toFixed(1)}s`);

        resolve(audioBlob);
      };

      this.mediaRecorder!.stop();
    });
  }

  /**
   * 取消录音并清理资源
   */
  cancel(): void {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
    }
    this.mediaRecorder = null;
    this.audioChunks = [];
    console.log('[ASR] 取消录音');
  }
}

/**
 * Convert audio blob to WAV format.
 * Ensures 16kHz, mono, 16-bit PCM format required by the ASR model.
 *
 * @param blob - Audio blob (e.g., from MediaRecorder)
 * @returns Promise that resolves with WAV format blob
 */
export async function convertToWav(blob: Blob): Promise<Blob> {
  const arrayBuffer = await blob.arrayBuffer();
  const audioContext = new AudioContext({ sampleRate: 16000 });
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

  // Convert to 16-bit PCM
  const numberOfChannels = 1; // Force mono
  const sampleRate = 16000;
  const length = audioBuffer.length;
  const buffer = new Int16Array(length);

  // Get the first channel (or mix down to mono if stereo)
  const channelData = audioBuffer.getChannelData(0);

  for (let i = 0; i < length; i++) {
    // Convert float (-1 to 1) to int16 (-32768 to 32767)
    const s = Math.max(-1, Math.min(1, channelData[i]));
    buffer[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }

  // Create WAV file
  const wavBuffer = new ArrayBuffer(44 + buffer.length * 2);
  const view = new DataView(wavBuffer);

  // WAV header
  const writeString = (offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  writeString(0, 'RIFF');
  view.setUint32(4, 36 + buffer.length * 2, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, numberOfChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numberOfChannels * 2, true);
  view.setUint16(32, numberOfChannels * 2, true);
  view.setUint16(34, 16, true); // 16-bit
  writeString(36, 'data');
  view.setUint32(40, buffer.length * 2, true);

  // Write audio data
  for (let i = 0; i < buffer.length; i++) {
    view.setInt16(44 + i * 2, buffer[i], true);
  }

  audioContext.close();

  return new Blob([wavBuffer], { type: 'audio/wav' });
}

/**
 * Send audio to the server for speech recognition.
 *
 * @param audioBlob - Audio blob in WAV format
 * @param options - Voice input options
 * @returns Promise that resolves with recognition result
 */
export async function recognizeAudio(
  audioBlob: Blob,
  options: VoiceInputOptions = {}
): Promise<VoiceRecognitionResult> {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'audio.wav');
  formData.append('character_id', options.characterId || 'sister_001');

  try {
    const response = await fetch(API_ENDPOINTS.voiceInput(), {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Error: ${response.status} - ${errorText}`);
    }

    return await response.json();
  } catch (error) {
    return {
      text: '',
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}

/**
 * 从音频 Blob 识别文本（录音完成后的识别流程）
 */
export async function recognizeFromBlob(
  audioBlob: Blob,
  options: VoiceInputOptions = {}
): Promise<VoiceRecognitionResult> {
  const totalTimeStart = performance.now();
  const timings: { [key: string]: number } = {};

  try {
    // Convert to WAV
    const convertStart = performance.now();
    const wavBlob = await convertToWav(audioBlob);
    timings.convert = performance.now() - convertStart;
    console.log(`[ASR] WAV转换: ${(timings.convert).toFixed(0)}ms, 文件大小: ${(wavBlob.size / 1024).toFixed(1)}KB`);

    // Recognize
    const recognizeStart = performance.now();
    const result = await recognizeAudio(wavBlob, options);
    timings.recognize = performance.now() - recognizeStart;
    timings.total = performance.now() - totalTimeStart;

    console.log(`[ASR] 识别完成: ${(timings.recognize).toFixed(0)}ms`);
    console.log(`[ASR] 总耗时: ${(timings.total).toFixed(0)}ms (转换: ${(timings.convert).toFixed(0)}ms, 识别: ${(timings.recognize).toFixed(0)}ms)`);

    return result;
  } catch (error) {
    timings.total = performance.now() - totalTimeStart;
    console.error(`[ASR] 失败: ${(timings.total).toFixed(0)}ms`, error);
    return {
      text: '',
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
