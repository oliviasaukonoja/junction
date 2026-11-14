package fi.stepcloser.app

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.os.SystemClock
import com.meta.wearable.dat.core.session.DeviceSession
import com.meta.wearable.dat.display.Display
import com.meta.wearable.dat.display.addDisplay
import com.meta.wearable.dat.display.types.DisplayState
import com.meta.wearable.dat.display.views.ButtonStyle
import com.meta.wearable.dat.display.views.ImageSize
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Sends real WebGL-rendered 3D frames to DAT's native bitmap view.
 * Only one frame is in flight. Epoch checks reject frames from stopped sessions.
 * A clear is serialized after any in-flight send; remote disappearance still
 * requires physical-device measurement.
 */
class LensRenderer(
    private val scope: CoroutineScope,
    private val report: (String, String, String) -> Unit,
    private val trace: (String) -> Unit,
    private val userStop: () -> Unit
) {
    private var display: Display? = null
    private var observer: Job? = null
    private val sends = Mutex()
    private var epoch = 0L
    private var currentBitmap: Bitmap? = null
    private var frameCount = 0
    private var connection = DisplayConnectionState()
    var mayHaveContent = false
        private set
    var token = ""
        private set
    val isReady: Boolean get() = connection.isReady && display?.state?.value == DisplayState.STARTED

    fun attach(session: DeviceSession) {
        if (display != null) return
        connection = DisplayConnectionState()
        trace("Display attach requested")
        report("STARTING", "", "Preparing the glasses display.")
        session.addDisplay().fold(
            onSuccess = { added ->
                display = added
                observer = scope.launch {
                    added.state.collect { state ->
                        if (display !== added) return@collect
                        trace("Display state: " + state.name)
                        when (connection.observe(state)) {
                            DisplayConnectionState.Change.PREPARING ->
                                report("STARTING", "", "Preparing display (" + state.name + "). Waiting for STARTED.")
                            DisplayConnectionState.Change.READY ->
                                report("READY", "", "Display connected. Tap Start whenever you choose.")
                            DisplayConnectionState.Change.LOST -> {
                                epoch++; token = ""
                                val reason = if (connection.hasStarted) "Display ended after becoming ready"
                                    else "Display closed before becoming ready"
                                report("LOST", "", reason + " (" + state.name + "). Reconnect." +
                                    if (mayHaveContent) " Remove the glasses if any image remains." else "")
                            }
                            DisplayConnectionState.Change.NONE -> Unit
                        }
                    }
                }
            },
            onFailure = { error, _ -> report("ERROR", "", "Display attach failed: " + error.description) }
        )
    }

    fun arm(requestToken: String): Boolean {
        if (!isReady || requestToken.isEmpty()) return false
        epoch++; token = requestToken; frameCount = 0
        return true
    }

    private suspend fun send(bitmap: Bitmap, request: Long, requestToken: String, neutral: Boolean): Boolean =
        withContext(NonCancellable) {
            sends.withLock {
                val target = display
                if (target == null || !isReady || epoch != request || token != requestToken) return@withLock false
                var accepted = false
                try {
                    mayHaveContent = true
                    target.sendContent {
                        flexBox(padding = 0, gap = 0) {
                            image(bitmap = bitmap, sizePreset = ImageSize.FILL, flexGrow = 1f, flexShrink = 1f)
                            button(label = "STOP", style = ButtonStyle.PRIMARY, onClick = { userStop() })
                        }
                    }.fold(
                        onSuccess = { accepted = it },
                        onFailure = { error, _ -> report("ERROR", requestToken, error.description) }
                    )
                } catch (e: Exception) {
                    report("ERROR", requestToken, "Display transmission failed.")
                }
                if (accepted) {
                    val previous = currentBitmap
                    currentBitmap = bitmap
                    previous?.recycle()
                    if (epoch == request && token == requestToken) {
                        frameCount++
                        report(if (neutral) "NEUTRAL" else "FRAME", requestToken, frameCount.toString())
                    }
                }
                accepted
            }
        }

    fun frame(bitmap: Bitmap, requestToken: String, done: (Boolean, Long) -> Unit) {
        val request = epoch
        scope.launch {
            val started = SystemClock.elapsedRealtime()
            var accepted = false
            try {
                accepted = send(bitmap, request, requestToken, false)
                if (!accepted) bitmap.recycle()
            } finally { done(accepted, SystemClock.elapsedRealtime() - started) }
        }
    }

    fun neutral() {
        if (!arm("neutral")) { report("ERROR", "", "Connect Meta Ray-Ban Display first."); return }
        val request = epoch
        val bitmap = Bitmap.createBitmap(600, 600, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.BLACK)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(174, 226, 181) }
        canvas.drawCircle(300f, 300f, 42f, paint)
        scope.launch {
            if (!send(bitmap, request, "neutral", true)) bitmap.recycle()
        }
    }

    fun clear() {
        epoch++; token = ""
        val request = epoch
        val target = display
        if (target == null) {
            report("CLEAR_UNCONFIRMED", "", "Display is disconnected. Remove the glasses if any image remains.")
            return
        }
        report("CLEARING", "", "Clearing the lens.")
        scope.launch {
            val cleared = withTimeoutOrNull(3000) {
                sends.withLock {
                    if (epoch != request || target !== display) return@withLock false
                    var ok = false
                    target.clearDisplay().fold(onSuccess = { ok = it }, onFailure = { _, _ -> })
                    ok
                }
            } ?: false
            if (epoch == request) {
                if (cleared) {
                    mayHaveContent = false
                    currentBitmap?.recycle(); currentBitmap = null
                    report("CLEARED", "", "The SDK acknowledged lens clear. Confirm it visually.")
                } else report("CLEAR_UNCONFIRMED", "", "Lens clear was not acknowledged. Remove the glasses if any image remains.")
            }
        }
    }

    fun release() {
        trace("Display released")
        val clearWasUnconfirmed = mayHaveContent
        epoch++; token = ""
        observer?.cancel(); observer = null
        display?.stop(); display = null
        mayHaveContent = false
        connection = DisplayConnectionState()
        if (clearWasUnconfirmed)
            report("CLEAR_UNCONFIRMED", "", "Display closed before lens clear was confirmed. Remove the glasses if any image remains.")
        // Do not recycle an image still owned by an in-flight SDK operation.
        scope.launch { sends.withLock { currentBitmap?.recycle(); currentBitmap = null } }
    }
}
