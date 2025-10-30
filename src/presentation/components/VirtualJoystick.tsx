import { useEffect, useRef, useState, useCallback } from "react";

interface VirtualJoystickProps {
  onMove: (x: number, y: number) => void;
}

export const VirtualJoystick = ({ onMove }: VirtualJoystickProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  const JOYSTICK_SIZE = 150;
  const STICK_SIZE = 50;
  const MAX_DISTANCE = (JOYSTICK_SIZE - STICK_SIZE) / 2;

  const handleMove = useCallback(
    (clientX: number, clientY: number) => {
      if (!containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      let deltaX = clientX - centerX;
      let deltaY = clientY - centerY;

      // Constrain to circle
      const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
      if (distance > MAX_DISTANCE) {
        const angle = Math.atan2(deltaY, deltaX);
        deltaX = Math.cos(angle) * MAX_DISTANCE;
        deltaY = Math.sin(angle) * MAX_DISTANCE;
      }

      // Update position
      setPosition({ x: deltaX, y: deltaY });

      // Normalize to -1 to 1 range
      const normalizedX = deltaX / MAX_DISTANCE;
      const normalizedY = deltaY / MAX_DISTANCE;

      onMove(normalizedX, normalizedY);
    },
    [MAX_DISTANCE, onMove],
  );

  const handleMouseDown = () => setIsDragging(true);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setPosition({ x: 0, y: 0 });
    onMove(0, 0);
  }, [onMove]);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      if (!isDragging) return;
      handleMove(e.clientX, e.clientY);
    },
    [isDragging, handleMove],
  );

  const handleTouchStart = () => setIsDragging(true);

  const handleTouchEnd = useCallback(() => {
    setIsDragging(false);
    setPosition({ x: 0, y: 0 });
    onMove(0, 0);
  }, [onMove]);

  const handleTouchMove = useCallback(
    (e: TouchEvent) => {
      if (!isDragging || e.touches.length === 0) return;
      const touch = e.touches[0];
      handleMove(touch.clientX, touch.clientY);
    },
    [isDragging, handleMove],
  );

  useEffect(() => {
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.addEventListener("touchmove", handleTouchMove);
    document.addEventListener("touchend", handleTouchEnd);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.removeEventListener("touchmove", handleTouchMove);
      document.removeEventListener("touchend", handleTouchEnd);
    };
  }, [handleMouseMove, handleMouseUp, handleTouchMove, handleTouchEnd]);

  return (
    <div style={styles.container}>
      <div style={styles.instructions}>
        🕹️ Joystick Controls (Desktop)
        <br />
        <small>Move to tilt the flame</small>
      </div>
      <div
        ref={containerRef}
        style={{
          ...styles.joystickContainer,
          width: JOYSTICK_SIZE,
          height: JOYSTICK_SIZE,
        }}
        onMouseDown={handleMouseDown}
        onTouchStart={handleTouchStart}
      >
        <div
          style={{
            ...styles.stick,
            width: STICK_SIZE,
            height: STICK_SIZE,
            transform: `translate(${position.x}px, ${position.y}px)`,
          }}
        />
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: "fixed",
    bottom: "2rem",
    right: "2rem",
    zIndex: 100,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "1rem",
  },
  instructions: {
    color: "#fff",
    fontSize: "0.875rem",
    textAlign: "center",
    textShadow: "0 2px 4px rgba(0,0,0,0.5)",
  },
  joystickContainer: {
    position: "relative",
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    border: "2px solid rgba(255, 255, 255, 0.3)",
    borderRadius: "50%",
    cursor: "pointer",
    touchAction: "none",
  },
  stick: {
    position: "absolute",
    top: "50%",
    left: "50%",
    marginTop: -25,
    marginLeft: -25,
    backgroundColor: "#ff6b35",
    borderRadius: "50%",
    border: "3px solid #fff",
    boxShadow: "0 4px 8px rgba(0,0,0,0.3)",
    transition: "transform 0.1s ease-out",
    pointerEvents: "none",
  },
};
