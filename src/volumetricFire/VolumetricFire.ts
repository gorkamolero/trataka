import * as THREE from "three";
import { PriorityQueue } from "./PriorityQueue";
import { cornerNeighbors, incomingEdges } from "./fireConstants";
import { vertexShader, fragmentShader } from "./shaders";

interface ActiveEdge {
  expired: boolean;
  startIndex: number;
  endIndex: number;
  deltaPos: THREE.Vector3;
  deltaTex: THREE.Vector3;
  pos: THREE.Vector3;
  tex: THREE.Vector3;
  cur: number;
  prev?: number;
  next?: number;
}

export class VolumetricFire {
  static texturePath = "/textures/";

  mesh: THREE.Mesh;
  camera: THREE.Camera;

  private _sliceSpacing: number;
  private _posCorners: THREE.Vector3[];
  private _basePosCorners: THREE.Vector3[]; // Store original positions
  private _texCorners: THREE.Vector3[];
  private _viewVector: THREE.Vector3;
  private _points: number[] = [];
  private _texCoords: number[] = [];
  private _indexes: number[] = [];
  private _leanX: number = 0;
  private _leanZ: number = 0;

  constructor(
    width: number,
    height: number,
    depth: number,
    sliceSpacing: number,
    camera: THREE.Camera,
  ) {
    this.camera = camera;
    this._sliceSpacing = sliceSpacing;

    const widthHalf = width * 0.5;
    const heightHalf = height * 0.5;
    const depthHalf = depth * 0.5;

    this._basePosCorners = [
      new THREE.Vector3(-widthHalf, -heightHalf, -depthHalf),
      new THREE.Vector3(widthHalf, -heightHalf, -depthHalf),
      new THREE.Vector3(-widthHalf, heightHalf, -depthHalf),
      new THREE.Vector3(widthHalf, heightHalf, -depthHalf),
      new THREE.Vector3(-widthHalf, -heightHalf, depthHalf),
      new THREE.Vector3(widthHalf, -heightHalf, depthHalf),
      new THREE.Vector3(-widthHalf, heightHalf, depthHalf),
      new THREE.Vector3(widthHalf, heightHalf, depthHalf),
    ];

    // Clone for working positions
    this._posCorners = this._basePosCorners.map((v) => v.clone());

    this._texCorners = [
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(1, 0, 0),
      new THREE.Vector3(0, 1, 0),
      new THREE.Vector3(1, 1, 0),
      new THREE.Vector3(0, 0, 1),
      new THREE.Vector3(1, 0, 1),
      new THREE.Vector3(0, 1, 1),
      new THREE.Vector3(1, 1, 1),
    ];

    this._viewVector = new THREE.Vector3();

    // Load textures
    const textureLoader = new THREE.TextureLoader();

    const nzw = textureLoader.load(VolumetricFire.texturePath + "nzw.png");
    nzw.wrapS = THREE.RepeatWrapping;
    nzw.wrapT = THREE.RepeatWrapping;
    nzw.magFilter = THREE.LinearFilter;
    nzw.minFilter = THREE.LinearFilter;

    const fireProfile = textureLoader.load(
      VolumetricFire.texturePath + "firetex.png",
    );
    fireProfile.wrapS = THREE.ClampToEdgeWrapping;
    fireProfile.wrapT = THREE.ClampToEdgeWrapping;
    fireProfile.magFilter = THREE.LinearFilter;
    fireProfile.minFilter = THREE.LinearFilter;

    const uniforms = {
      nzw: { value: nzw },
      fireProfile: { value: fireProfile },
      time: { value: 1.0 },
    };

    const material = new THREE.RawShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms,
      side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending,
      transparent: true,
    });

    // Create geometry
    const index = new Uint16Array((width + height + depth) * 30);
    const position = new Float32Array((width + height + depth) * 30 * 3);
    const tex = new Float32Array((width + height + depth) * 30 * 3);

    const geometry = new THREE.BufferGeometry();
    geometry.setIndex(new THREE.BufferAttribute(index, 1));
    geometry.setAttribute("position", new THREE.BufferAttribute(position, 3));
    geometry.setAttribute("tex", new THREE.BufferAttribute(tex, 3));

    this.mesh = new THREE.Mesh(geometry, material);
    this.mesh.updateMatrixWorld();
  }

  update(elapsed: number): void {
    this.applyLean();
    this.updateViewVector();
    this.slice();
    this.updateGeometry();
    (this.mesh.material as THREE.RawShaderMaterial).uniforms.time.value =
      elapsed;
  }

  setLean(leanX: number, leanZ: number): void {
    this._leanX = leanX;
    this._leanZ = leanZ;
  }

  private applyLean(): void {
    // Apply lean by tilting the corners based on their height
    // Higher corners move more (creating a lean effect)
    for (let i = 0; i < 8; i++) {
      const basePos = this._basePosCorners[i];
      // Calculate lean offset based on height (y coordinate)
      // Normalize height from -heightHalf to +heightHalf to 0-1 range
      const heightFactor = (basePos.y + 2) / 4; // Assuming height is 4

      this._posCorners[i].copy(basePos);
      this._posCorners[i].x += this._leanX * heightFactor * 2;
      this._posCorners[i].z += this._leanZ * heightFactor * 2;
    }
  }

  private updateGeometry(): void {
    (this.mesh.geometry.index as THREE.BufferAttribute).array.set(
      new Uint16Array(this._indexes),
    );
    (this.mesh.geometry.attributes.position as THREE.BufferAttribute).array.set(
      new Float32Array(this._points),
    );
    (this.mesh.geometry.attributes.tex as THREE.BufferAttribute).array.set(
      new Float32Array(this._texCoords),
    );

    (this.mesh.geometry.index as THREE.BufferAttribute).needsUpdate = true;
    (
      this.mesh.geometry.attributes.position as THREE.BufferAttribute
    ).needsUpdate = true;
    (this.mesh.geometry.attributes.tex as THREE.BufferAttribute).needsUpdate =
      true;
  }

  private updateViewVector(): void {
    const modelViewMatrix = new THREE.Matrix4();
    modelViewMatrix.multiplyMatrices(
      this.camera.matrixWorldInverse,
      this.mesh.matrixWorld,
    );

    this._viewVector
      .set(
        -modelViewMatrix.elements[2],
        -modelViewMatrix.elements[6],
        -modelViewMatrix.elements[10],
      )
      .normalize();
  }

  private slice(): void {
    this._points = [];
    this._texCoords = [];
    this._indexes = [];

    let i: number;
    const cornerDistance0 = this._posCorners[0].dot(this._viewVector);

    const cornerDistance = [cornerDistance0];
    let maxCorner = 0;
    let minDistance = cornerDistance0;
    let maxDistance = cornerDistance0;

    for (i = 1; i < 8; i++) {
      cornerDistance[i] = this._posCorners[i].dot(this._viewVector);

      if (cornerDistance[i] > maxDistance) {
        maxCorner = i;
        maxDistance = cornerDistance[i];
      }

      if (cornerDistance[i] < minDistance) {
        minDistance = cornerDistance[i];
      }
    }

    // Aligning slices
    let sliceDistance =
      Math.floor(maxDistance / this._sliceSpacing) * this._sliceSpacing;

    const activeEdges: ActiveEdge[] = [];
    let firstEdge = 0;
    let nextEdge = 0;
    const expirations = new PriorityQueue();

    const createEdge = (
      startIndex: number,
      endIndex: number,
    ): ActiveEdge | undefined => {
      if (nextEdge >= 12) return undefined;

      const activeEdge: ActiveEdge = {
        expired: false,
        startIndex,
        endIndex,
        deltaPos: new THREE.Vector3(),
        deltaTex: new THREE.Vector3(),
        pos: new THREE.Vector3(),
        tex: new THREE.Vector3(),
        cur: nextEdge,
      };

      const range = cornerDistance[startIndex] - cornerDistance[endIndex];

      if (range !== 0.0) {
        const irange = 1.0 / range;

        activeEdge.deltaPos
          .subVectors(this._posCorners[endIndex], this._posCorners[startIndex])
          .multiplyScalar(irange);

        activeEdge.deltaTex
          .subVectors(this._texCorners[endIndex], this._texCorners[startIndex])
          .multiplyScalar(irange);

        const step = cornerDistance[startIndex] - sliceDistance;

        activeEdge.pos.addVectors(
          activeEdge.deltaPos.clone().multiplyScalar(step),
          this._posCorners[startIndex],
        );

        activeEdge.tex.addVectors(
          activeEdge.deltaTex.clone().multiplyScalar(step),
          this._texCorners[startIndex],
        );

        activeEdge.deltaPos.multiplyScalar(this._sliceSpacing);
        activeEdge.deltaTex.multiplyScalar(this._sliceSpacing);
      }

      expirations.push(activeEdge, cornerDistance[endIndex]);
      activeEdges[nextEdge++] = activeEdge;
      return activeEdge;
    };

    for (i = 0; i < 3; i++) {
      const activeEdge = createEdge(maxCorner, cornerNeighbors[maxCorner][i]);
      if (activeEdge) {
        activeEdge.prev = (i + 2) % 3;
        activeEdge.next = (i + 1) % 3;
      }
    }

    let nextIndex = 0;

    while (sliceDistance > minDistance) {
      while (expirations.top().priority >= sliceDistance) {
        const edge = expirations.pop().object as ActiveEdge;

        if (edge.expired) continue;

        if (
          edge.endIndex !== activeEdges[edge.prev!].endIndex &&
          edge.endIndex !== activeEdges[edge.next!].endIndex
        ) {
          // split this edge
          edge.expired = true;

          const activeEdge1 = createEdge(
            edge.endIndex,
            incomingEdges[edge.endIndex][edge.startIndex],
          );
          if (activeEdge1) {
            activeEdge1.prev = edge.prev;
            activeEdges[edge.prev!].next = nextEdge - 1;
            activeEdge1.next = nextEdge;
          }

          const activeEdge2 = createEdge(
            edge.endIndex,
            incomingEdges[edge.endIndex][activeEdge1!.endIndex],
          );
          if (activeEdge2) {
            activeEdge2.prev = nextEdge - 2;
            activeEdge2.next = edge.next;
            activeEdges[activeEdge2.next!].prev = nextEdge - 1;
            firstEdge = nextEdge - 1;
          }
        } else {
          // merge edge
          let prev: ActiveEdge;
          let next: ActiveEdge;

          if (edge.endIndex === activeEdges[edge.prev!].endIndex) {
            prev = activeEdges[edge.prev!];
            next = edge;
          } else {
            prev = edge;
            next = activeEdges[edge.next!];
          }

          prev.expired = true;
          next.expired = true;

          const activeEdge = createEdge(
            edge.endIndex,
            incomingEdges[edge.endIndex][prev.startIndex],
          );
          if (activeEdge) {
            activeEdge.prev = prev.prev;
            activeEdges[activeEdge.prev!].next = nextEdge - 1;
            activeEdge.next = next.next;
            activeEdges[activeEdge.next!].prev = nextEdge - 1;
            firstEdge = nextEdge - 1;
          }
        }
      }

      let cur = firstEdge;
      let count = 0;

      do {
        ++count;
        const activeEdge = activeEdges[cur];
        this._points.push(activeEdge.pos.x, activeEdge.pos.y, activeEdge.pos.z);
        this._texCoords.push(
          activeEdge.tex.x,
          activeEdge.tex.y,
          activeEdge.tex.z,
        );
        activeEdge.pos.add(activeEdge.deltaPos);
        activeEdge.tex.add(activeEdge.deltaTex);
        cur = activeEdge.next!;
      } while (cur !== firstEdge);

      for (i = 2; i < count; i++) {
        this._indexes.push(nextIndex, nextIndex + i - 1, nextIndex + i);
      }

      nextIndex += count;
      sliceDistance -= this._sliceSpacing;
    }
  }
}
