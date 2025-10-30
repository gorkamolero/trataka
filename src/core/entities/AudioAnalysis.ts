/**
 * Core entity representing analyzed audio data from microphone
 */
export interface AudioAnalysis {
  /** Breath intensity (0 to 1, focused on low frequencies 10-140Hz) */
  breathIntensity: number;

  /** Overall volume level (0 to 1) */
  volume: number;

  /** Peak frequency detected in Hz */
  peakFrequency: number;

  /** Timestamp of the analysis */
  timestamp: number;
}

export const createDefaultAudioAnalysis = (): AudioAnalysis => ({
  breathIntensity: 0,
  volume: 0,
  peakFrequency: 0,
  timestamp: Date.now(),
});
