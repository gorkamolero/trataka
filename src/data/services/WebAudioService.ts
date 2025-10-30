import type { IAudioService } from "../../core/interfaces/IAudioService";
import type { AudioAnalysis } from "../../core/entities/AudioAnalysis";
import { createDefaultAudioAnalysis } from "../../core/entities/AudioAnalysis";
import { clamp } from "../../utils/math";

/**
 * Service for analyzing microphone input using Web Audio API
 * Focuses on breath detection (low frequencies 10-140Hz)
 */
export class WebAudioService implements IAudioService {
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private mediaStream: MediaStream | null = null;
  private source: MediaStreamAudioSourceNode | null = null;
  private callback: ((analysis: AudioAnalysis) => void) | null = null;
  private latestAnalysis: AudioAnalysis = createDefaultAudioAnalysis();
  private animationFrameId: number | null = null;
  private frequencyData: Uint8Array<ArrayBuffer> | null = null;

  private readonly FFT_SIZE = 256; // Low latency, good for breath detection
  private readonly SMOOTHING = 0.8;
  private readonly BREATH_FREQ_MIN = 10; // Hz
  private readonly BREATH_FREQ_MAX = 140; // Hz

  async initialize(): Promise<void> {
    if (!this.isAvailable()) {
      throw new Error("Web Audio API is not supported on this device");
    }

    try {
      // Request microphone access with optimal settings for breath detection
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false, // We want raw audio
          noiseSuppression: false, // We want to detect breath
          autoGainControl: false, // We want consistent levels
        },
      });

      // Create audio context
      this.audioContext = new (window.AudioContext ||
        (window as any).webkitAudioContext)();

      // Create analyser node
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = this.FFT_SIZE;
      this.analyser.smoothingTimeConstant = this.SMOOTHING;

      // Connect microphone to analyser
      this.source = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.source.connect(this.analyser);

      // Create frequency data array
      this.frequencyData = new Uint8Array(this.analyser.frequencyBinCount);

      console.log("WebAudioService initialized successfully");
    } catch (error) {
      console.error("Failed to initialize WebAudioService:", error);
      throw error;
    }
  }

  isAvailable(): boolean {
    return (
      typeof window !== "undefined" &&
      !!(window.AudioContext || (window as any).webkitAudioContext) &&
      !!navigator.mediaDevices?.getUserMedia
    );
  }

  start(callback: (analysis: AudioAnalysis) => void): void {
    if (!this.analyser || !this.frequencyData) {
      console.error(
        "WebAudioService not initialized. Call initialize() first.",
      );
      return;
    }

    this.callback = callback;
    this.analyzeAudio();
  }

  stop(): void {
    if (this.animationFrameId !== null) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    this.callback = null;
  }

  getLatestAnalysis(): AudioAnalysis | null {
    return this.latestAnalysis;
  }

  dispose(): void {
    this.stop();

    // Disconnect and cleanup audio nodes
    if (this.source) {
      this.source.disconnect();
      this.source = null;
    }

    if (this.analyser) {
      this.analyser.disconnect();
      this.analyser = null;
    }

    // Stop all tracks in the media stream
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    // Close audio context
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    this.frequencyData = null;
    console.log("WebAudioService disposed");
  }

  private analyzeAudio = (): void => {
    if (!this.analyser || !this.frequencyData) return;

    // Get frequency data
    this.analyser.getByteFrequencyData(this.frequencyData);

    // Calculate sample rate and frequency per bin
    const sampleRate = this.audioContext?.sampleRate ?? 44100;
    const frequencyPerBin = sampleRate / this.FFT_SIZE;

    // Find breath frequency range bins
    const minBin = Math.floor(this.BREATH_FREQ_MIN / frequencyPerBin);
    const maxBin = Math.floor(this.BREATH_FREQ_MAX / frequencyPerBin);

    // Calculate breath intensity (average of low frequencies)
    let breathSum = 0;
    let breathCount = 0;
    for (let i = minBin; i <= maxBin && i < this.frequencyData.length; i++) {
      breathSum += this.frequencyData[i];
      breathCount++;
    }
    const breathIntensity =
      breathCount > 0 ? breathSum / (breathCount * 255) : 0;

    // Calculate overall volume (RMS of all frequencies)
    let volumeSum = 0;
    for (let i = 0; i < this.frequencyData.length; i++) {
      volumeSum += this.frequencyData[i];
    }
    const volume = volumeSum / (this.frequencyData.length * 255);

    // Find peak frequency
    let peakValue = 0;
    let peakBin = 0;
    for (let i = 0; i < this.frequencyData.length; i++) {
      if (this.frequencyData[i] > peakValue) {
        peakValue = this.frequencyData[i];
        peakBin = i;
      }
    }
    const peakFrequency = peakBin * frequencyPerBin;

    // Create analysis result
    this.latestAnalysis = {
      breathIntensity: clamp(breathIntensity, 0, 1),
      volume: clamp(volume, 0, 1),
      peakFrequency,
      timestamp: Date.now(),
    };

    // Notify callback only if there's meaningful change (threshold)
    if (this.callback && (breathIntensity > 0.01 || volume > 0.01)) {
      this.callback(this.latestAnalysis);
    }

    // Continue analyzing
    this.animationFrameId = requestAnimationFrame(this.analyzeAudio);
  };

  /**
   * Convert audio analysis to flame height and flicker parameters
   */
  static toFlameParams(analysis: AudioAnalysis): {
    heightScale: number;
    flickerSpeed: number;
    colorTemperature: number;
  } {
    // Map breath intensity to flame height (0.7 to 1.3 range)
    const heightScale = 0.7 + analysis.breathIntensity * 0.6;

    // Map volume peaks to flicker speed (0.8 to 2.0 range)
    const flickerSpeed = 0.8 + analysis.volume * 1.2;

    // Map volume to color temperature shift (-0.2 to 0.2)
    const colorTemperature = (analysis.volume - 0.5) * 0.4;

    return {
      heightScale: clamp(heightScale, 0.5, 1.5),
      flickerSpeed: clamp(flickerSpeed, 0.5, 2.0),
      colorTemperature: clamp(colorTemperature, -1, 1),
    };
  }
}
