"""
Playback state management with proper state machine validation.
"""

import logging
from enum import Enum
from typing import Optional, Set

log = logging.getLogger("playback_state")


class PlaybackState(Enum):
    """Enumeration of all possible playback states."""

    # Core playback states
    NO_SESSION = "no_session"  # No active session/connection
    UNDETERMINED = "undetermined"  # Initial state when pipe opens
    PLAYING = "playing"  # Active playback
    PAUSED = "paused"  # Playback paused
    STOPPED = "stopped"  # Playback stopped
    WAITING = "waiting"  # Waiting for activity after pause/stop

    def __str__(self) -> str:
        """Return the string value for backward compatibility."""
        return self.value


class PlaybackStateMachine:
    """
    State machine for managing playback state transitions with validation.

    This ensures only valid state transitions occur and provides clear
    debugging and logging of state changes.
    """

    # Define valid state transitions
    VALID_TRANSITIONS = {
        PlaybackState.NO_SESSION: {
            PlaybackState.UNDETERMINED,  # Pipe opens
        },
        PlaybackState.UNDETERMINED: {
            PlaybackState.PLAYING,  # First data received
            PlaybackState.NO_SESSION,  # Connection lost
        },
        PlaybackState.PLAYING: {
            PlaybackState.PAUSED,  # pcst=0
            PlaybackState.STOPPED,  # pend or session end
            PlaybackState.NO_SESSION,  # Connection lost
        },
        PlaybackState.PAUSED: {
            PlaybackState.PLAYING,  # pcst=1
            PlaybackState.STOPPED,  # pend or session end
            PlaybackState.WAITING,  # Timer expires
            PlaybackState.NO_SESSION,  # Connection lost
        },
        PlaybackState.STOPPED: {
            PlaybackState.PLAYING,  # New session starts
            PlaybackState.WAITING,  # Timer expires
            PlaybackState.NO_SESSION,  # Connection lost
        },
        PlaybackState.WAITING: {
            PlaybackState.PLAYING,  # Activity resumes
            PlaybackState.NO_SESSION,  # Connection lost
        },
    }

    def __init__(self, initial_state: PlaybackState = PlaybackState.NO_SESSION):
        """Initialize state machine with given initial state."""
        self._current_state = initial_state
        self._previous_state: Optional[PlaybackState] = None

    @property
    def current_state(self) -> PlaybackState:
        """Get the current playback state."""
        return self._current_state

    @property
    def previous_state(self) -> Optional[PlaybackState]:
        """Get the previous playback state."""
        return self._previous_state

    def can_transition_to(self, new_state: PlaybackState) -> bool:
        """Check if transition to new state is valid."""
        if new_state == self._current_state:
            return True  # Same state is always valid (no-op)

        valid_targets = self.VALID_TRANSITIONS.get(self._current_state, set())
        return new_state in valid_targets

    def transition_to(self, new_state: PlaybackState, reason: str = "") -> bool:
        """
        Attempt to transition to new state.

        Args:
            new_state: Target state to transition to
            reason: Optional reason for the transition (for logging)

        Returns:
            True if transition was successful, False if invalid
        """
        if new_state == self._current_state:
            log.debug("State unchanged: %s", new_state)
            return True

        if not self.can_transition_to(new_state):
            log.warning(
                "Invalid state transition: %s -> %s%s", self._current_state, new_state, f" ({reason})" if reason else ""
            )
            return False

        # Valid transition
        self._previous_state = self._current_state
        self._current_state = new_state

        log.info(
            "State transition: %s -> %s%s", self._previous_state, self._current_state, f" ({reason})" if reason else ""
        )
        return True

    def get_valid_transitions(self) -> Set[PlaybackState]:
        """Get all valid states that can be transitioned to from current state."""
        return self.VALID_TRANSITIONS.get(self._current_state, set()).copy()

    def force_transition(self, new_state: PlaybackState, reason: str = "") -> bool:
        """
        Force a state transition bypassing validation (use carefully).

        This method should only be used when external factors require
        a state change that wouldn't normally be valid according to
        the state machine rules.

        Args:
            new_state: Target state to transition to
            reason: Reason for the forced transition (for logging)

        Returns:
            True if transition occurred, False if it was a no-op (same state)
        """
        if new_state == self._current_state:
            log.debug("State unchanged: %s", new_state)
            return False

        # Log warning for forced transitions to aid debugging
        log.warning(
            "Forced state transition: %s -> %s%s", self._current_state, new_state, f" ({reason})" if reason else ""
        )

        self._previous_state = self._current_state
        self._current_state = new_state
        return True

    def reset(self, new_state: PlaybackState = PlaybackState.NO_SESSION) -> None:
        """Reset state machine to initial state."""
        self._previous_state = self._current_state
        self._current_state = new_state
        log.info("State machine reset to: %s", new_state)


def parse_playback_state(state_str: str) -> Optional[PlaybackState]:
    """
    Parse a string into a PlaybackState enum.

    Args:
        state_str: String representation of state

    Returns:
        PlaybackState enum or None if invalid
    """
    try:
        return PlaybackState(state_str)
    except ValueError:
        log.warning("Unknown playback state: %s", state_str)
        return None
