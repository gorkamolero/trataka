import { useEffect, useRef } from "react";
import * as THREE from "three";
import { Candle } from "../../components/Candle";
import type { FlameState } from "../../core/entities/FlameState";

interface FlameCanvasProps {
  flameState: FlameState;
}

export const FlameCanvas = ({ flameState }: FlameCanvasProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<{
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    renderer: THREE.WebGLRenderer;
    candle: Candle;
    clock: THREE.Clock;
    animationId: number | null;
  } | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Scene setup
    const width = window.innerWidth;
    const height = window.innerHeight;
    const clock = new THREE.Clock();
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000);

    // Camera setup
    const camera = new THREE.PerspectiveCamera(60, width / height, 1, 1000);
    camera.position.set(3, 5, 8).setLength(15);
    camera.lookAt(0, 2, 0);

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // Lighting - improved for better depth perception
    const light = new THREE.DirectionalLight(0xffffff, 0.5);
    light.position.set(10, 10, 5);
    light.castShadow = true;
    scene.add(light);
    scene.add(new THREE.AmbientLight(0x4a4a5a, 0.3));

    // Create candle
    const candle = new Candle();
    scene.add(candle.group);

    // Animation loop
    const animate = () => {
      const animationId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      candle.update(elapsed);
      renderer.render(scene, camera);

      if (sceneRef.current) {
        sceneRef.current.animationId = animationId;
      }
    };

    animate();

    // Store refs
    sceneRef.current = {
      scene,
      camera,
      renderer,
      candle,
      clock,
      animationId: null,
    };

    // Handle resize
    const handleResize = () => {
      const newWidth = window.innerWidth;
      const newHeight = window.innerHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };

    window.addEventListener("resize", handleResize);

    // Cleanup
    return () => {
      window.removeEventListener("resize", handleResize);
      if (sceneRef.current?.animationId) {
        cancelAnimationFrame(sceneRef.current.animationId);
      }
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Update flame based on state changes
  useEffect(() => {
    if (!sceneRef.current) return;
    const { candle } = sceneRef.current;
    if (!candle) return;

    candle.setLean(flameState.leanX, flameState.leanZ);

    // Apply breath effect from heightScale (audio analysis)
    const breathIntensity = (flameState.heightScale - 1.0) * 2; // Convert heightScale to 0-1 range
    candle.setBreath(Math.max(0, Math.min(1, breathIntensity)));
  }, [flameState]);

  return <div ref={containerRef} style={{ width: "100vw", height: "100vh" }} />;
};
