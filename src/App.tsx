import { useState, useEffect, useRef } from "react";
import { FlameCanvas } from "./presentation/components/FlameCanvas";
import { PermissionButton } from "./presentation/components/PermissionButton";
import { VirtualJoystick } from "./presentation/components/VirtualJoystick";
import { AudioIndicator } from "./presentation/components/AudioIndicator";
import type { PermissionType } from "./presentation/components/PermissionButton";
import { createDefaultFlameState } from "./core/entities/FlameState";
import type { FlameState } from "./core/entities/FlameState";
import { MotionSensorService } from "./data/services/MotionSensorService";
import { WebAudioService } from "./data/services/WebAudioService";

type PermissionStatus = "pending" | "granted" | "denied";

function App() {
  const [flameState, setFlameState] = useState<FlameState>(
    createDefaultFlameState(),
  );
  const [motionPermission, setMotionPermission] =
    useState<PermissionStatus>("pending");
  const [audioPermission, setAudioPermission] =
    useState<PermissionStatus>("pending");
  const [currentPermissionRequest, setCurrentPermissionRequest] =
    useState<PermissionType | null>("motion");
  const [audioLevel, setAudioLevel] = useState({
    breathIntensity: 0,
    volume: 0,
  });

  const motionServiceRef = useRef<MotionSensorService | null>(null);
  const audioServiceRef = useRef<WebAudioService | null>(null);

  // Initialize services
  useEffect(() => {
    motionServiceRef.current = new MotionSensorService();
    audioServiceRef.current = new WebAudioService();

    // Check if we're on a non-iOS device (auto-grant motion permission)
    const checkMotionPermission = async () => {
      const hasRequestPermission =
        typeof (
          DeviceOrientationEvent as unknown as {
            requestPermission?: () => Promise<PermissionState>;
          }
        ).requestPermission === "function";

      if (motionServiceRef.current?.isAvailable()) {
        // Non-iOS devices don't need explicit permission
        if (!hasRequestPermission) {
          setMotionPermission("granted");
          setCurrentPermissionRequest("audio");
        }
      } else {
        setMotionPermission("denied");
        setCurrentPermissionRequest("audio");
      }
    };

    checkMotionPermission();

    // Cleanup on unmount
    return () => {
      motionServiceRef.current?.stop();
      audioServiceRef.current?.dispose();
    };
  }, []);

  // Detect if we're on desktop (no touch support)
  const isDesktop = !("ontouchstart" in window);

  // Start motion service when permission granted (but not on desktop)
  useEffect(() => {
    if (
      motionPermission === "granted" &&
      motionServiceRef.current &&
      !isDesktop
    ) {
      motionServiceRef.current.start((reading) => {
        const { leanX, leanZ, magnitude } =
          MotionSensorService.toFlameLean(reading);

        setFlameState((prev) => ({
          ...prev,
          leanX,
          leanZ,
          intensity: 1 + magnitude * 0.3, // Increase intensity when tilted
          flickerSpeed: 1 + magnitude * 0.5, // Increase flicker when tilted
        }));
      });
    }
  }, [motionPermission, isDesktop]);

  // Start audio service when permission granted
  useEffect(() => {
    const startAudio = async () => {
      if (audioPermission === "granted" && audioServiceRef.current) {
        try {
          await audioServiceRef.current.initialize();
          audioServiceRef.current.start((analysis) => {
            const { heightScale, flickerSpeed, colorTemperature } =
              WebAudioService.toFlameParams(analysis);

            // Update audio level indicator
            setAudioLevel({
              breathIntensity: analysis.breathIntensity,
              volume: analysis.volume,
            });

            setFlameState((prev) => ({
              ...prev,
              heightScale,
              flickerSpeed: prev.flickerSpeed * flickerSpeed, // Combine with motion flicker
              colorTemperature,
            }));
          });
        } catch (error) {
          console.error("Failed to initialize audio service:", error);
          setAudioPermission("denied");
        }
      }
    };

    startAudio();
  }, [audioPermission]);

  const handleMotionGranted = async () => {
    setMotionPermission("granted");
    setCurrentPermissionRequest("audio");
  };

  const handleMotionDenied = () => {
    setMotionPermission("denied");
    setCurrentPermissionRequest("audio");
  };

  const handleAudioGranted = () => {
    setAudioPermission("granted");
    setCurrentPermissionRequest(null);
  };

  const handleAudioDenied = () => {
    setAudioPermission("denied");
    setCurrentPermissionRequest(null);
  };

  // Handle virtual joystick input (for desktop testing)
  const handleJoystickMove = (x: number, y: number) => {
    setFlameState((prev) => ({
      ...prev,
      leanX: x,
      leanZ: -y, // Invert Y for natural control
      intensity: 1 + Math.sqrt(x * x + y * y) * 0.3,
      flickerSpeed: 1 + Math.sqrt(x * x + y * y) * 0.5,
    }));
  };

  return (
    <div className="App">
      <FlameCanvas flameState={flameState} />

      {/* Audio level indicator */}
      {audioPermission === "granted" && (
        <AudioIndicator
          breathIntensity={audioLevel.breathIntensity}
          volume={audioLevel.volume}
        />
      )}

      {/* Virtual Joystick for desktop */}
      {isDesktop && !currentPermissionRequest && (
        <VirtualJoystick onMove={handleJoystickMove} />
      )}

      {/* Motion permission dialog */}
      {currentPermissionRequest === "motion" && (
        <PermissionButton
          type="motion"
          onGranted={handleMotionGranted}
          onDenied={handleMotionDenied}
        />
      )}

      {/* Audio permission dialog */}
      {currentPermissionRequest === "audio" && (
        <PermissionButton
          type="audio"
          onGranted={handleAudioGranted}
          onDenied={handleAudioDenied}
        />
      )}
    </div>
  );
}

export default App;
