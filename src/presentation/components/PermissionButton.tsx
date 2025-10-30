import { useState } from "react";

export type PermissionType = "motion" | "audio";

interface PermissionButtonProps {
  type: PermissionType;
  onGranted: () => void;
  onDenied: () => void;
}

export const PermissionButton = ({
  type,
  onGranted,
  onDenied,
}: PermissionButtonProps) => {
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messages = {
    motion: {
      title: "Enable Motion Sensing",
      description: "Allow motion sensors to control the flame with device tilt",
      button: "Enable Motion",
    },
    audio: {
      title: "Enable Microphone",
      description:
        "Allow microphone access to control the flame with your breath",
      button: "Enable Microphone",
    },
  };

  const handleRequest = async () => {
    setRequesting(true);
    setError(null);

    try {
      if (type === "motion") {
        // Request motion permission
        if (
          typeof DeviceOrientationEvent !== "undefined" &&
          typeof (
            DeviceOrientationEvent as unknown as {
              requestPermission?: () => Promise<PermissionState>;
            }
          ).requestPermission === "function"
        ) {
          console.log("Requesting DeviceOrientation permission...");
          const permission = await (
            DeviceOrientationEvent as unknown as {
              requestPermission: () => Promise<PermissionState>;
            }
          ).requestPermission();
          console.log("Permission result:", permission);
          if (permission === "granted") {
            onGranted();
          } else {
            setError(
              `Permission ${permission}. iOS requires HTTPS or user denied.`,
            );
            onDenied();
          }
        } else {
          // Non-iOS devices don't require permission
          onGranted();
        }
      } else if (type === "audio") {
        // Request microphone permission
        try {
          await navigator.mediaDevices.getUserMedia({ audio: true });
          onGranted();
        } catch (err: unknown) {
          const error = err as Error & { name: string };
          if (error.name === "NotAllowedError") {
            setError(
              "Microphone permission denied. Please enable it in your device settings.",
            );
          } else if (error.name === "NotFoundError") {
            setError("No microphone found on this device.");
          } else if (error.name === "NotReadableError") {
            setError("Microphone is already in use by another application.");
          } else {
            setError("Failed to access microphone. Please try again.");
          }
          onDenied();
        }
      }
    } catch (err) {
      console.error("Permission request error:", err);
      setError("An unexpected error occurred. Please try again.");
      onDenied();
    } finally {
      setRequesting(false);
    }
  };

  const msg = messages[type];

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h2 style={styles.title}>{msg.title}</h2>
        <p style={styles.description}>{msg.description}</p>
        <button
          onClick={handleRequest}
          disabled={requesting}
          style={styles.button}
        >
          {requesting ? "Requesting..." : msg.button}
        </button>
        {error && <p style={styles.error}>{error}</p>}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    position: "absolute",
    top: 0,
    left: 0,
    width: "100vw",
    height: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(0, 0, 0, 0.8)",
    zIndex: 1000,
  },
  card: {
    backgroundColor: "#1a1a1a",
    padding: "2rem",
    borderRadius: "1rem",
    maxWidth: "400px",
    textAlign: "center",
    border: "1px solid #333",
  },
  title: {
    color: "#fff",
    fontSize: "1.5rem",
    marginBottom: "1rem",
  },
  description: {
    color: "#aaa",
    fontSize: "1rem",
    marginBottom: "1.5rem",
    lineHeight: "1.5",
  },
  button: {
    backgroundColor: "#ff6b35",
    color: "#fff",
    border: "none",
    padding: "0.75rem 2rem",
    fontSize: "1rem",
    borderRadius: "0.5rem",
    cursor: "pointer",
    transition: "background-color 0.2s",
  },
  error: {
    color: "#ff4444",
    fontSize: "0.875rem",
    marginTop: "1rem",
  },
};
