import { useState, useEffect, useRef } from "react";
import { FlameCanvas } from "./presentation/components/FlameCanvas";
import { PermissionButton } from "./presentation/components/PermissionButton";
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

  const motionServiceRef = useRef<MotionSensorService | null>(null);
  const audioServiceRef = useRef<WebAudioService | null>(null);

  // Initialize services
  useEffect(() => {
    motionServiceRef.current = new MotionSensorService();
    audioServiceRef.current = new WebAudioService();

    // Check if we're on a non-iOS device (auto-grant motion permission)
    const checkMotionPermission = async () => {
      if (motionServiceRef.current?.isAvailable()) {
        // Non-iOS devices don't need explicit permission
        if (
          typeof (DeviceOrientationEvent as any).requestPermission !==
          "function"
        ) {
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

  // Start motion service when permission granted
  useEffect(() => {
    if (motionPermission === "granted" && motionServiceRef.current) {
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
  }, [motionPermission]);

  // Start audio service when permission granted
  useEffect(() => {
    const startAudio = async () => {
      if (audioPermission === "granted" && audioServiceRef.current) {
        try {
          await audioServiceRef.current.initialize();
          audioServiceRef.current.start((analysis) => {
            const { heightScale, flickerSpeed, colorTemperature } =
              WebAudioService.toFlameParams(analysis);

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
    try {
      await motionServiceRef.current?.initialize();
      setMotionPermission("granted");
      setCurrentPermissionRequest("audio");
    } catch (error) {
      console.error("Motion permission error:", error);
      setMotionPermission("denied");
      setCurrentPermissionRequest("audio");
    }
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

  return (
    <div className="App">
      <FlameCanvas flameState={flameState} />

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
