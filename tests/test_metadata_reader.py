"""Tests for the ShairportSyncPipeReader class and XML parsing functionality."""

import base64
from unittest.mock import Mock, patch

import pytest

from nowplaying.metadata_monitor import ShairportSyncPipeReader
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

    def test_single_line_xml_parsing(self):
        """Test parsing of single-line XML items."""
        # Test album metadata (asal = 0x6173616c)
        album_data = base64.b64encode(b"Test Album").decode()
        xml_line = f'<item><type>636f7265</type><code>6173616c</code><length>10</length><data encoding="base64">{album_data}</data></item>'

        self.reader.process_line(xml_line)

        # Metadata should be stored but not dispatched until bundle end
        assert self.reader._current_metadata.get("album") == "Test Album"
        self.metadata_callback.assert_not_called()

    def test_multi_line_xml_parsing(self):
        """Test parsing of multi-line XML items."""
        lines = [
            "<item><type>636f7265</type><code>6173616c</code><length>10</length>",  # Album
            '<data encoding="base64">',
            base64.b64encode(b"Test Album").decode(),
            "</data></item>",
        ]

        for line in lines:
            self.reader.process_line(line)

        assert self.reader._current_metadata.get("album") == "Test Album"

    def test_metadata_bundle_lifecycle(self):
        """Test complete metadata bundle from start to end."""
        lines = [
            # Metadata bundle start
            "<item><type>73736e63</type><code>6d647374</code><length>0</length></item>",
            # Album metadata
            "<item><type>636f7265</type><code>6173616c</code><length>10</length>",
            '<data encoding="base64">',
            base64.b64encode(b"Test Album").decode(),
            "</data></item>",
            # Artist metadata
            "<item><type>636f7265</type><code>61736172</code><length>11</length>",
            '<data encoding="base64">',
            base64.b64encode(b"Test Artist").decode(),
            "</data></item>",
            # Title metadata
            "<item><type>636f7265</type><code>6d696e6d</code><length>9</length>",
            '<data encoding="base64">',
            base64.b64encode(b"Test Song").decode(),
            "</data></item>",
            # Genre metadata
            "<item><type>636f7265</type><code>6173676e</code><length>4</length>",
            '<data encoding="base64">',
            base64.b64encode(b"Rock").decode(),
            "</data></item>",
            # Metadata bundle end
            "<item><type>73736e63</type><code>6d64656e</code><length>0</length></item>",
        ]

        for line in lines:
            self.reader.process_line(line)

        # Should dispatch complete metadata at the end
        # Check that metadata callback was called once and contains expected fields
        self.metadata_callback.assert_called_once()
        call_args = self.metadata_callback.call_args[0][0]

        # Verify expected metadata fields are present
        expected_fields = {
            "album": "Test Album",
            "artist": "Test Artist",
            "title": "Test Song",
            "genre": "Rock",
        }
        for key, value in expected_fields.items():
            assert call_args[key] == value, f"Expected {key}='{value}', got '{call_args.get(key)}'"

        # Verify metadata includes ID and sequence number
        assert "metadata_id" in call_args
        assert "sequence_number" in call_args

    def test_state_changes_pcst(self):
        """Test play control state changes."""
        # Play state (pcst = 0x70637374 with payload "1")
        play_data = base64.b64encode(b"1").decode()
        play_xml = f'<item><type>73736e63</type><code>70637374</code><length>1</length><data encoding="base64">{play_data}</data></item>'

        self.reader.process_line(play_xml)
        self.state_callback.assert_called_with(PlaybackState.PLAYING)

        # Reset mock
        self.state_callback.reset_mock()

        # Pause state (pcst with payload "0")
        pause_data = base64.b64encode(b"0").decode()
        pause_xml = f'<item><type>73736e63</type><code>70637374</code><length>1</length><data encoding="base64">{pause_data}</data></item>'

        self.reader.process_line(pause_xml)
        self.state_callback.assert_called_with(PlaybackState.PAUSED)

    def test_session_state_changes(self):
        """Test session begin/end state changes."""
        # Play session begin (pbeg = 0x70626567)
        pbeg_xml = "<item><type>73736e63</type><code>70626567</code><length>0</length></item>"
        self.reader.process_line(pbeg_xml)
        self.state_callback.assert_called_with(PlaybackState.PLAYING)

        # Reset mock
        self.state_callback.reset_mock()

        # Play session end (pend = 0x70656e64)
        pend_xml = "<item><type>73736e63</type><code>70656e64</code><length>0</length></item>"
        self.reader.process_line(pend_xml)
        self.state_callback.assert_called_with(PlaybackState.STOPPED)

    def test_additional_ssnc_codes(self):
        """Test additional SSNC codes that were previously unknown."""
        test_cases = [
            # Client IP (clip = 0x636c6970)
            {
                "xml": f'<item><type>73736e63</type><code>636c6970</code><length>13</length><data encoding="base64">{base64.b64encode(b"192.168.1.180").decode()}</data></item>',
                "should_callback": False,
            },
            # Server IP (svip = 0x73766970)
            {
                "xml": f'<item><type>73736e63</type><code>73766970</code><length>11</length><data encoding="base64">{base64.b64encode(b"192.168.1.1").decode()}</data></item>',
                "should_callback": False,
            },
            # Active Remote (acre = 0x61637265)
            {
                "xml": f'<item><type>73736e63</type><code>61637265</code><length>10</length><data encoding="base64">{base64.b64encode(b"1234567890").decode()}</data></item>',
                "should_callback": False,
            },
            # DACP ID (daid = 0x64616964)
            {
                "xml": f'<item><type>73736e63</type><code>64616964</code><length>16</length><data encoding="base64">{base64.b64encode(b"ABCD1234EFGH5678").decode()}</data></item>',
                "should_callback": False,
            },
            # Enter Active State (abeg = 0x61626567)
            {
                "xml": "<item><type>73736e63</type><code>61626567</code><length>0</length></item>",
                "should_callback": False,
            },
            # Exit Active State (aend = 0x61656e64)
            {
                "xml": "<item><type>73736e63</type><code>61656e64</code><length>0</length></item>",
                "should_callback": True,  # This should trigger NO_SESSION state
            },
        ]

        for test_case in test_cases:
            self.state_callback.reset_mock()
            self.reader.process_line(test_case["xml"])

            if test_case["should_callback"]:
                self.state_callback.assert_called_once()
            else:
                self.state_callback.assert_not_called()

    def test_picture_data_handling(self):
        """Test picture data (album art) handling."""
        # PICT data (PICT = 0x50494354)
        image_data = b"\xff\xd8\xff\xe0\x00\x10JFIF"  # JPEG header
        pict_data = base64.b64encode(image_data).decode()
        pict_xml = f'<item><type>73736e63</type><code>50494354</code><length>{len(image_data)}</length><data encoding="base64">{pict_data}</data></item>'

        with patch("builtins.open", create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            self.reader.process_line(pict_xml)

        # Should not trigger state callback but should call metadata callback with cover art path
        self.state_callback.assert_not_called()

        # Picture data without metadata bundle should not trigger metadata callback
        # since there's no active metadata_id to update
        self.metadata_callback.assert_not_called()

    def test_progress_info_handling(self):
        """Test progress information handling."""
        # Progress metadata
        progress_data = base64.b64encode(b"1000/2000/3000").decode()
        prgr_xml = f'<item><type>73736e63</type><code>70726772</code><length>13</length><data encoding="base64">{progress_data}</data></item>'

        self.reader.process_line(prgr_xml)

        # Should not trigger callbacks but should be handled without error
        self.state_callback.assert_not_called()
        self.metadata_callback.assert_not_called()

    def test_unknown_metadata_codes(self):
        """Test handling of unknown metadata codes."""
        # Unknown core metadata code
        unknown_data = base64.b64encode(b"unknown").decode()
        unknown_xml = f'<item><type>636f7265</type><code>12345678</code><length>7</length><data encoding="base64">{unknown_data}</data></item>'

        self.reader.process_line(unknown_xml)

        # Should not crash or trigger callbacks
        self.state_callback.assert_not_called()
        self.metadata_callback.assert_not_called()

    def test_invalid_xml_handling(self):
        """Test handling of invalid XML."""
        invalid_lines = [
            "<item><type>invalid</type>",  # Invalid hex
            "<item><code>6173616c</code><length>10</length></item>",  # Missing type
            "<item><type>636f7265</type><length>10</length></item>",  # Missing code
            "<item><type>636f7265</type><code>6173616c</code></item>",  # Missing length
            "not xml at all",
            "",
            "   ",
        ]

        for line in invalid_lines:
            # Should not crash
            self.reader.process_line(line)

        self.state_callback.assert_not_called()
        self.metadata_callback.assert_not_called()

    def test_base64_decode_errors(self):
        """Test handling of base64 decode errors."""
        # Invalid base64 data
        invalid_xml = '<item><type>636f7265</type><code>6173616c</code><length>10</length><data encoding="base64">invalid_base64!</data></item>'

        # Should not crash
        self.reader.process_line(invalid_xml)

        self.metadata_callback.assert_not_called()

    def test_utf8_decode_errors(self):
        """Test handling of UTF-8 decode errors."""
        # Invalid UTF-8 bytes
        invalid_utf8 = b"\xff\xfe\x00\x00"
        invalid_data = base64.b64encode(invalid_utf8).decode()
        invalid_xml = f'<item><type>636f7265</type><code>6173616c</code><length>4</length><data encoding="base64">{invalid_data}</data></item>'

        # Should not crash
        self.reader.process_line(invalid_xml)

        self.metadata_callback.assert_not_called()

    def test_all_core_metadata_fields(self):
        """Test all supported core metadata fields."""
        metadata_tests = [
            (0x6173616C, "album", b"Test Album"),  # asal
            (0x61736172, "artist", b"Test Artist"),  # asar
            (0x6D696E6D, "title", b"Test Title"),  # minm
            (0x6173676E, "genre", b"Test Genre"),  # asgn
            (0x61736370, "composer", b"Test Composer"),  # ascp
            (0x6173636D, "comment", b"Test Comment"),  # ascm
            (0x61736474, "description", b"Test Description"),  # asdt
            (0x61737374, "sortartist", b"Test Sort Artist"),  # asst
            (0x6173736E, "sorttitle", b"Test Sort Title"),  # assn
        ]

        # Start metadata bundle
        self.reader.process_line("<item><type>73736e63</type><code>6d647374</code><length>0</length></item>")

        # Add each metadata field
        for code, _field_name, data in metadata_tests:
            encoded_data = base64.b64encode(data).decode()
            xml = f'<item><type>636f7265</type><code>{code:08x}</code><length>{len(data)}</length><data encoding="base64">{encoded_data}</data></item>'
            self.reader.process_line(xml)

        # End metadata bundle
        self.reader.process_line("<item><type>73736e63</type><code>6d64656e</code><length>0</length></item>")

        # Verify all fields were captured
        self.metadata_callback.assert_called_once()
        call_args = self.metadata_callback.call_args[0][0]

        # Check all expected metadata fields
        expected_metadata = {field_name: data.decode() for _, field_name, data in metadata_tests}
        for key, value in expected_metadata.items():
            assert call_args[key] == value, f"Expected {key}='{value}', got '{call_args.get(key)}'"

        # Verify metadata includes ID and sequence number
        assert "metadata_id" in call_args
        assert "sequence_number" in call_args

    def test_state_machine_integration(self):
        """Test that state changes integrate properly with metadata."""
        # Session begin
        self.reader.process_line("<item><type>73736e63</type><code>70626567</code><length>0</length></item>")
        self.state_callback.assert_called_with(PlaybackState.PLAYING)

        # Metadata bundle with song info
        lines = [
            "<item><type>73736e63</type><code>6d647374</code><length>0</length></item>",
            f'<item><type>636f7265</type><code>6173616c</code><length>5</length><data encoding="base64">{base64.b64encode(b"Album").decode()}</data></item>',
            "<item><type>73736e63</type><code>6d64656e</code><length>0</length></item>",
        ]

        for line in lines:
            self.reader.process_line(line)

        # Should have metadata with ID and sequence
        self.metadata_callback.assert_called_once()
        call_args = self.metadata_callback.call_args[0][0]

        # Check expected album field
        assert call_args["album"] == "Album"

        # Verify metadata includes ID and sequence number
        assert "metadata_id" in call_args
        assert "sequence_number" in call_args

        # Session end
        self.reader.process_line("<item><type>73736e63</type><code>70656e64</code><length>0</length></item>")
        self.state_callback.assert_called_with(PlaybackState.STOPPED)

    def test_data_collection_state_reset(self):
        """Test that data collection state is properly reset between items."""
        # Process one complete item
        lines1 = [
            "<item><type>636f7265</type><code>6173616c</code><length>6</length>",
            '<data encoding="base64">',
            base64.b64encode(b"Album1").decode(),
            "</data></item>",
        ]

        for line in lines1:
            self.reader.process_line(line)

        # Verify state is reset
        assert self.reader._current_item is None
        assert not self.reader._collecting_data
        assert self.reader._data_buffer == ""

        # Process another item to ensure clean state
        lines2 = [
            "<item><type>636f7265</type><code>61736172</code><length>6</length>",
            '<data encoding="base64">',
            base64.b64encode(b"Artist").decode(),
            "</data></item>",
        ]

        for line in lines2:
            self.reader.process_line(line)

        # Should work correctly
        assert self.reader._current_metadata.get("artist") == "Artist"

    def test_metadata_id_always_present(self):
        """Test that metadata_id is always present and is a valid UUID."""
        import uuid

        # Start a metadata bundle (mdst = 0x6d647374)
        self.reader.process_line("<item><type>73736e63</type><code>6d647374</code><length>0</length></item>")

        # Test with a simple metadata item
        lines = [
            "<item><type>636f7265</type><code>6d646976</code><length>1</length>",
            '<data encoding="base64">',
            "MQ==",  # "1" in base64
            "</data></item>",
        ]

        for line in lines:
            self.reader.process_line(line)

        # Verify metadata_id is present and is a valid UUID
        assert "metadata_id" in self.reader._current_metadata
        metadata_id = self.reader._current_metadata["metadata_id"]
        assert metadata_id is not None

        # Verify it's a valid UUID by parsing it
        try:
            uuid.UUID(metadata_id)
        except ValueError:
            pytest.fail(f"metadata_id '{metadata_id}' is not a valid UUID")

    def test_sequence_number_increments(self):
        """Test that sequence numbers increment with each metadata bundle."""
        # Start first metadata bundle
        self.reader.process_line("<item><type>73736e63</type><code>6d647374</code><length>0</length></item>")

        # Process first metadata bundle
        lines1 = [
            "<item><type>636f7265</type><code>6d646976</code><length>1</length>",
            '<data encoding="base64">',
            "MQ==",  # "1" in base64
            "</data></item>",
        ]

        for line in lines1:
            self.reader.process_line(line)

        first_sequence = self.reader._current_metadata.get("sequence_number")
        assert first_sequence is not None
        assert isinstance(first_sequence, str)  # sequence_number is stored as string
        first_sequence_int = int(first_sequence)

        # Start second metadata bundle
        self.reader.process_line("<item><type>73736e63</type><code>6d647374</code><length>0</length></item>")

        # Process second metadata bundle
        lines2 = [
            "<item><type>636f7265</type><code>61736172</code><length>6</length>",
            '<data encoding="base64">',
            base64.b64encode(b"Artist").decode(),
            "</data></item>",
        ]

        for line in lines2:
            self.reader.process_line(line)

        second_sequence = self.reader._current_metadata.get("sequence_number")
        assert second_sequence is not None
        assert isinstance(second_sequence, str)  # sequence_number is stored as string
        second_sequence_int = int(second_sequence)
        assert second_sequence_int > first_sequence_int

    def test_sequence_number_resets_on_new_reader(self):
        """Test that sequence numbers start from a consistent value for new readers."""
        # Create a new reader instance
        from unittest.mock import Mock

        new_reader = ShairportSyncPipeReader(state_callback=Mock(), metadata_callback=Mock())

        # Start metadata bundle
        new_reader.process_line("<item><type>73736e63</type><code>6d647374</code><length>0</length></item>")

        # Process metadata
        lines = [
            "<item><type>636f7265</type><code>6d646976</code><length>1</length>",
            '<data encoding="base64">',
            "MQ==",  # "1" in base64
            "</data></item>",
        ]

        for line in lines:
            new_reader.process_line(line)

        # First metadata should have sequence number 1
        first_sequence = new_reader._current_metadata.get("sequence_number")
        assert first_sequence == "1"

    def test_metadata_id_unique_across_bundles(self):
        """Test that each metadata bundle gets a unique metadata_id."""
        # Start first metadata bundle
        self.reader.process_line("<item><type>73736e63</type><code>6d647374</code><length>0</length></item>")

        # Process first metadata bundle
        lines1 = [
            "<item><type>636f7265</type><code>6d646976</code><length>1</length>",
            '<data encoding="base64">',
            "MQ==",  # "1" in base64
            "</data></item>",
        ]

        for line in lines1:
            self.reader.process_line(line)

        first_id = self.reader._current_metadata.get("metadata_id")

        # Start second metadata bundle
        self.reader.process_line("<item><type>73736e63</type><code>6d647374</code><length>0</length></item>")

        # Process second metadata bundle
        lines2 = [
            "<item><type>636f7265</type><code>61736172</code><length>6</length>",
            '<data encoding="base64">',
            base64.b64encode(b"Artist").decode(),
            "</data></item>",
        ]

        for line in lines2:
            self.reader.process_line(line)

        second_id = self.reader._current_metadata.get("metadata_id")

        # Verify both IDs exist and are different
        assert first_id is not None
        assert second_id is not None
        assert first_id != second_id


if __name__ == "__main__":
    pytest.main([__file__])
