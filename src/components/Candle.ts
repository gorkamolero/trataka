import * as THREE from "three";

export class Candle {
  group: THREE.Group;
  flameMeshes: THREE.Mesh[] = [];
  flameMaterials: THREE.ShaderMaterial[] = [];
  candleLight: THREE.PointLight;
  candleLight2: THREE.PointLight;
  id: string;

  constructor() {
    this.id = Math.random().toString(36).substr(2, 9);
    this.group = new THREE.Group();

    // Candle case with metallic texture
    const casePath = new THREE.Path();
    casePath.moveTo(0, 0);
    casePath.lineTo(0, 0);
    casePath.absarc(1.5, 0.5, 0.5, Math.PI * 1.5, Math.PI * 2);
    casePath.lineTo(2, 1.5);
    casePath.lineTo(1.99, 1.5);
    casePath.lineTo(1.9, 0.5);
    const caseGeo = new THREE.LatheGeometry(casePath.getPoints(), 64);
    const caseMat = new THREE.MeshStandardMaterial({
      color: 0x2a2a2a,
      metalness: 0.4,
      roughness: 0.6,
      envMapIntensity: 0.5,
    });
    const caseMesh = new THREE.Mesh(caseGeo, caseMat);
    caseMesh.castShadow = true;
    caseMesh.receiveShadow = true;
    this.group.add(caseMesh);

    // Paraffin with waxy texture
    const paraffinPath = new THREE.Path();
    paraffinPath.moveTo(0, -0.25);
    paraffinPath.lineTo(0, -0.25);
    paraffinPath.absarc(1, 0, 0.25, Math.PI * 1.5, Math.PI * 2);
    paraffinPath.lineTo(1.25, 0);
    paraffinPath.absarc(1.89, 0.1, 0.1, Math.PI * 1.5, Math.PI * 2);
    const paraffinGeo = new THREE.LatheGeometry(paraffinPath.getPoints(), 64);
    paraffinGeo.translate(0, 1.25, 0);
    const paraffinMat = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      side: THREE.DoubleSide,
      metalness: 0,
      roughness: 0.6,
      emissive: 0xffbb66,
      emissiveIntensity: 0.15,
    });
    const paraffinMesh = new THREE.Mesh(paraffinGeo, paraffinMat);
    paraffinMesh.receiveShadow = true;
    caseMesh.add(paraffinMesh);

    // Candlewick
    const candlewickProfile = new THREE.Shape();
    candlewickProfile.absarc(0, 0, 0.0625, 0, Math.PI * 2);

    const candlewickCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 0.5, -0.0625),
      new THREE.Vector3(0.25, 0.5, 0.125),
    ]);

    const candlewickGeo = new THREE.ExtrudeGeometry(candlewickProfile, {
      steps: 8,
      bevelEnabled: false,
      extrudePath: candlewickCurve,
    });

    const colors: number[] = [];
    const color1 = new THREE.Color("black");
    const color2 = new THREE.Color(0x994411);
    const color3 = new THREE.Color(0xffff44);

    const posAttr = candlewickGeo.attributes.position;
    for (let i = 0; i < posAttr.count; i++) {
      const y = posAttr.getY(i);
      if (y < 0.4) {
        color1.toArray(colors, i * 3);
      } else {
        color2.toArray(colors, i * 3);
      }
      if (y < 0.15) color3.toArray(colors, i * 3);
    }

    candlewickGeo.setAttribute(
      "color",
      new THREE.BufferAttribute(new Float32Array(colors), 3),
    );
    candlewickGeo.translate(0, 0.95, 0);
    const candlewickMat = new THREE.MeshBasicMaterial({ vertexColors: true });
    const candlewickMesh = new THREE.Mesh(candlewickGeo, candlewickMat);
    caseMesh.add(candlewickMesh);

    // Candle lights
    this.candleLight = new THREE.PointLight(0xffaa33, 1, 5, 2);
    this.candleLight.position.set(0, 3, 0);
    this.candleLight.castShadow = true;
    caseMesh.add(this.candleLight);

    this.candleLight2 = new THREE.PointLight(0xffaa33, 1, 10, 2);
    this.candleLight2.position.set(0, 4, 0);
    this.candleLight2.castShadow = true;
    caseMesh.add(this.candleLight2);

    // Flame (front and back)
    this.createFlame(caseMesh, false);
    this.createFlame(caseMesh, true);
  }

  private createFlame(parent: THREE.Mesh, isFrontSide: boolean) {
    const side = isFrontSide ? THREE.FrontSide : THREE.BackSide;

    const flameMat = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        flickerIntensity: { value: 1.0 },
        windX: { value: 0.0 },
        windZ: { value: 0.0 },
      },
      vertexShader: `
        uniform float time;
        uniform float flickerIntensity;
        uniform float windX;
        uniform float windZ;
        varying vec2 vUv;
        varying float hValue;

        float random (in vec2 st) {
            return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
        }

        float noise (in vec2 st) {
            vec2 i = floor(st);
            vec2 f = fract(st);
            float a = random(i);
            float b = random(i + vec2(1.0, 0.0));
            float c = random(i + vec2(0.0, 1.0));
            float d = random(i + vec2(1.0, 1.0));
            vec2 u = f*f*(3.0-2.0*f);
            return mix(a, b, u.x) + (c - a)* u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
        }

        void main() {
          vUv = uv;
          vec3 pos = position;

          pos *= vec3(0.8, 2, 0.725);
          hValue = position.y;
          float posXZlen = length(position.xz);

          pos.y *= 1. + (cos((posXZlen + 0.25) * 3.1415926) * 0.25 + noise(vec2(0, time)) * 0.125 + noise(vec2(position.x + time, position.z + time)) * 0.5) * position.y;

          // Apply flicker with intensity control and wind direction
          float flickerAmount = 0.0312 * flickerIntensity;
          pos.x += noise(vec2(time * 2., (position.y - time) * 4.0)) * hValue * flickerAmount;
          pos.z += noise(vec2((position.y - time) * 4.0, time * 2.)) * hValue * flickerAmount;

          // Add MUCH stronger wind effect
          pos.x += windX * hValue * 0.5;
          pos.z += windZ * hValue * 0.5;

          gl_Position = projectionMatrix * modelViewMatrix * vec4(pos,1.0);
        }
      `,
      fragmentShader: `
        varying float hValue;
        varying vec2 vUv;

        vec3 heatmapGradient(float t) {
          return clamp((pow(t, 1.5) * 0.8 + 0.2) * vec3(smoothstep(0.0, 0.35, t) + t * 0.5, smoothstep(0.5, 1.0, t), max(1.0 - t * 1.7, t * 7.0 - 6.0)), 0.0, 1.0);
        }

        void main() {
          float v = abs(smoothstep(0.0, 0.4, hValue) - 1.);
          float alpha = (1. - v) * 0.99;
          alpha -= 1. - smoothstep(1.0, 0.97, hValue);
          gl_FragColor = vec4(heatmapGradient(smoothstep(0.0, 0.3, hValue)) * vec3(0.95,0.95,0.4), alpha);
          gl_FragColor.rgb = mix(vec3(0,0,1), gl_FragColor.rgb, smoothstep(0.0, 0.3, hValue));
          gl_FragColor.rgb += vec3(1, 0.9, 0.5) * (1.25 - vUv.y);
          gl_FragColor.rgb = mix(gl_FragColor.rgb, vec3(0.66, 0.32, 0.03), smoothstep(0.95, 1., hValue));
        }
      `,
      transparent: true,
      side: side,
    });

    const flameGeo = new THREE.SphereGeometry(0.5, 32, 32);
    flameGeo.translate(0, 0.5, 0);
    const flameMesh = new THREE.Mesh(flameGeo, flameMat);
    flameMesh.position.set(0.06, 1.2, 0.06);
    flameMesh.rotation.y = THREE.MathUtils.degToRad(-45);
    flameMesh.matrixAutoUpdate = true; // Ensure automatic matrix updates

    parent.add(flameMesh);
    this.flameMeshes.push(flameMesh);
    this.flameMaterials.push(flameMat);
  }

  update(time: number) {
    // Update flame shader time
    this.flameMaterials.forEach((mat) => {
      mat.uniforms.time.value = time;
    });

    // Animate candle light with wind influence
    const windInfluence = Math.sqrt(
      this.flameMaterials[0].uniforms.windX.value ** 2 +
        this.flameMaterials[0].uniforms.windZ.value ** 2,
    );

    this.candleLight2.position.x =
      Math.sin(time * Math.PI) * 0.25 +
      this.flameMaterials[0].uniforms.windX.value * 0.3;
    this.candleLight2.position.z =
      Math.cos(time * Math.PI * 0.75) * 0.25 +
      this.flameMaterials[0].uniforms.windZ.value * 0.3;
    this.candleLight2.intensity =
      2 +
      Math.sin(time * Math.PI * 2) * Math.cos(time * Math.PI * 1.5) * 0.25 +
      windInfluence;
  }

  setLean(leanX: number, leanZ: number) {
    const magnitude = Math.sqrt(leanX * leanX + leanZ * leanZ);
    const flickerIntensity = 1.0 + magnitude * 3.0;

    // Only update shader wind uniforms - no mesh transformation
    this.flameMaterials.forEach((mat) => {
      mat.uniforms.windX.value = leanX;
      mat.uniforms.windZ.value = leanZ;
      mat.uniforms.flickerIntensity.value = flickerIntensity;
    });

    // Update light intensity as visual feedback
    this.candleLight2.color.setRGB(1, 0.66 + magnitude * 0.34, 0.2);
    this.candleLight2.intensity = 2 + magnitude * 2;
  }

  setBreath(breathIntensity: number) {
    // breathIntensity ranges from 0 to 1
    // Make the flame grow/shrink and flicker more with breath
    this.flameMeshes.forEach((mesh) => {
      const baseScale = 1.0;
      const breathScale = baseScale + breathIntensity * 0.3;
      mesh.scale.y = breathScale;
    });

    // Increase flicker with breath
    const breathFlicker = 1.0 + breathIntensity * 2.0;
    this.flameMaterials.forEach((mat) => {
      const currentFlicker = mat.uniforms.flickerIntensity.value;
      mat.uniforms.flickerIntensity.value = currentFlicker * breathFlicker;
    });

    // Make light brighter and more orange with breath
    const breathColor = 0.66 + breathIntensity * 0.2;
    this.candleLight2.color.setRGB(1, breathColor, 0.2);
    this.candleLight2.intensity = 2 + breathIntensity * 3;
  }
}
