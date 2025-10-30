import type { SensorReading } from "../entities/SensorReading";

/**
 * Interface for device motion/orientation sensor service
 */
export interface ISensorService {
  /**
   * Initialize the sensor service
   * @returns Promise that resolves when initialization is complete
   */
  initialize(): Promise<void>;

  /**
   * Start listening to sensor events
   * @param callback Function to call when new sensor data is available
   */
  start(callback: (reading: SensorReading) => void): void;

  /**
   * Stop listening to sensor events
   */
  stop(): void;

  /**
   * Check if sensor is available on this device
   */
  isAvailable(): boolean;

  /**
   * Request necessary permissions (iOS 13+)
   * @returns Promise that resolves to permission state
   */
  requestPermission(): Promise<PermissionState>;

  /**
   * Get the latest sensor reading
   */
  getLatestReading(): SensorReading | null;
}
