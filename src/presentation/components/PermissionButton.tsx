import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

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
    <Dialog open={true}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{msg.title}</DialogTitle>
          <DialogDescription>{msg.description}</DialogDescription>
        </DialogHeader>
        {error && <div className="text-sm text-destructive">{error}</div>}
        <DialogFooter>
          <Button variant="outline" onClick={onDenied} disabled={requesting}>
            Skip
          </Button>
          <Button onClick={handleRequest} disabled={requesting}>
            {requesting ? "Requesting..." : msg.button}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
