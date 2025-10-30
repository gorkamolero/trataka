# Trataka Implementation Plan

## Project Overview
Building an audio and motion-reactive candle flame meditation web app using THREE.js, WebGL shaders, Device Orientation API, and Web Audio API. Target: 60fps on modern mobile devices with progressive enhancement for older hardware.

---

## Phase 1: Project Setup & Core Architecture (Week 1)

### Initial Setup
- [ ] Install core dependencies (THREE.js, @types/three, gsap, vite)
- [ ] Set up TypeScript configuration with strict mode
- [ ] Configure Vite for GLSL shader imports
- [ ] Create Clean Architecture folder structure (core/data/presentation)
- [ ] Set up ESLint and Prettier for code quality

### Core Architecture Foundation
- [ ] Create core entities (`FlameState.ts`, `SensorReading.ts`, `AudioAnalysis.ts`)
- [ ] Define interfaces (`IFlameRenderer.ts`, `ISensorService.ts`, `IAudioService.ts`)
- [ ] Implement `FeatureDetector.ts` for progressive enhancement
- [ ] Create `PerformanceMonitor.ts` for FPS tracking
- [ ] Set up utility functions (`math.ts` for interpolation, normalization)

### Basic THREE.js Scene
- [ ] Create `ThreeJSFlameRenderer.ts` with scene setup
- [ ] Implement orthographic camera for 2D candle view
- [ ] Add basic lighting (ambient + point light)
- [ ] Create simple plane geometry for flame
- [ ] Set up render loop with requestAnimationFrame
- [ ] Verify 60fps on desktop with stats.js overlay

### Progressive Enhancement Foundation
- [ ] Implement WebGL support detection
- [ ] Create `CanvasFlameRenderer.ts` stub for fallback
- [ ] Add basic gradient-based flame drawing in Canvas 2D
- [ ] Implement renderer factory pattern based on capabilities
- [ ] Test fallback switching mechanism

### Basic Flame Animation
- [ ] Create simple gradient texture for flame
- [ ] Implement time-based UV scrolling (upward motion)
- [ ] Add basic color gradient (yellow → orange → red)
- [ ] Implement smooth animation loop
- [ ] Test cross-browser compatibility (Chrome, Safari, Firefox)

---

## Phase 2: GLSL Shader Implementation (Week 2)

### Shader Setup
- [ ] Create `flame.vert.glsl` with basic pass-through
- [ ] Create `flame.frag.glsl` with UV coordinate handling
- [ ] Set up GLSL file imports in Vite config
- [ ] Create `noise.glsl` with Perlin noise functions
- [ ] Implement shader hot-reloading for development

### Perlin Noise Implementation
- [ ] Generate or source high-quality noise texture (512x512)
- [ ] Implement Fractional Brownian Motion (FBM) in shader
- [ ] Create multi-octave noise sampling (3-4 octaves)
- [ ] Add texture wrapping and filtering settings
- [ ] Optimize noise calculations for mobile

### Fragment Shader Flame Effect
- [ ] Implement UV distortion using noise samples
- [ ] Add time-based upward scrolling (`uv.y -= time * 0.5`)
- [ ] Create color gradient mapping (1900K yellow → orange → red)
- [ ] Implement alpha masking for candle flame shape
- [ ] Add turbulence effects using noise distortion

### Vertex Shader Enhancement
- [ ] Add subtle vertex displacement for organic edges
- [ ] Implement wind/sway effect in vertex shader
- [ ] Optimize vertex calculations for mobile GPUs
- [ ] Pass proper varyings to fragment shader

### Shader Optimization
- [ ] Profile shader performance on desktop
- [ ] Reduce texture lookups where possible
- [ ] Use built-in GLSL functions (mix, smoothstep, dot)
- [ ] Eliminate shader branches (if statements)
- [ ] Test on mid-range mobile device (iPhone 12/Pixel 5)

### Visual Polish
- [ ] Fine-tune flame color palette for meditation aesthetic
- [ ] Adjust flame shape and proportions
- [ ] Add subtle glow effect at flame core
- [ ] Implement smooth flicker animation
- [ ] Create adjustable intensity parameter

---

## Phase 3: Motion Sensor Integration (Week 3)

### Device Orientation API Setup
- [ ] Create `MotionSensorService.ts` in data/services
- [ ] Implement feature detection for DeviceOrientationEvent
- [ ] Add TypeScript types for sensor readings
- [ ] Set up event listener for orientation changes
- [ ] Implement proper cleanup/disposal

### iOS Permission Handling
- [ ] Create `PermissionService.ts` for unified permission handling
- [ ] Implement iOS 13+ `requestPermission()` detection
- [ ] Create `PermissionButton.tsx` component with clear messaging
- [ ] Handle permission promise rejection gracefully
- [ ] Add user-friendly error messages for denied permissions

### Sensor Data Processing
- [ ] Normalize beta/gamma to -1 to 1 range
- [ ] Implement dead zone filtering (±5° threshold)
- [ ] Add smooth interpolation (lerp with 0.1-0.15 factor)
- [ ] Constrain beta to prevent upside-down issues
- [ ] Handle null value validation (iOS edge cases)

### Motion → Flame Mapping
- [ ] Create `UpdateFlameFromMotion.ts` use case
- [ ] Map tilt to flame lean direction (opposite physics)
- [ ] Calculate tilt magnitude for intensity effects
- [ ] Implement wind effect (increased flicker when tilted)
- [ ] Add shader uniforms for lean and intensity

### Sensor Input Buffering
- [ ] Implement input buffer pattern for latest sensor data
- [ ] Throttle sensor updates to 20-30Hz
- [ ] Sync sensor sampling with requestAnimationFrame
- [ ] Prevent redundant flame updates

### Cross-Platform Testing
- [ ] Test on iOS Safari (multiple devices)
- [ ] Test on Chrome Android
- [ ] Test on Samsung Internet
- [ ] Handle coordinate system differences
- [ ] Verify HTTPS requirement on all platforms

### Fallback Controls
- [ ] Implement touch/drag controls for devices without sensors
- [ ] Add mouse controls for desktop
- [ ] Create UI toggle to disable motion controls
- [ ] Test fallback switching seamlessly

---

## Phase 4: Audio Integration (Week 4)

### Web Audio API Setup
- [ ] Create `WebAudioService.ts` in data/services
- [ ] Implement getUserMedia() microphone access
- [ ] Create AudioContext and AnalyserNode
- [ ] Set up MediaStreamSource connection
- [ ] Configure optimal audio settings (no echo cancellation, no noise suppression)

### Microphone Permission Handling
- [ ] Add microphone permission UI in `PermissionButton.tsx`
- [ ] Handle getUserMedia() promise rejection
- [ ] Create specific error handlers (NotAllowedError, NotFoundError, NotReadableError)
- [ ] Implement permission retry mechanism
- [ ] Add clear explanation of why microphone is needed

### Audio Analysis Implementation
- [ ] Set fftSize to 256 for low latency
- [ ] Create Uint8Array for frequency data
- [ ] Implement getByteFrequencyData() in animation loop
- [ ] Focus analysis on low frequencies (10-140Hz for breath)
- [ ] Calculate breath intensity metric (0-1 normalized)

### Audio → Flame Mapping
- [ ] Create `UpdateFlameFromAudio.ts` use case
- [ ] Map breath intensity to flame height scaling
- [ ] Map audio peaks to flicker bursts
- [ ] Implement volume-based color temperature shifts
- [ ] Add shader uniforms for audio-driven effects

### Multi-Stream Coordination
- [ ] Create `CalculateCombinedFlameState.ts` use case
- [ ] Implement unified state calculation from all inputs
- [ ] Combine motion magnitude with audio for flicker speed
- [ ] Ensure atomic updates in animation loop
- [ ] Prevent input source conflicts

### Latency Optimization
- [ ] Target <20ms audio-to-visual latency
- [ ] Optimize analyser smoothingTimeConstant (0.8)
- [ ] Profile audio processing time
- [ ] Implement threshold for meaningful changes (>0.01)
- [ ] Test perceived latency with breath sounds

### Audio Testing
- [ ] Test with various breathing patterns
- [ ] Test with different microphone types
- [ ] Verify low background noise interference
- [ ] Test in quiet vs. noisy environments
- [ ] Ensure no feedback loops (muted output)

---

## Phase 5: Performance Optimization (Week 5)

### Performance Profiling Setup
- [ ] Set up Chrome DevTools remote debugging for iOS
- [ ] Configure Android USB debugging
- [ ] Implement stats.js FPS monitor overlay
- [ ] Add custom performance metrics (frame time, draw calls)
- [ ] Create performance logging to console

### Mobile GPU Optimization
- [ ] Limit devicePixelRatio to 2 max
- [ ] Implement resolution scaling (75-80% native)
- [ ] Reduce texture resolution for mobile (512x512)
- [ ] Enable mipmaps conditionally (disable for orthographic view)
- [ ] Use BufferGeometry exclusively

### Draw Call Minimization
- [ ] Audit total draw calls per frame (target <10)
- [ ] Merge candle body geometry into single mesh
- [ ] Implement instanced rendering if using particles
- [ ] Use texture atlases to reduce texture bindings
- [ ] Profile draw call overhead

### Shader Optimization for Mobile
- [ ] Move calculations from fragment to vertex shader where possible
- [ ] Reduce noise texture lookups
- [ ] Simplify color gradient calculations
- [ ] Remove unnecessary varyings
- [ ] Test shader complexity on older devices (iPhone 8)

### Memory Management
- [ ] Implement texture disposal on cleanup
- [ ] Track WebGL context memory usage
- [ ] Add manual garbage collection hints
- [ ] Monitor total VRAM usage
- [ ] Test memory stability over 30-minute sessions

### Adaptive Quality System
- [ ] Detect frame rate drops (<45fps threshold)
- [ ] Implement quality level switching (High/Medium/Low)
- [ ] Reduce particle count dynamically
- [ ] Simplify shader complexity on quality reduction
- [ ] Restore quality when performance improves

### Texture Compression
- [ ] Generate ASTC compressed textures
- [ ] Generate ETC2 for Android
- [ ] Generate PVRTC for iOS
- [ ] Implement format detection and selection
- [ ] Measure performance improvement

### Battery Impact Testing
- [ ] Monitor battery drain over 30-minute session
- [ ] Optimize for battery efficiency
- [ ] Test thermal throttling on sustained use
- [ ] Add low-power mode option

### Real Device Testing Matrix
- [ ] Test on iPhone 15 Pro (flagship modern)
- [ ] Test on iPhone 12 (mid-range modern)
- [ ] Test on iPhone 8 (older low-end)
- [ ] Test on Pixel 8 (flagship Android)
- [ ] Test on Samsung Galaxy A-series (mid-range Android)
- [ ] Test on older budget Android device
- [ ] Document performance metrics for each device

---

## Phase 6: Polish & Production Readiness (Week 6)

### Meditation Features
- [ ] Implement session timer with configurable duration
- [ ] Add gentle start/end notifications
- [ ] Create adjustable flame intensity setting
- [ ] Add adjustable flame size control
- [ ] Implement optional crackling sound effects

### Settings Panel
- [ ] Create `SettingsPanel.tsx` component
- [ ] Add quality settings (Auto/High/Medium/Low)
- [ ] Add motion sensitivity slider
- [ ] Add audio sensitivity slider
- [ ] Add session duration presets
- [ ] Implement settings persistence (localStorage)

### Error Handling
- [ ] Comprehensive sensor failure handling
- [ ] Audio device unavailable fallbacks
- [ ] WebGL context loss recovery
- [ ] Network offline detection
- [ ] User-friendly error messages

### Onboarding Flow
- [ ] Create welcome screen with app explanation
- [ ] Design permission request flow with clear rationale
- [ ] Add interactive tutorial for tilt controls
- [ ] Show breathing guidance for audio response
- [ ] Implement "skip tutorial" option

### Accessibility
- [ ] Add keyboard navigation support
- [ ] Implement ARIA labels for controls
- [ ] Add high-contrast mode option
- [ ] Ensure screen reader compatibility
- [ ] Test with accessibility tools

### Service Worker & Offline Support
- [ ] Set up Workbox for service worker generation
- [ ] Implement cache-first strategy for static assets
- [ ] Cache all shaders, textures, and sounds
- [ ] Add offline fallback page
- [ ] Test complete offline functionality
- [ ] Keep total cache size under 5MB

### Analytics & Monitoring
- [ ] Implement performance metrics tracking
- [ ] Track permission acceptance rates
- [ ] Log session completion statistics
- [ ] Monitor frame rate distribution
- [ ] Track WebGL context losses
- [ ] Add error reporting (Sentry or similar)

### Cross-Browser Testing
- [ ] Test on Chrome desktop (latest)
- [ ] Test on Safari desktop (latest)
- [ ] Test on Firefox desktop (latest)
- [ ] Test on Edge (latest)
- [ ] Test on iOS Safari (iOS 15, 16, 17)
- [ ] Test on Chrome Android (latest)
- [ ] Test on Samsung Internet
- [ ] Document browser-specific issues

### Performance Validation
- [ ] Verify 60fps on modern devices (iPhone 12+, Pixel 5+)
- [ ] Verify 30fps minimum on older devices (iPhone 8)
- [ ] Confirm <20ms audio latency
- [ ] Validate smooth sensor response
- [ ] Test 30-minute session stability

### Production Build Optimization
- [ ] Configure Vite production build settings
- [ ] Implement code splitting for lazy loading
- [ ] Optimize bundle size (target <500KB total)
- [ ] Enable tree shaking
- [ ] Minify shaders
- [ ] Generate source maps

### Deployment
- [ ] Set up hosting (Vercel/Netlify/Firebase)
- [ ] Configure HTTPS (required for sensors/audio)
- [ ] Set up CI/CD pipeline
- [ ] Configure environment variables
- [ ] Set up domain and SSL certificate

### Documentation
- [ ] Write README with setup instructions
- [ ] Document architecture decisions
- [ ] Create API documentation for core interfaces
- [ ] Add inline code comments for complex logic
- [ ] Document browser compatibility matrix
- [ ] Create troubleshooting guide

### Final Polish
- [ ] Test all permission scenarios
- [ ] Verify graceful degradation paths
- [ ] Test rapid input changes (shake device)
- [ ] Verify no memory leaks
- [ ] Final UX review and tweaks
- [ ] Performance audit on all target devices

---

## Technical Debt & Future Enhancements

### Post-Launch Improvements
- [ ] Add particle system for flame sparks (50-100 particles)
- [ ] Implement post-processing bloom effect
- [ ] Add multiple candle flame styles
- [ ] Create guided meditation sessions
- [ ] Add breath visualization overlay
- [ ] Implement session history tracking
- [ ] Add social sharing features
- [ ] Create PWA manifest for installability

### Advanced Features (Future Phases)
- [ ] Multiple candles with synchronized motion
- [ ] Wind effect visualization
- [ ] Customizable candle appearance
- [ ] Ambient background sounds
- [ ] Integration with meditation timers/apps
- [ ] VR/AR mode support
- [ ] Advanced analytics dashboard

---

## Risk Mitigation

### Critical Risks
1. **iOS Permission Rejection**: Implement clear onboarding, provide value before asking
2. **Mobile Performance Issues**: Implement adaptive quality early, test on real devices throughout
3. **Audio Latency**: Profile early, optimize FFT size and processing pipeline
4. **Battery Drain**: Monitor and optimize rendering efficiency
5. **Browser Compatibility**: Test early and often across all target browsers

### Testing Strategy
- Real device testing from Phase 1 onwards
- Weekly cross-browser compatibility checks
- Continuous performance monitoring
- User testing for permission flows
- Battery and thermal testing on extended sessions

---

## Success Metrics

### Technical Performance
- 60fps on iPhone 12+, Pixel 5+ (90% of frames)
- 30fps minimum on iPhone 8 (95% of frames)
- <20ms audio-to-visual latency
- <16.67ms total frame time on modern devices
- <5MB total app size (including cache)
- Zero memory leaks over 30-minute sessions

### User Experience
- >80% permission acceptance rate
- <3 seconds to first flame render
- Works offline after first load
- Smooth sensor response (no jitter)
- No crashes during 30-minute sessions

---

## Timeline Summary

**Total Duration**: 6 weeks (1 full-time developer)

- **Week 1**: Core architecture + basic THREE.js flame
- **Week 2**: GLSL shader implementation
- **Week 3**: Motion sensor integration
- **Week 4**: Audio/microphone integration
- **Week 5**: Performance optimization
- **Week 6**: Polish + production deployment

**Critical Path**:
1. Shader development (requires GLSL expertise)
2. iOS permission handling (requires Apple devices)
3. Mobile performance optimization (requires real device testing)

**Parallel Work Opportunities**:
- Motion and audio services can be developed in parallel after Week 1
- UI components can be built while core rendering is in progress
- Documentation can be written throughout

---

## Notes

- All sensor and audio APIs require HTTPS in production
- iOS 13+ requires explicit permission for device motion
- Test on real devices early and often—emulators are insufficient
- Keep bundle size minimal for fast load on mobile networks
- Progressive enhancement is critical—not all devices support all features
- Clean Architecture enables testing without browser dependencies
