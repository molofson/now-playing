"""Tests for the ShairportSyncPipeReader class and XML parsing functionality."""

import base64
from unittest.mock import Mock

from nowplaying.metadata_reader import ShairportSyncPipeReader  # noqa: I100
from nowplaying.playback_state import PlaybackState


class TestShairportSyncPipeReader:
    """Test the ShairportSyncPipeReader class for XML parsing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.state_callback = Mock()
        self.metadata_callback = Mock()
        self.reader = ShairportSyncPipeReader(
            state_callback=self.state_callback, metadata_callback=self.metadata_callback
        )

    def test_single_line_xml_with_metadata(self):
        """Test parsing single-line XML with metadata."""
        # Base64 encode "Test Artist"
        artist_data = base64.b64encode("Test Artist".encode("utf-8")).decode("ascii")
        line = f'<item><type>636F7265</type><code>61736172</code><length>11</length><data encoding="base64">{artist_data}</data></item>'

        self.reader.process_line(line)

        # Should not trigger metadata callback yet (no bundle)
        self.metadata_callback.assert_not_called()

    def test_multiline_xml_parsing(self):
        """Test parsing XML that spans multiple lines."""
        # Start metadata bundle
        self.reader.process_line("<item><type>73736E63</type><code>6D647374</code><length>0</length></item>")

        # Start XML item
        self.reader.process_line("<item><type>636F7265</type><code>61736172</code><length>11</length>")
        self.reader.process_line('<data encoding="base64">')

        # Multi-line base64 data
        artist_data = base64.b64encode("Test Artist".encode("utf-8")).decode("ascii")
        self.reader.process_line(artist_data)
        self.reader.process_line("</data></item>")

        # End metadata bundle
        self.reader.process_line("<item><type>73736E63</type><code>6D64656E</code><length>0</length></item>")

        # Should trigger metadata callback with the artist
        self.metadata_callback.assert_called_once()
        metadata = self.metadata_callback.call_args[0][0]
        assert metadata["artist"] == "Test Artist"

    def test_metadata_bundle_processing(self):
        """Test complete metadata bundle processing."""
        # Start metadata bundle
        self.reader.process_line("<item><type>73736E63</type><code>6D647374</code><length>0</length></item>")

        # Add artist metadata
        artist_data = base64.b64encode("Test Artist".encode("utf-8")).decode("ascii")
        artist_line = f'<item><type>636F7265</type><code>61736172</code><length>11</length><data encoding="base64">{artist_data}</data></item>'
        self.reader.process_line(artist_line)

        # Add title metadata
        title_data = base64.b64encode("Test Song".encode("utf-8")).decode("ascii")
        title_line = f'<item><type>636F7265</type><code>6D696E6D</code><length>9</length><data encoding="base64">{title_data}</data></item>'
        self.reader.process_line(title_line)

        # End metadata bundle
        self.reader.process_line("<item><type>73736E63</type><code>6D64656E</code><length>0</length></item>")

        # Should trigger metadata callback with both fields
        self.metadata_callback.assert_called_once()
        metadata = self.metadata_callback.call_args[0][0]
        assert metadata["artist"] == "Test Artist"
        assert metadata["title"] == "Test Song"

    def test_play_state_changes(self):
        """Test play state change handling."""
        # Test play begin
        self.reader.process_line("<item><type>73736E63</type><code>70626567</code><length>0</length></item>")
        self.state_callback.assert_called_with(PlaybackState.PLAYING)

        self.state_callback.reset_mock()

        # Test play end
        self.reader.process_line("<item><type>73736E63</type><code>70656E64</code><length>0</length></item>")
        self.state_callback.assert_called_with(PlaybackState.STOPPED)

    def test_play_control_state_parsing(self):
        """Test play control state parsing (pcst)."""
        # Test playing state
        playing_data = base64.b64encode("1".encode("ascii")).decode("ascii")
        playing_line = f'<item><type>73736E63</type><code>70637374</code><length>1</length><data encoding="base64">{playing_data}</data></item>'
        self.reader.process_line(playing_line)
        self.state_callback.assert_called_with(PlaybackState.PLAYING)

        self.state_callback.reset_mock()

        # Test paused state
        paused_data = base64.b64encode("0".encode("ascii")).decode("ascii")
        paused_line = f'<item><type>73736E63</type><code>70637374</code><length>1</length><data encoding="base64">{paused_data}</data></item>'
        self.reader.process_line(paused_line)
        self.state_callback.assert_called_with(PlaybackState.PAUSED)

    def test_unknown_metadata_codes(self):
        """Test handling of unknown metadata codes."""
        # Unknown core metadata code
        unknown_data = base64.b64encode("unknown".encode("utf-8")).decode("ascii")
        unknown_line = f'<item><type>636F7265</type><code>12345678</code><length>7</length><data encoding="base64">{unknown_data}</data></item>'

        # Should not raise an exception
        self.reader.process_line(unknown_line)

    def test_invalid_xml_format(self):
        """Test handling of invalid XML format."""
        # Invalid XML line should be handled gracefully
        self.reader.process_line("<invalid>xml</invalid>")

        # Should not crash or call callbacks
        self.state_callback.assert_not_called()
        self.metadata_callback.assert_not_called()

    def test_empty_and_whitespace_lines(self):
        """Test handling of empty and whitespace-only lines."""
        self.reader.process_line("")
        self.reader.process_line("   ")
        self.reader.process_line("\t\n")

        # Should not crash or call callbacks
        self.state_callback.assert_not_called()
        self.metadata_callback.assert_not_called()

    def test_base64_decode_error_handling(self):
        """Test handling of invalid base64 data."""
        # Invalid base64 data
        invalid_line = '<item><type>636F7265</type><code>61736172</code><length>10</length><data encoding="base64">invalid_base64!</data></item>'

        # Should handle gracefully without crashing
        self.reader.process_line(invalid_line)

    def test_unicode_metadata_handling(self):
        """Test handling of Unicode metadata."""
        # Unicode artist name
        unicode_artist = "Björk"
        artist_data = base64.b64encode(unicode_artist.encode("utf-8")).decode("ascii")

        # Start metadata bundle
        self.reader.process_line("<item><type>73736E63</type><code>6D647374</code><length>0</length></item>")

        # Add Unicode artist metadata
        artist_line = f'<item><type>636F7265</type><code>61736172</code><length>{len(unicode_artist.encode("utf-8"))}</length><data encoding="base64">{artist_data}</data></item>'
        self.reader.process_line(artist_line)

        # End metadata bundle
        self.reader.process_line("<item><type>73736E63</type><code>6D64656E</code><length>0</length></item>")

        # Should handle Unicode correctly
        self.metadata_callback.assert_called_once()
        metadata = self.metadata_callback.call_args[0][0]
        assert metadata["artist"] == unicode_artist

    def test_all_core_metadata_codes(self):
        """Test all supported core metadata codes."""
        metadata_tests = [
            ("6173616C", "album", "Test Album"),  # asal - Album
            ("61736172", "artist", "Test Artist"),  # asar - Artist
            ("6D696E6D", "title", "Test Title"),  # minm - Title
            ("6173676E", "genre", "Test Genre"),  # asgn - Genre
            ("61736370", "composer", "Test Composer"),  # ascp - Composer
            ("6173636D", "comment", "Test Comment"),  # ascm - Comment
            ("61736474", "description", "Test Description"),  # asdt - Description
            ("61737374", "sortartist", "Test Sort Artist"),  # asst - Sort Artist
            ("6173736E", "sorttitle", "Test Sort Title"),  # assn - Sort Title
        ]

        # Start metadata bundle
        self.reader.process_line("<item><type>73736E63</type><code>6D647374</code><length>0</length></item>")

        for code, _field_name, test_value in metadata_tests:
            data = base64.b64encode(test_value.encode("utf-8")).decode("ascii")
            line = f'<item><type>636F7265</type><code>{code}</code><length>{len(test_value.encode("utf-8"))}</length><data encoding="base64">{data}</data></item>'
            self.reader.process_line(line)

        # End metadata bundle
        self.reader.process_line("<item><type>73736E63</type><code>6D64656E</code><length>0</length></item>")

        # Should have all metadata fields
        self.metadata_callback.assert_called_once()
        metadata = self.metadata_callback.call_args[0][0]

        for _code, field_name, test_value in metadata_tests:
            assert metadata[field_name] == test_value

    def test_ssnc_state_transitions(self):
        """Test various SSNC state transition codes."""
        # Test active begin/end
        self.reader.process_line("<item><type>73736E63</type><code>61626567</code><length>0</length></item>")  # abeg
        # Should not change state for active begin

        self.reader.process_line("<item><type>73736E63</type><code>61656E64</code><length>0</length></item>")  # aend
        self.state_callback.assert_called_with(PlaybackState.NO_SESSION)

        self.state_callback.reset_mock()

        # Test play stream resume
        self.reader.process_line("<item><type>73736E63</type><code>7072736D</code><length>0</length></item>")  # prsm
        self.state_callback.assert_called_with(PlaybackState.PLAYING)
