package fi.stepcloser.app

import com.meta.wearable.dat.display.types.DisplayState
import fi.stepcloser.app.DisplayConnectionState.Change
import org.junit.Assert.*
import org.junit.Test

class DisplayConnectionStateTest {
    @Test fun initialStoppedDoesNotDisconnectAndStartupCanReachReady() {
        val connection = DisplayConnectionState()
        assertEquals(Change.PREPARING, connection.observe(DisplayState.STOPPED))
        assertFalse(connection.isReady)
        assertEquals(Change.PREPARING, connection.observe(DisplayState.STARTING))
        assertEquals(Change.READY, connection.observe(DisplayState.STARTED))
        assertTrue(connection.isReady)
    }

    @Test fun repeatedInitialStoppedStillAllowsTheFirstStartedEvent() {
        val connection = DisplayConnectionState()
        repeat(3) { assertEquals(Change.PREPARING, connection.observe(DisplayState.STOPPED)) }
        assertEquals(Change.READY, connection.observe(DisplayState.STARTED))
    }

    @Test fun startedMayBeTheFirstObservedState() {
        val connection = DisplayConnectionState()
        assertEquals(Change.READY, connection.observe(DisplayState.STARTED))
        assertTrue(connection.hasStarted)
    }

    @Test fun stoppedAfterReadyReallyDisconnects() {
        val connection = DisplayConnectionState()
        connection.observe(DisplayState.STARTED)
        assertEquals(Change.LOST, connection.observe(DisplayState.STOPPED))
        assertFalse(connection.isReady)
    }

    @Test fun stoppingAfterReadyEndsTheAttachmentImmediately() {
        val connection = DisplayConnectionState()
        connection.observe(DisplayState.STARTED)
        assertEquals(Change.LOST, connection.observe(DisplayState.STOPPING))
        assertEquals(Change.NONE, connection.observe(DisplayState.STOPPED))
    }

    @Test fun closedBeforeReadyIsARealStartupFailure() {
        val connection = DisplayConnectionState()
        assertEquals(Change.LOST, connection.observe(DisplayState.CLOSED))
        assertFalse(connection.hasStarted)
        assertFalse(connection.isReady)
    }

    @Test fun lateStartedCannotRestartATerminatedAttachment() {
        val connection = DisplayConnectionState()
        connection.observe(DisplayState.STARTED)
        connection.observe(DisplayState.STOPPED)
        assertEquals(Change.NONE, connection.observe(DisplayState.STARTED))
        assertFalse(connection.isReady)
    }

    @Test fun aNewAttachmentCanConnectAfterThePreviousOneEnded() {
        val previous = DisplayConnectionState()
        previous.observe(DisplayState.STARTED)
        previous.observe(DisplayState.STOPPED)
        val next = DisplayConnectionState()
        next.observe(DisplayState.STOPPED)
        assertEquals(Change.READY, next.observe(DisplayState.STARTED))
    }

    @Test fun duplicateReadyDoesNotRestartTheRehearsal() {
        val connection = DisplayConnectionState()
        connection.observe(DisplayState.STARTED)
        assertEquals(Change.NONE, connection.observe(DisplayState.STARTED))
        assertTrue(connection.isReady)
    }
}
