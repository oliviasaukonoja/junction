package fi.stepcloser.app

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import android.media.MediaPlayer
import android.os.Bundle
import android.os.SystemClock
import android.util.Base64
import android.util.Log
import android.view.WindowInsets
import android.view.WindowManager
import android.webkit.JavascriptInterface
import android.webkit.RenderProcessGoneDetail
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.lifecycleScope
import androidx.webkit.WebViewAssetLoader
import com.meta.wearable.dat.core.Wearables
import com.meta.wearable.dat.core.selectors.AutoDeviceSelector
import com.meta.wearable.dat.core.session.DeviceSession
import com.meta.wearable.dat.core.session.DeviceSessionState
import com.meta.wearable.dat.core.types.Device
import com.meta.wearable.dat.core.types.DeviceIdentifier
import com.meta.wearable.dat.core.types.LinkState
import com.meta.wearable.dat.core.types.RegistrationState
import com.meta.wearable.dat.core.types.Permission as DatPermission
import com.meta.wearable.dat.core.types.PermissionStatus as DatPermissionStatus
import com.meta.wearable.dat.core.voiceinvocations.isVoiceInvocationsIntent
import com.meta.wearable.dat.core.voiceinvocations.startVoiceInvocationsStream
import com.meta.wearable.dat.core.voiceinvocations.types.actions.LaunchApp
import com.meta.wearable.dat.speech.Speech
import com.meta.wearable.dat.speech.addSpeech
import com.meta.wearable.dat.speech.removeSpeech
import com.meta.wearable.dat.speech.types.SpeechState
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.Job
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicBoolean

class MainActivity : ComponentActivity() {
    private lateinit var web: WebView
    private lateinit var lens: LensRenderer
    private lateinit var audio: AudioManager
    private var initialized = false
    private var session: DeviceSession? = null
    private var stateJob: Job? = null
    private var errorJob: Job? = null
    private var connectTimeout: Job? = null
    private var watchdog: Job? = null
    private val metadataJobs = mutableMapOf<DeviceIdentifier, Job>()
    private val devices = mutableMapOf<DeviceIdentifier, Device>()
    private var permissionAction: (() -> Unit)? = null
    private var player: MediaPlayer? = null
    private var focus: AudioFocusRequest? = null
    private var neutralShown = false
    private var neutralCleared = false
    private var drillPassed = false
    @Volatile private var activeToken = ""
    private val frameBusy = AtomicBoolean(false)
    private var lastFrameAt = 0L
    private var receiverRegistered = false
    private var connectStartedAt = 0L
    private var lastSessionState = "none"
    private var lastDisplayState = "none"
    private var connectionRequestSerial = 0L
    // --- Calmsight voice coach: speech on the glasses + "Hey Meta, start ..." ---
    private var speech: Speech? = null
    private val speechJobs = mutableListOf<Job>()
    @Volatile private var coachSpeakingUntil = 0L
    private var voiceStreamStarted = false
    private var pageReady = false
    private var pendingVoiceLaunch = false
    private val micPermission = registerForActivityResult(Wearables.RequestPermissionContract()) { result ->
        result.onSuccess { status ->
            if (status == DatPermissionStatus.Granted) attachSpeech()
            else emit("speechState", "state" to "DENIED")
        }.onFailure { error, _ -> emit("speechState", "state" to ("ERROR " + error.description)) }
    }
    private val permission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { allowed ->
        val action = permissionAction; permissionAction = null
        if (allowed) initialize { action?.invoke() }
        else emit("message", "message" to "Bluetooth permission was denied. Phone preview is still available.")
    }
    private val noisyReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            abort("Audio output disconnected. Choose the audio output and rehearse again.")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        audio = getSystemService(AUDIO_SERVICE) as AudioManager
        if (savedInstanceState == null && isVoiceInvocationsIntent(intent)) pendingVoiceLaunch = true
        if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED) initialize { }
        lens = LensRenderer(lifecycleScope, { status, token, message ->
            lastDisplayState = status
            if (status in listOf("STARTING", "READY", "ERROR", "LOST", "CLEAR_UNCONFIRMED"))
                trace("Display " + status + ": " + message)
            when (status) {
                "READY" -> { connectTimeout?.cancel(); drillPassed = false; neutralShown = false; neutralCleared = false }
                "NEUTRAL" -> { neutralShown = true; neutralCleared = false }
                "CLEARED" -> if (neutralShown) neutralCleared = true
                "FRAME" -> lastFrameAt = SystemClock.elapsedRealtime()
                "ERROR", "LOST" -> {
                    activeToken = ""; watchdog?.cancel(); stopAudio(); drillPassed = false
                    connectTimeout?.cancel(); connectTimeout = null
                    if (status == "ERROR" && lens.mayHaveContent) lens.clear()
                }
            }
            emit("lens", "status" to status, "token" to token, "message" to message)
        }, { message -> trace(message) }, { runOnUiThread { abort("STOP selected on the glasses.") } })
        val loader = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this)).build()
        web = WebView(this)
        web.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = false
            allowContentAccess = false
            mediaPlaybackRequiresUserGesture = true
            setSupportMultipleWindows(false)
        }
        web.setOnApplyWindowInsetsListener { view, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars())
            view.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        web.webViewClient = object : WebViewClient() {
            override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                // Calmsight coach backend (Modal) is the only allowed external host.
                if (request.url.scheme == "https" && request.url.host?.endsWith(".modal.run") == true) return null
                val response = loader.shouldInterceptRequest(request.url)
                if (request.url.path?.endsWith(".mjs") == true) response?.mimeType = "text/javascript"
                return response ?: WebResourceResponse("text/plain", "UTF-8", 403, "Blocked",
                    emptyMap(), "External page requests blocked".byteInputStream())
            }
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest) =
                request.url.host != "appassets.androidplatform.net"
            override fun onPageFinished(view: WebView, url: String) {
                emit("host", "platform" to "android", "version" to "0.5.0")
                publishDevices()
                pageReady = true
                if (pendingVoiceLaunch) { pendingVoiceLaunch = false; emit("voiceLaunch") }
            }
            override fun onRenderProcessGone(view: WebView, detail: RenderProcessGoneDetail): Boolean {
                abort("The renderer stopped."); closeSession(); finish(); return true
            }
        }
        web.addJavascriptInterface(Bridge(), "StepCloserNative")
        setContentView(web)
        web.loadUrl("https://appassets.androidplatform.net/assets/web/index.html")
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                abort("Stopped with the Android Back button.")
            }
        })
        registerReceiver(noisyReceiver, IntentFilter(AudioManager.ACTION_AUDIO_BECOMING_NOISY),
            Context.RECEIVER_NOT_EXPORTED)
        receiverRegistered = true
    }

    private fun emit(type: String, vararg values: Pair<String, String>) {
        if (!::web.isInitialized) return
        val json = JSONObject().put("type", type)
        values.forEach { json.put(it.first, it.second) }
        web.post { if (!isDestroyed) web.evaluateJavascript("window.StepCloserCallbacks?.event(" + json + ")", null) }
    }
    private fun trace(message: String) {
        Log.i("StepCloserConnection", message)
        val elapsed = if (connectStartedAt == 0L) 0 else SystemClock.elapsedRealtime() - connectStartedAt
        emit("connection", "message" to message, "elapsedMs" to elapsed.toString())
    }
    private fun requireBluetooth(action: () -> Unit) {
        if (checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED) initialize(action)
        else { permissionAction = action; permission.launch(Manifest.permission.BLUETOOTH_CONNECT) }
    }
    private fun initialize(action: () -> Unit) {
        if (initialized) { action(); return }
        Wearables.initialize(this).fold(
            onSuccess = {
                initialized = true
                startVoiceInvocations()
                lifecycleScope.launch {
                    Wearables.registrationState.collect { state ->
                        trace("Registration: " + state.name)
                        emit("registration", "state" to state.name)
                        if (state != RegistrationState.REGISTERED && session != null) {
                            abort("Meta registration ended."); closeSession()
                        }
                    }
                }
                lifecycleScope.launch {
                    Wearables.registrationErrorStream.collect { error ->
                        trace("Registration error: " + error.description)
                        emit("message", "message" to ("Meta registration: " + error.description))
                    }
                }
                lifecycleScope.launch {
                    Wearables.devices.collect { ids ->
                        (metadataJobs.keys - ids).toList().forEach { id ->
                            metadataJobs.remove(id)?.cancel(); devices.remove(id)
                        }
                        ids.forEach { id ->
                            if (id !in metadataJobs) metadataJobs[id] = launch {
                                Wearables.devicesMetadata[id]?.collect { device ->
                                    devices[id] = device; publishDevices()
                                }
                            }
                        }
                        publishDevices()
                    }
                }
                action()
            },
            onFailure = { error, _ -> emit("message", "message" to ("Meta setup failed: " + error.description)) }
        )
    }
    private fun publishDevices() {
        val array = JSONArray()
        devices.values.forEach { device ->
            array.put(JSONObject().put("name", device.name)
                .put("display", device.isDisplayCapable())
                .put("connected", device.linkState == LinkState.CONNECTED)
                .put("compatibility", device.compatibility.toString()))
        }
        emit("devices", "items" to array.toString())
    }
    private fun connect() {
        val request = ++connectionRequestSerial
        requireBluetooth {
          lifecycleScope.launch {
            // Cached registration/device metadata can arrive just after init.
            // Wait briefly rather than making Start require a second tap.
            withTimeoutOrNull(3000) {
                while (request == connectionRequestSerial &&
                    (Wearables.registrationState.value != RegistrationState.REGISTERED ||
                    devices.values.none { it.isDisplayCapable() && it.linkState == LinkState.CONNECTED })) delay(75)
            }
            if (request != connectionRequestSerial) return@launch
            if (Wearables.registrationState.value != RegistrationState.REGISTERED) {
                emit("message", "message" to "Tap Register with Meta AI first, and complete registration."); return@launch
            }
            if (devices.values.none { it.isDisplayCapable() && it.linkState == LinkState.CONNECTED }) {
                emit("message", "message" to "No connected display-capable glasses were found. Ordinary Ray-Ban Meta and Oakley Meta cannot show spiders. Check the exact model and firmware."); return@launch
            }
            if (session != null && lens.isReady) {
                emit("lens", "status" to "READY", "message" to "The display is already connected.")
                return@launch
            }
            if (session != null && connectTimeout?.isActive == true) {
                emit("message", "message" to "Display connection is still starting. Wait for READY or a specific error.")
                return@launch
            }
            closeSession()
            connectStartedAt = SystemClock.elapsedRealtime()
            lastSessionState = "creating"; lastDisplayState = "not attached"
            trace("Connect requested")
            emit("lens", "status" to "STARTING", "message" to "Connecting to Meta Ray-Ban Display.")
            Wearables.createSession(AutoDeviceSelector(filter = { it.isDisplayCapable() })).fold(
                onSuccess = { created ->
                    session = created
                    stateJob = lifecycleScope.launch {
                        created.state.collect { state ->
                            if (session !== created) return@collect
                            lastSessionState = state.name
                            trace("Session state: " + state.name)
                            when (state) {
                                DeviceSessionState.STARTED -> { lens.attach(created); attachSpeech() }
                                DeviceSessionState.PAUSED, DeviceSessionState.STOPPING, DeviceSessionState.STOPPED -> {
                                    abort("Glasses session entered " + state.name + ". Reconnect, then tap Start again.")
                                    closeSession()
                                }
                                else -> Unit
                            }
                        }
                    }
                    errorJob = lifecycleScope.launch {
                        created.errors.collect { error ->
                            trace("Session error: " + error.description)
                            abort("Glasses session error: " + error.description); closeSession()
                        }
                    }
                    connectTimeout = lifecycleScope.launch {
                        delay(45000)
                        if (!lens.isReady && session === created) {
                            abort("Display startup timed out. Last session: " + lastSessionState +
                                "; last display: " + lastDisplayState + ". See Connection details."); closeSession()
                        }
                    }
                    created.start()
                },
                onFailure = { error, _ ->
                    trace("Create session failed: " + error.description)
                    emit("lens", "status" to "ERROR", "message" to ("Create session failed: " + error.description))
                }
            )
          }
        }
    }
    private fun arm(token: String) {
        if (!lens.isReady || token.length !in 1..80) {
            emit("lens", "status" to "ERROR", "message" to "Connect the display before starting.")
            return
        }
        if (!lens.arm(token)) return
        activeToken = token; lastFrameAt = SystemClock.elapsedRealtime()
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        watchdog?.cancel()
        watchdog = lifecycleScope.launch {
            while (activeToken == token) {
                delay(1000)
                if (SystemClock.elapsedRealtime() - lastFrameAt > 5000) {
                    abort("Display frames are no longer acknowledged. Reconnect before continuing.")
                }
            }
        }
        emit("armed", "token" to token)
    }
    private fun stopAudio() {
        player?.let { runCatching { it.stop() }; it.release() }; player = null
        focus?.let { audio.abandonAudioFocusRequest(it) }; focus = null
    }
    private fun playPrompt(key: String) {
        if (!key.matches(Regex("[a-z0-9_-]{1,32}"))) return
        stopAudio()
        val attrs = AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA)
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()
        val request = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
            .setAudioAttributes(attrs).setOnAudioFocusChangeListener { change ->
                if (change < 0) abort("Audio was interrupted. Review the activity before continuing.")
            }.build()
        focus = request
        if (audio.requestAudioFocus(request) != AudioManager.AUDIOFOCUS_REQUEST_GRANTED) {
            emit("message", "message" to "Audio focus is unavailable. Check audio before starting."); return
        }
        try {
            assets.openFd("web/audio/" + key + ".mp3").use { fd ->
                player = MediaPlayer().apply {
                    setAudioAttributes(attrs)
                    setDataSource(fd.fileDescriptor, fd.startOffset, fd.length)
                    setOnCompletionListener { stopAudio() }
                    setOnErrorListener { _, _, _ ->
                        stopAudio(); emit("message", "message" to "Audio playback failed. Text guidance remains available."); true
                    }
                    prepare()
                    coachSpeakingUntil = SystemClock.elapsedRealtime() + duration + 700
                    start()
                }
            }
        } catch (e: Exception) {
            stopAudio(); emit("message", "message" to "Audio playback failed. Check the media volume.")
        }
    }
    private fun playUrl(url: String) {
        val uri = android.net.Uri.parse(url)
        if (uri.scheme != "https" || uri.host?.endsWith(".modal.run") != true) return
        stopAudio()
        val attrs = AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA)
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build()
        val request = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
            .setAudioAttributes(attrs).setOnAudioFocusChangeListener { change ->
                if (change < 0) abort("Audio was interrupted. Review the activity before continuing.")
            }.build()
        focus = request
        if (audio.requestAudioFocus(request) != AudioManager.AUDIOFOCUS_REQUEST_GRANTED) return
        try {
            player = MediaPlayer().apply {
                setAudioAttributes(attrs)
                setDataSource(url)
                setOnPreparedListener {
                    coachSpeakingUntil = SystemClock.elapsedRealtime() + it.duration + 700
                    it.start()
                }
                setOnCompletionListener { stopAudio() }
                setOnErrorListener { _, _, _ -> stopAudio(); emit("coachAudioFailed"); true }
                prepareAsync()
            }
        } catch (e: Exception) {
            stopAudio(); emit("coachAudioFailed")
        }
    }
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        if (isVoiceInvocationsIntent(intent)) voiceLaunch()
    }
    private fun voiceLaunch() {
        runOnUiThread { if (pageReady) emit("voiceLaunch") else pendingVoiceLaunch = true }
    }
    private fun startVoiceInvocations() {
        if (voiceStreamStarted) return
        voiceStreamStarted = true
        lifecycleScope.launch {
            Wearables.registrationState.first { it == RegistrationState.REGISTERED }
            val stream = Wearables.startVoiceInvocationsStream(AutoDeviceSelector())
            launch { stream.errors.collect { error -> trace("Voice invocation: " + error.description) } }
            stream.invocations.collect { invocation ->
                when (invocation) {
                    is LaunchApp -> {
                        invocation.responseHandle.sendSuccess(null)
                        voiceLaunch()
                    }
                }
            }
        }
    }
    private fun attachSpeech() {
        val current = session ?: return
        if (speech != null) return
        lifecycleScope.launch {
            val granted = Wearables.checkPermissionStatus(DatPermission.MICROPHONE).fold(
                onSuccess = { it == DatPermissionStatus.Granted }, onFailure = { _, _ -> false })
            if (!granted) { emit("speechState", "state" to "NEEDS_PERMISSION"); return@launch }
            if (session !== current || speech != null) return@launch
            current.addSpeech().fold(
                onSuccess = { sp ->
                    speech = sp
                    var hasStarted = false
                    speechJobs += lifecycleScope.launch {
                        sp.transcriptions.collect { result ->
                            result ?: return@collect
                            if (SystemClock.elapsedRealtime() < coachSpeakingUntil) return@collect
                            if (!result.isFinal) { emit("speechPartial", "text" to result.text); return@collect }
                            if (result.text.isNotBlank()) emit("speech", "text" to result.text)
                        }
                    }
                    speechJobs += lifecycleScope.launch {
                        sp.state.collect { state ->
                            emit("speechState", "state" to state.name)
                            if (state == SpeechState.STARTED) hasStarted = true
                            // Known DAT issue: recognition goes quiet after ~1 min. Start it again.
                            if (state == SpeechState.STOPPED && hasStarted && speech === sp) { delay(300); sp.start() }
                        }
                    }
                    speechJobs += lifecycleScope.launch {
                        while (speech === sp) { delay(50_000); if (speech === sp) { sp.stop(); delay(400); sp.start() } }
                    }
                    sp.start().onFailure { error, _ -> emit("speechState", "state" to ("ERROR " + error.description)) }
                },
                onFailure = { error, _ -> emit("speechState", "state" to ("UNAVAILABLE " + error.description)) }
            )
        }
    }
    private fun detachSpeech() {
        val sp = speech ?: return
        speech = null
        speechJobs.forEach { it.cancel() }; speechJobs.clear()
        runCatching { sp.stop() }
        runCatching { session?.removeSpeech() }
    }
    private fun stopExposure() {
        activeToken = ""; watchdog?.cancel(); watchdog = null; stopAudio()
        window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        if (session != null && lens.mayHaveContent) lens.clear()
    }
    private fun abort(reason: String) {
        runOnUiThread {
            trace(reason)
            stopExposure()
            emit("interruption", "message" to reason)
        }
    }
    private fun closeSession() {
        activeToken = ""; watchdog?.cancel(); watchdog = null
        drillPassed = false; neutralShown = false; neutralCleared = false
        connectTimeout?.cancel(); connectTimeout = null
        stateJob?.cancel(); errorJob?.cancel(); stateJob = null; errorJob = null
        lens.release()
        detachSpeech()
        session?.stop(); session = null
    }
    inner class Bridge {
        @JavascriptInterface fun register() { runOnUiThread { requireBluetooth {
            if (Wearables.registrationState.value == RegistrationState.REGISTERED)
                emit("message", "message" to "Already registered with Meta AI. Tap Connect display.")
            else Wearables.startRegistration(this@MainActivity)
        } } }
        @JavascriptInterface fun connect() { runOnUiThread { this@MainActivity.connect() } }
        @JavascriptInterface fun disconnect() { activeToken = ""; runOnUiThread { connectionRequestSerial++; stopExposure(); closeSession(); emit("disconnected") } }
        @JavascriptInterface fun neutral() { runOnUiThread {
            drillPassed = false; neutralShown = false; neutralCleared = false; lens.neutral()
        } }
        @JavascriptInterface fun confirmDrill() { runOnUiThread {
            drillPassed = neutralShown && neutralCleared && lens.isReady
            emit("drill", "passed" to drillPassed.toString())
        } }
        @JavascriptInterface fun arm(token: String) { runOnUiThread { this@MainActivity.arm(token) } }
        @JavascriptInterface fun submitFrame(encoded: String, token: String, sequence: Int, capturedAtMs: Double): Boolean {
            if (token != activeToken || token.isEmpty() || encoded.length > 1500000 ||
                sequence < 1 || !frameBusy.compareAndSet(false, true)) return false
            val began = SystemClock.elapsedRealtime()
            lifecycleScope.launch(Dispatchers.Default) {
                var bitmap: android.graphics.Bitmap? = null
                var handedToDisplay = false
                var byteCount = 0
                fun completed(accepted: Boolean) {
                    frameBusy.set(false)
                    emit("frameResult", "token" to token, "sequence" to sequence.toString(),
                        "accepted" to accepted.toString(), "capturedAtMs" to capturedAtMs.toString(),
                        "nativeMs" to (SystemClock.elapsedRealtime() - began).toString(),
                        "bytes" to byteCount.toString())
                }
                try {
                    val bytes = Base64.decode(encoded, Base64.NO_WRAP)
                    byteCount = bytes.size
                    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                    BitmapFactory.decodeByteArray(bytes, 0, bytes.size, bounds)
                    if (bounds.outWidth !in 200..600 || bounds.outWidth != bounds.outHeight) return@launch
                    bitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size) ?: return@launch
                    withContext(Dispatchers.Main) {
                        if (token == activeToken) {
                            val frame = bitmap ?: return@withContext
                            handedToDisplay = true
                            lens.frame(frame, token) { accepted, _ -> completed(accepted) }
                        }
                    }
                } catch (_: Exception) {
                    // Failure is returned to the producer; no obsolete frame is retried.
                } finally {
                    if (!handedToDisplay) { bitmap?.recycle(); completed(false) }
                }
            }
            return true
        }
        @JavascriptInterface fun stop() {
            activeToken = ""
            runOnUiThread { stopExposure() }
        }
        @JavascriptInterface fun playPrompt(key: String) { runOnUiThread { this@MainActivity.playPrompt(key) } }
        @JavascriptInterface fun enableVoice() { runOnUiThread {
            if (session == null) { emit("speechState", "state" to "CONNECT_FIRST"); return@runOnUiThread }
            micPermission.launch(DatPermission.MICROPHONE)
        } }
        @JavascriptInterface fun playUrl(url: String) { runOnUiThread { this@MainActivity.playUrl(url) } }
        @JavascriptInterface fun stopAudio() { runOnUiThread { this@MainActivity.stopAudio() } }
    }
    override fun onPause() {
        super.onPause()
        if (::lens.isInitialized) {
            // Meta/system setup can temporarily cover this Activity. An idle
            // connection contains no feared content and may finish connecting.
            // Any pending or visible image still stops and requires a restart.
            if (activeToken.isNotEmpty() || lens.token.isNotEmpty() || lens.mayHaveContent) {
                abort("App left the foreground during presentation. Reconnect and restart explicitly.")
                closeSession()
            } else if (session != null) trace("Activity paused with no image pending; retaining the connection.")
            stopAudio()
        }
    }
    override fun onDestroy() {
        if (receiverRegistered) unregisterReceiver(noisyReceiver)
        closeSession(); stopAudio(); metadataJobs.values.forEach { it.cancel() }
        web.removeJavascriptInterface("StepCloserNative"); web.destroy()
        super.onDestroy()
    }
}
