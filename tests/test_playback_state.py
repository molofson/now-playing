"""
Tests for the new PlaybackState system.
"""

from unittest.mock import Mock

import pytest

from nowplaying.playback_state import PlaybackState, PlaybackStateMachine


class TestPlaybackState:
    """Test the PlaybackState enum."""

    def test_state_string_values(self):
        """Test that state enums have correct string values."""
        assert str(PlaybackState.NO_SESSION) == "no_session"
        assert str(PlaybackState.PLAYING) == "playing"
        assert str(PlaybackState.PAUSED) == "paused"
        assert str(PlaybackState.STOPPED) == "stopped"
        assert str(PlaybackState.WAITING) == "waiting"
        assert str(PlaybackState.UNDETERMINED) == "undetermined"


class TestPlaybackStateMachine:
    """Test the PlaybackStateMachine class."""

    def setup_method(self):
        self.state_machine = PlaybackStateMachine()

    def test_initial_state(self):
        """Test that state machine starts with NO_SESSION."""
        assert self.state_machine.current_state == PlaybackState.NO_SESSION
        assert self.state_machine.previous_state is None

    def test_valid_transition_no_session_to_undetermined(self):
        """Test valid transition from NO_SESSION to UNDETERMINED."""
        assert self.state_machine.transition_to(PlaybackState.UNDETERMINED, "pipe opened")
        assert self.state_machine.current_state == PlaybackState.UNDETERMINED
        assert self.state_machine.previous_state == PlaybackState.NO_SESSION

    def test_valid_transition_sequence(self):
        """Test a valid sequence of transitions."""
        transitions = [
            (PlaybackState.UNDETERMINED, "pipe opened"),
            (PlaybackState.PLAYING, "metadata received"),
            (PlaybackState.PAUSED, "user paused"),
            (PlaybackState.PLAYING, "user resumed"),
            (PlaybackState.STOPPED, "session ended"),
        ]

        for state, reason in transitions:
            assert self.state_machine.transition_to(state, reason)
            assert self.state_machine.current_state == state

    def test_invalid_transition(self):
        """Test that invalid transitions are rejected."""
        # Try to go directly from NO_SESSION to PLAYING (should fail)
        assert not self.state_machine.transition_to(PlaybackState.PLAYING, "invalid")
        assert self.state_machine.current_state == PlaybackState.NO_SESSION

    def test_same_state_transition(self):
        """Test that same-state transitions are allowed."""
        self.state_machine.transition_to(PlaybackState.UNDETERMINED)
        assert self.state_machine.transition_to(PlaybackState.UNDETERMINED, "duplicate")
        assert self.state_machine.current_state == PlaybackState.UNDETERMINED

    def test_get_valid_transitions(self):
        """Test getting valid transitions for current state."""
        # From NO_SESSION, should only be able to go to UNDETERMINED
        valid = self.state_machine.get_valid_transitions()
        assert valid == {PlaybackState.UNDETERMINED}

        # Transition to PLAYING and test its valid transitions
        self.state_machine.transition_to(PlaybackState.UNDETERMINED)
        self.state_machine.transition_to(PlaybackState.PLAYING)
        valid = self.state_machine.get_valid_transitions()
        expected = {PlaybackState.PAUSED, PlaybackState.STOPPED, PlaybackState.NO_SESSION}
        assert valid == expected

    def test_reset(self):
        """Test resetting the state machine."""
        # Change state
        self.state_machine.transition_to(PlaybackState.UNDETERMINED)
        self.state_machine.transition_to(PlaybackState.PLAYING)

        # Reset
        self.state_machine.reset()
        assert self.state_machine.current_state == PlaybackState.NO_SESSION
        assert self.state_machine.previous_state == PlaybackState.PLAYING
