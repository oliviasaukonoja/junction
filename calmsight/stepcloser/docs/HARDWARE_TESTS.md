# Device checks — v0.5.0

These are development acceptance tests, not mandatory app steps. No physical glasses performance results were measured in the build environment.

Record phone model/Android version, Meta AI version, glasses firmware and DAT glasses app version.

## Direct start and multiple actors

1. Open the updated app and start the walking scene without an audio test, STOP rehearsal or review dialog.
2. With glasses disconnected but registered, press Start once. Check that it connects and starts the selected scene.
3. Press STOP while connecting. A later READY event must not display a spider.
4. Try counts 1, 3, 5, 10 and 20. Check the actual number in the lens.
5. Try 0.5×, 1×, 1.5× and 2× walking/circling speed.
6. Verify that crowd actors have independent gait/orbit phases and remain in view.
7. Try circling/jumps. Check that the spoken warning precedes group jumps at every speed.
8. Check the optional neutral dot test. Stopping it must not require a confirmation before starting a spider.

## Compare delivery profiles

Keep all device versions and scene settings identical. Use at least three repeated runs per setting.

| Count | Profile | Mean SDK ack/s | Mean ACK ms | Frame size | Physical smoothness | STOP result |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Auto | | | | | |
| 1 | Fast | | | | | |
| 5 | Auto | | | | | |
| 5 | Fast | | | | | |
| 20 | Auto | | | | | |
| 20 | Fast | | | | | |

ACK rate is measured from SDK responses, not photons. Review physical animation independently. The glasses-paced phone preview shows the cadence of submitted frames, not a captured recording of the lens.

Confirm Auto lowers resolution on a slow link and does not queue delayed frames. The next frame should represent current elapsed time, without replaying old history. Fast profile trades detail for smaller images. A higher walking speed changes the motion, not the number of network updates.

## Stops and interruptions

- Phone STOP during motion: phone clears immediately; native lens clear is requested. Measure optical clear latency separately.
- In-lens STOP: verify selectable focus while image content is updating.
- STOP then restart quickly: a late old frame/ACK must not restart the old session or block the new producer permanently.
- Bluetooth loss/out-of-range: verify loss message, no auto-resume, and remove glasses if an image remains.
- Phone lock/app switch: pending starts and visible content stop.
- Audio interruption: verify handling and restart explicitly.
- Five-minute crowd run: observe temperature, frame rate, battery and stability.
- Browser reload/app restart: no automatic presentation; saved count/profile may be restored, but Start remains explicit.

## Record

| Test | Pass / Fail / Not run | Device observations |
| --- | --- | --- |
| | | |

Do not mark a physical case passed from source inspection or unit tests. STOP acknowledgement is not a guarantee of optical disappearance during link failure.
