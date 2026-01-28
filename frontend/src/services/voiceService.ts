/**
 * Voice input service for audio recording and speech recognition.
 */

import { API_ENDPOINTS } from './api';

export interface VoiceInputOptions {
  characterId?: string;
  enableVoiceprint?: boolean;
  voiceprintThreshold?: number;
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
 * Record audio from the microphone using MediaRecorder API.
 * Automatically stops recording after silence is detected.
 *
 * @param maxDuration - Maximum recording duration in seconds (default: 30)
 * @param silenceDuration - Silence duration before auto-stop in seconds (default: 2.0)
 * @returns Promise that resolves with the audio blob
 */
export async function recordAudio(
  maxDuration: number = 30,
  silenceDuration: number = 2.0
): Promise<Blob> {
  return new Promise((resolve, reject) => {
    // Check if MediaRecorder is supported
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      reject(new Error('Microphone access not supported in this browser'));
      return;
    }

    let mediaRecorder: MediaRecorder | null = null;
    let audioChunks: BlobPart[] = [];
    let silenceStart: number | null = null;
    let audioContext: AudioContext | null = null;
    let analyser: AnalyserNode | null = null;
    let microphone: MediaStreamAudioSourceNode | null = null;
    let animationId: number | null = null;

    // Silence detection threshold (dB)
    const SILENCE_THRESHOLD = -40;
    const SAMPLE_RATE = 16000;

    async function startRecording() {
      try {
        // Get microphone access
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,
            sampleRate: SAMPLE_RATE,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });

        // Create audio context for silence detection
        audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        microphone = audioContext.createMediaStreamSource(stream);
        microphone.connect(analyser);

        // Create MediaRecorder
        const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
        mediaRecorder = new MediaRecorder(stream, { mimeType });

        // Store audio chunks
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunks.push(event.data);
          }
        };

        // Handle recording stop
        mediaRecorder.onstop = () => {
          const audioBlob = new Blob(audioChunks, { type: mimeType });

          // Clean up
          if (animationId !== null) {
            cancelAnimationFrame(animationId);
          }
          if (microphone) {
            microphone.disconnect();
          }
          if (audioContext && audioContext.state !== 'closed') {
            audioContext.close();
          }
          stream.getTracks().forEach((track) => track.stop());

          resolve(audioBlob);
        };

        // Start recording
        mediaRecorder.start();
        const startTime = Date.now();

        // Monitor audio level for silence detection
        const dataArray = new Uint8Array(analyser.frequencyBinCount);

        function detectSilence() {
          if (!mediaRecorder || mediaRecorder.state === 'inactive') {
            return;
          }

          analyser!.getByteFrequencyData(dataArray);

          // Calculate average volume
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const average = sum / dataArray.length;

          // Convert to dB
          const db = 20 * Math.log10(average / 255);

          // Check for silence
          if (db < SILENCE_THRESHOLD) {
            if (silenceStart === null) {
              silenceStart = Date.now();
            } else if (Date.now() - silenceStart > silenceDuration * 1000) {
              // Silence detected for long enough, stop recording
              mediaRecorder.stop();
              return;
            }
          } else {
            silenceStart = null;
          }

          // Check for max duration
          if (Date.now() - startTime > maxDuration * 1000) {
            mediaRecorder.stop();
            return;
          }

          animationId = requestAnimationFrame(detectSilence);
        }

        detectSilence();

      } catch (error) {
        reject(error);
      }
    }

    startRecording();
  });
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
  formData.append('enable_voiceprint', String(options.enableVoiceprint || false));
  formData.append('voiceprint_threshold', String(options.voiceprintThreshold || 0.85));

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
 * Record audio and get character response in one call.
 *
 * @param options - Voice chat options
 * @param maxDuration - Maximum recording duration in seconds
 * @returns Promise that resolves with character response
 */
export async function voiceChat(
  options: VoiceChatOptions = {},
  maxDuration: number = 30
): Promise<Response> {
  // Record audio
  const audioBlob = await recordAudio(maxDuration);
  const wavBlob = await convertToWav(audioBlob);

  // Send to server
  const formData = new FormData();
  formData.append('audio', wavBlob, 'audio.wav');
  formData.append('character_id', options.characterId || 'sister_001');
  formData.append('stream', String(options.stream || false));

  if (options.conversationHistory) {
    formData.append('conversation_history', JSON.stringify(options.conversationHistory));
  }

  const response = await fetch(API_ENDPOINTS.voiceChat(), {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error: ${response.status} - ${errorText}`);
  }

  return response;
}

/**
 * Complete voice input workflow: record, convert, and recognize.
 *
 * @param options - Voice input options
 * @param maxDuration - Maximum recording duration in seconds
 * @returns Promise that resolves with recognition result
 */
export async function voiceToText(
  options: VoiceInputOptions = {},
  maxDuration: number = 30
): Promise<VoiceRecognitionResult> {
  try {
    // Record audio
    const audioBlob = await recordAudio(maxDuration);

    // Convert to WAV
    const wavBlob = await convertToWav(audioBlob);

    // Recognize
    return await recognizeAudio(wavBlob, options);
  } catch (error) {
    return {
      text: '',
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
