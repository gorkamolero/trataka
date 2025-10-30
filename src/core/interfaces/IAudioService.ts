import type { AudioAnalysis } from "../entities/AudioAnalysis";

/**
 * Interface for audio/microphone analysis service
 */
export interface IAudioService {
  /**
   * Initialize the audio service and request microphone access
   * @returns Promise that resolves when initialization is complete
   */
  initialize(): Promise<void>;

  /**
   * Start analyzing audio input
   * @param callback Function to call when new audio analysis is available
   */
  start(callback: (analysis: AudioAnalysis) => void): void;

  /**
   * Stop analyzing audio input
   */
  stop(): void;

  /**
   * Check if microphone is available
   */
  isAvailable(): boolean;

  /**
   * Get the latest audio analysis
   */
  getLatestAnalysis(): AudioAnalysis | null;

  /**
   * Clean up audio resources
   */
  dispose(): void;
}
