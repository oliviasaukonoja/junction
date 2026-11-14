# Verification — v0.5.0

14 November 2026.

## Passed in the build environment

- Android assembleDebug with JDK 17, Gradle 8.14.1, Android SDK/build-tools 36 and DAT 1.0.1.
- Nine native JVM connection lifecycle regression tests.
- Thirty-five Node state, model geometry, motion, crowd and frame-delivery tests.
- Eight application-flow checks using the actual app logic with DOM/native/GPU test doubles.
- APK v2 signature verification and matching signing certificate with the supplied v0.4.0 APK.
- All 33 asset files matched the APK byte for byte, including all 20 audio clips.
- JavaScript syntax checks.

Coverage includes direct start without mandatory tests/review, STOP/cancel during connection, stale ACK rejection, one outstanding frame, adaptive resolution, speed and count validation, 20-actor instanced matrix data, independent crowd motion, perspective framing and spoken jump cue timing.

## Not verified here

- Physical glasses frame rate, optical latency, Bluetooth/audio route, visual smoothness, display contrast, heat/battery use and physical clear latency.
- Browser/Android GPU visual review of the new crowd renderer. Geometry/matrix tests do not establish visual quality or a hardware FPS result.
- Android lint was not rerun; the prior offline environment lacked the lint engine dependency. Run ./gradlew lintDebug with normal repository access.
- Clinical effectiveness or therapeutic safety outcomes.

No numeric physical speedup is claimed. JPEG encoding reduces the WebView bridge payload; DAT receives decoded bitmaps and controls its own transport. The SDK acknowledgement counter is not an optical frame-rate measurement.

## Delivery implementation

- Reusable downsampling canvas; JPEG bridge encoding at 256–512 pixels depending on profile.
- One outstanding packet; a new current pose is captured after SDK acknowledgement.
- Worker-thread bounds validation and bitmap decoding.
- Session token and sequence matching reject old acknowledgements.
- Auto starts at 384 pixels, can lower to 320/256 on slow acknowledgements, and can restore quality.
- Bounded pose prediction of up to 250 ms based on half the smoothed ACK round-trip.
- Walking/circling speed changes simulation phase; jump cue timing stays on wall time.
- Phone preview may follow submitted frame cadence. It is not a recording of the glasses.

The native clear request still waits behind an in-flight SDK send. A failed connection can prevent clearing; remove the glasses if content remains. No subsecond physical clear guarantee is made.

## Final APK

- Filename: StepCloser3D_v0.5.0.apk
- Version code: 6
- Bytes: 24903096
- SHA-256: a9c2b49aa6d5b566841ae13f5c18ab8cffd71511c4832f6803322bc560c3f70d

Machine-readable results are in verification-results.json. Physical acceptance cases are in HARDWARE_TESTS.md.
