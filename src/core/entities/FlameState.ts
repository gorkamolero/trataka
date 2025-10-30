/**
 * Core entity representing the current state of the flame
 */
export interface FlameState {
  /** Flame lean direction in X axis (-1 to 1, where -1 is left, 1 is right) */
  leanX: number;

  /** Flame lean direction in Z axis (-1 to 1, where -1 is back, 1 is forward) */
  leanZ: number;

  /** Overall flame intensity (0 to 1) */
  intensity: number;

  /** Flame height multiplier (0.5 to 1.5) */
  heightScale: number;

  /** Flicker speed multiplier (0.5 to 2.0) */
  flickerSpeed: number;

  /** Color temperature shift (-1 to 1, affects color gradient) */
  colorTemperature: number;
}

export const createDefaultFlameState = (): FlameState => ({
  leanX: 0,
  leanZ: 0,
  intensity: 1,
  heightScale: 1,
  flickerSpeed: 1,
  colorTemperature: 0,
});
