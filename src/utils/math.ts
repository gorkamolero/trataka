/**
 * Linear interpolation between two values
 */
export const lerp = (start: number, end: number, factor: number): number => {
  return start + (end - start) * factor;
};

/**
 * Normalize a value from one range to another
 */
export const normalize = (
  value: number,
  min: number,
  max: number,
  newMin: number = 0,
  newMax: number = 1
): number => {
  return ((value - min) / (max - min)) * (newMax - newMin) + newMin;
};

/**
 * Clamp a value between min and max
 */
export const clamp = (value: number, min: number, max: number): number => {
  return Math.min(Math.max(value, min), max);
};

/**
 * Apply dead zone to a value
 */
export const applyDeadZone = (value: number, threshold: number): number => {
  return Math.abs(value) < threshold ? 0 : value;
};
