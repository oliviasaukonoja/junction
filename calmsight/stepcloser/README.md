# StepCloser 3D — source v0.5.0

Complete Android project, bundled web/3D source, local audio, Gradle wrapper and tests. This release builds on the direct-start v0.4.0 app and improves display delivery and multi-spider rendering.

## Changes

- Choose **1, 3, 5, 10 or 20 spiders**.
- Choose **0.5×, 1×, 1.5× or 2× walking/circling speed**.
- Single-spider mode retains the detailed textured/hairy model. Crowds share instanced GPU batches, use lower polygon spheres and omit individual hairs.
- Glasses frames use smaller JPEG captures instead of a 600×600 PNG every 180 ms.
- Capture happens only when the previous frame has been acknowledged. There is one outstanding frame, no historical frame queue, and stale session acknowledgements are ignored.
- Frame resolution adapts in Auto mode. Fixed Fast, Balanced and Sharp profiles are also available.
- Base64/image decoding runs on an Android worker coroutine.
- A bounded latency estimate advances captured animation poses by up to 250 ms. It is an estimate, not a measured optical presentation timestamp.
- The phone can follow glasses frame submissions so its preview does not misleadingly animate at screen refresh while glasses update more slowly. A live phone preview remains selectable.
- Direct Start buttons remain available. Audio tests, STOP tests and reflections are optional; there is no review dialog.
- Connection startup fixes from v0.3.1 are retained.

## Why the glasses looked slower

The old app rendered the phone continuously but requested at most about 5.6 image submissions/second to glasses, before transport and SDK overhead. Bitmap/image UI updates are not a continuous video stream.

This version reduces image-transfer work and avoids producing frames while another is still in flight. Animation positions follow elapsed time, rather than advancing one simulation step per received frame. A low delivery rate therefore causes choppiness/latency rather than intentionally slowing the simulation clock.

JPEG is the WebView-to-Android encoding. DAT receives a smaller decoded bitmap and controls its own transport format. The JPEG setting does not guarantee JPEG on the physical device link.

Compression cannot remove every per-update SDK/link cost. **No physical-glasses FPS improvement has been measured in this build environment.** The on-screen acknowledgement rate measures SDK responses; it is not the optical lens FPS.

| Profile | Frame size | JPEG quality | Maximum request rate |
| --- | --- | --- | --- |
| Auto | Starts at 384; adapts to 320 or 256 | 0.76 | 15/s |
| Fast motion | 256×256 | 0.66 | 15/s |
| Balanced | 384×384 | 0.78 | 12/s |
| Sharp | 512×512 | 0.86 | 8/s |

These rates are caps, not guaranteed achieved rates. A new request waits for the previous SDK result. Auto lowers size after six samples when average acknowledgement time exceeds 190 ms, and can restore quality when it falls below 80 ms.

## Hardware

| Device | Supported output |
| --- | --- |
| Meta Ray-Ban Display | Native lens overlay through Meta Wearables DAT 1.0.1 |
| Ordinary Ray-Ban Meta / Oakley Meta | Guide audio through Android's chosen Bluetooth media route; visuals stay on phone |
| Android phone | ARM64, Android 12/API 31 or newer |
| Meta Quest | Not a supported mixed reality target for this APK |

The lens image is monoscopic with simulated perspective depth. There is no room tracking, real-surface anchoring, physical distance measurement or depth occlusion.

## Use it

1. Install the supplied v0.5.0 APK over v0.4.0. Its signing certificate and application ID match the earlier supplied APK.
2. Select Meta Display glasses or Phone preview.
3. Choose the spider count and walking/circling speed.
4. Tap **Start walking toward me** or **Start circling & jumps**. Registered compatible glasses connect automatically.
5. If the glasses are choppy, stop, choose **Fast motion**, and start again.

For first-time glasses setup, enable Developer Mode and the required DAT app through Meta AI, then use Register with Meta AI in StepCloser. Internet access may be needed for registration. The supplied development manifest uses application ID/client token 0.

Crowd actors are smaller so they fit inside the lens view. They have different gait/orbit phases. Group jumps share the announced jump timing. Speed changes walking and circling; it does not shorten the spoken jump cue interval or jump duration.

Keep the phone STOP accessible. STOP clears the phone scene, cancels pending starts and requests lens clearing. If a connection failure leaves an image in the lens, remove the glasses.

## Build on Ubuntu / Linux

Install a full JDK 17 and Android Studio Narwhal or newer. In Android Studio's SDK Manager install:

- Android SDK Platform 36
- Android SDK Build-Tools 36.0.0
- Android SDK Platform-Tools

Extract the source, then:

    cd StepCloser3D/android
    chmod +x gradlew
    export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
    printf 'sdk.dir=%s\n' "$HOME/Android/Sdk" > local.properties
    ./gradlew assembleDebug

Adjust JDK/SDK paths for your computer. Gradle and Maven dependencies need internet access on the first build.

Output:

    app/build/outputs/apk/debug/app-debug.apk

Install with USB debugging authorized:

    adb devices
    adb install -r app/build/outputs/apk/debug/app-debug.apk

Android Studio alternative: open the **android/** directory, sync Gradle, select the phone and run **app**.

The project pins Gradle 8.14.1, AGP 8.11.1, Kotlin 2.2.21, DAT 1.0.1 and compile/target SDK 36. Version name is 0.5.0; version code is 6. Application ID is fi.stepcloser.app.

### Signing when building yourself

Your computer creates its own debug signing key. It will normally differ from the supplied APK's key, so a locally rebuilt APK may report INSTALL_FAILED_UPDATE_INCOMPATIBLE when replacing the supplied app. Use a separate development application ID/URL scheme, or remove the old installation after saving any local notes you need. Removing an app erases its local data. No private signing key is included in this source.

## Tests and phone-only preview

Node 20 or newer:

    cd StepCloser3D
    npm test

The core tests use Node and bundled Three.js, without a browser or emulator. For the application flow tests, install the pinned development dependency:

    npm ci
    npm run test:flow

The flow tests run the actual app logic with DOM, native-bridge and GPU test doubles. They validate direct start, cancellation, frame backpressure, optional tests and crowd/speed selection. They do not validate visual appearance, Android WebView or physical glasses.

Native JVM connection regression tests:

    cd android
    ./gradlew testDebugUnitTest

From the StepCloser3D project root, for a browser-only phone preview:

    npm run preview

Open http://localhost:18763 in a WebGL 2 capable browser. This preview does not connect to Meta glasses. Browser/GPU and physical-device review remain required.

The spoken clips are bundled. To regenerate them after editing prompts.mjs, install FFmpeg with its Flite filter:

    npm run audio

## Source map

All web files below are under android/app/src/main/assets/web/.

| File | Purpose |
| --- | --- |
| app.mjs / index.html / styles.css | Direct-start interface, options, audio, journal, native events |
| engine.mjs | Session state, explicit start/stop, count and speed validation |
| model.mjs | Original spider geometry, body texture, hair and articulated leg IK |
| crowd.mjs | Shared instanced mesh batches for up to 20 actors |
| motion.mjs | Walking, orbit, jump, crowd layout and spoken-cue timing |
| spider.mjs | WebGL scene, camera, rendering and JPEG capture |
| delivery.mjs | One-frame producer, acknowledgement pacing, quality adaptation and metrics |
| prompts.mjs / audio/ | Spoken guidance text and bundled audio clips |
| vendor/ | Bundled Three.js 0.180.0 and MIT license |

Android native files are under android/app/src/main/java/fi/stepcloser/app/.

| File | Purpose |
| --- | --- |
| MainActivity.kt | DAT registration/session, JPEG worker decoding, bridge, audio and interruption handling |
| LensRenderer.kt | Actual DAT bitmap content, in-lens STOP and serialized clear |
| DisplayConnectionState.kt | Startup versus terminal display state handling |

### Frame path

The WebGL scene renders a current pose. A reusable 2D canvas downsamples it and encodes JPEG. The bridge returns whether Android accepted the packet. A worker validates dimensions and decodes it. The native renderer awaits sendContent. A frameResult event releases the producer and records timing. STOP invalidates tokens so late packets cannot restart the session.

The local bridge signature is:

    submitFrame(base64Jpeg, sessionToken, sequenceNumber, captureTimestampMs)

It returns a Boolean queue-acceptance result. The later frameResult event contains token, sequence, accepted, capturedAtMs, nativeMs and bytes. Never treat the immediate Boolean as proof of physical lens presentation.

## Measure your glasses

See docs/HARDWARE_TESTS.md. Compare Auto and Fast with 1, 5 and 20 spiders. Record SDK acknowledgement rate, acknowledgement latency, physical animation smoothness and STOP behavior separately. Capture multiple runs on the same phone/glasses versions before claiming a speedup.

Connection log:

    adb logcat -d -s StepCloserConnection:I '*:S'

## Scope and references

This is an experimental practice prototype. Clinical effectiveness has not been established. No camera, microphone recording or cloud AI is used by StepCloser. Device registration and communication involve Meta services; DAT analytics and SDK crash reporting are opted out in the manifest.

- Meta Android toolkit: https://github.com/meta/meta-wearables-dat-android
- Meta display documentation: https://wearables.developer.meta.com/docs/develop/
- Developer Mode setup: https://wearables.developer.meta.com/docs/develop/dat/getting-started-toolkit/

Third-party notices and full relevant license records are in docs/ and vendor/.
