package fi.stepcloser.app

import com.meta.wearable.dat.display.types.DisplayState

/**
 * A newly attached display can report STOPPED before its first STARTED event.
 * Only a stop after readiness (or CLOSED at any time) ends this attachment.
 * A terminated attachment must never become ready again without reconnecting.
 */
class DisplayConnectionState {
    enum class Change { PREPARING, READY, LOST, NONE }
    var hasStarted = false
        private set
    var isReady = false
        private set
    private var ended = false

    fun observe(state: DisplayState): Change {
        if (ended) return Change.NONE
        return when (state) {
            DisplayState.STARTED -> {
                val wasReady = isReady
                hasStarted = true
                isReady = true
                if (wasReady) Change.NONE else Change.READY
            }
            DisplayState.STARTING, DisplayState.STOPPING, DisplayState.STOPPED -> {
                isReady = false
                if (hasStarted) {
                    ended = true
                    Change.LOST
                } else Change.PREPARING
            }
            DisplayState.CLOSED -> {
                isReady = false
                ended = true
                Change.LOST
            }
        }
    }
}
