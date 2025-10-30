import type { ISensorService } from "../../core/interfaces/ISensorService";
import type { SensorReading } from "../../core/entities/SensorReading";
import { createDefaultSensorReading } from "../../core/entities/SensorReading";
import { normalize, clamp, applyDeadZone, lerp } from "../../utils/math";

/**
 * Service for handling device orientation/motion sensors
 * Supports iOS 13+ permission model
 */
export class MotionSensorService implements ISensorService {
  private callback: ((reading: SensorReading) => void) | null = null;
  private latestReading: SensorReading = createDefaultSensorReading();
  private smoothedReading: SensorReading = createDefaultSensorReading();
  private isListening = false;
  private readonly DEAD_ZONE = 5; // degrees
  private readonly LERP_FACTOR = 0.15; // smooth interpolation
  private eventCount = 0;

  async initialize(): Promise<void> {
    // Check if DeviceOrientationEvent is available
    if (!this.isAvailable()) {
      throw new Error("DeviceOrientationEvent is not supported on this device");
    }
  }

  isAvailable(): boolean {
    return typeof DeviceOrientationEvent !== "undefined";
  }

  async requestPermission(): Promise<PermissionState> {
    // iOS 13+ requires explicit permission
    if (
      typeof DeviceOrientationEvent !== "undefined" &&
      typeof (DeviceOrientationEvent as any).requestPermission === "function"
    ) {
      try {
        const permission = await (
          DeviceOrientationEvent as any
        ).requestPermission();
        return permission === "granted" ? "granted" : "denied";
      } catch (error) {
        console.error("Error requesting device orientation permission:", error);
        return "denied";
      }
    }

    // Non-iOS devices don't require permission
    return "granted";
  }

  start(callback: (reading: SensorReading) => void): void {
    if (this.isListening) {
      console.warn("MotionSensorService is already listening");
      return;
    }

    this.callback = callback;
    this.isListening = true;

    window.addEventListener("deviceorientation", this.handleOrientation);
  }

  stop(): void {
    if (!this.isListening) return;

    this.isListening = false;
    this.callback = null;
    window.removeEventListener("deviceorientation", this.handleOrientation);
  }

  getLatestReading(): SensorReading | null {
    return this.smoothedReading;
  }

  private handleOrientation = (event: DeviceOrientationEvent): void => {
    this.eventCount++;

    // Extract orientation data
    const alpha = event.alpha ?? 0;
    const beta = event.beta ?? 0;
    const gamma = event.gamma ?? 0;

    // Log every 30 events to avoid spam
    if (this.eventCount % 30 === 0) {
      console.log(
        `Motion events: ${this.eventCount}, α=${alpha.toFixed(1)}° β=${beta.toFixed(1)}° γ=${gamma.toFixed(1)}°`,
      );
    }

    // Validate and constrain values
    const constrainedBeta = clamp(beta, -90, 90); // Prevent upside-down
    const constrainedGamma = clamp(gamma, -90, 90);

    // Apply dead zone
    const deadZonedBeta = applyDeadZone(constrainedBeta, this.DEAD_ZONE);
    const deadZonedGamma = applyDeadZone(constrainedGamma, this.DEAD_ZONE);

    // Create raw reading
    this.latestReading = {
      alpha,
      beta: deadZonedBeta,
      gamma: deadZonedGamma,
      timestamp: Date.now(),
    };

    // Apply smooth interpolation
    this.smoothedReading = {
      alpha: lerp(
        this.smoothedReading.alpha,
        this.latestReading.alpha,
        this.LERP_FACTOR,
      ),
      beta: lerp(
        this.smoothedReading.beta,
        this.latestReading.beta,
        this.LERP_FACTOR,
      ),
      gamma: lerp(
        this.smoothedReading.gamma,
        this.latestReading.gamma,
        this.LERP_FACTOR,
      ),
      timestamp: this.latestReading.timestamp,
    };

    // Notify callback with smoothed data
    if (this.callback) {
      this.callback(this.smoothedReading);
    }
  };

  /**
   * Convert sensor reading to normalized flame lean values
   */
  static toFlameLean(reading: SensorReading): {
    leanX: number;
    leanZ: number;
    magnitude: number;
  } {
    // Map device orientation to flame lean:
    // beta: front-to-back tilt (forward/backward) -> maps to leanX (left/right wind)
    // gamma: left-to-right tilt (sideways) -> maps to leanZ (forward/backward wind)
    const leanX = normalize(reading.beta, -45, 45, -1, 1);
    const leanZ = normalize(reading.gamma, -45, 45, -1, 1);

    // Calculate tilt magnitude (for intensity effects)
    const magnitude = Math.sqrt(leanX * leanX + leanZ * leanZ);

    return {
      leanX: clamp(leanX, -1, 1),
      leanZ: clamp(leanZ, -1, 1),
      magnitude: clamp(magnitude, 0, 1),
    };
  }
}
