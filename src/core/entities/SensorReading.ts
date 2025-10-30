/**
 * Core entity representing device orientation sensor data
 */
export interface SensorReading {
  /** Device tilt left/right in degrees (-180 to 180) */
  beta: number;

  /** Device tilt forward/back in degrees (-90 to 90) */
  gamma: number;

  /** Compass heading in degrees (0 to 360) */
  alpha: number;

  /** Timestamp of the reading */
  timestamp: number;
}

export const createDefaultSensorReading = (): SensorReading => ({
  beta: 0,
  gamma: 0,
  alpha: 0,
  timestamp: Date.now(),
});
