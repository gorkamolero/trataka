import { useEffect, useRef } from "react";
import * as THREE from "three";
import { VolumetricFire } from "../../volumetricFire";
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
    fire: VolumetricFire;
    clock: THREE.Clock;
    animationId: number | null;
  } | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Set texture path
    VolumetricFire.texturePath = "/textures/";

    // Scene setup
    const width = window.innerWidth;
    const height = window.innerHeight;
    const clock = new THREE.Clock();
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000);

    // Camera setup - fixed position for meditation
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    camera.position.set(0, 2, 6);
    camera.lookAt(0, 2, 0);

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); // Limit for performance
    containerRef.current.appendChild(renderer.domElement);

    // Fire setup
    const fireWidth = 2;
    const fireHeight = 4;
    const fireDepth = 2;
    const sliceSpacing = 0.5;

    const fire = new VolumetricFire(
      fireWidth,
      fireHeight,
      fireDepth,
      sliceSpacing,
      camera,
    );

    scene.add(fire.mesh);
    fire.mesh.position.set(0, fireHeight / 2, 0);

    // Animation loop
    const animate = () => {
      const animationId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      fire.update(elapsed);
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
      fire,
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
      if (containerRef.current && renderer.domElement) {
        containerRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Update flame based on state changes
  useEffect(() => {
    if (!sceneRef.current) return;

    const { fire } = sceneRef.current;

    // Apply flame lean (rotate the mesh)
    fire.mesh.rotation.x = flameState.leanZ * 0.3; // Max 17 degrees
    fire.mesh.rotation.z = -flameState.leanX * 0.3; // Max 17 degrees

    // Apply height scale
    fire.mesh.scale.y = flameState.heightScale;

    // TODO: Apply intensity, flickerSpeed, and colorTemperature to shader uniforms
    // This will require exposing shader uniforms in VolumetricFire class
  }, [flameState]);

  return <div ref={containerRef} style={{ width: "100vw", height: "100vh" }} />;
};
