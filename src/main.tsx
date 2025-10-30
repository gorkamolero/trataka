import "./style.css";
import * as THREE from "three";
import { VolumetricFire } from "./volumetricFire";

VolumetricFire.texturePath = "/textures/";

const width = window.innerWidth;
const height = window.innerHeight;
const clock = new THREE.Clock();
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000);

const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
camera.position.set(0, 0, 3);

const renderer = new THREE.WebGLRenderer();
renderer.setSize(width, height);
document.body.appendChild(renderer.domElement);

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

function animate() {
  requestAnimationFrame(animate);
  const elapsed = clock.getElapsedTime();

  camera.position.set(
    Math.sin(elapsed * 0.1) * 8,
    Math.sin(elapsed * 0.5) * 10,
    Math.cos(elapsed * 0.1) * 8,
  );
  camera.lookAt(scene.position);

  fire.update(elapsed);
  renderer.render(scene, camera);
}

animate();

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
