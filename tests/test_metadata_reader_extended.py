"""
Extended tests for ShairportSyncPipeReader covering newer functionality like
cover art handling, binary data detection, and comprehensive DMAP support.
"""

import base64
import os
import struct
import tempfile
import time
from unittest.mock import Mock, patch

import pytest

from nowplaying.metadata_reader import ShairportSyncPipeReader
from nowplaying.playback_state import PlaybackState


class TestShairportSyncPipeReaderExtended:
    """Extended tests for newer ShairportSyncPipeReader functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.state_callback = Mock()
        self.metadata_callback = Mock()
        self.reader = ShairportSyncPipeReader(
            state_callback=self.state_callback, metadata_callback=self.metadata_callback
        )

    def test_binary_data_detection_in_core_metadata(self):
        """Test detection and logging of binary data in core metadata fields."""
        # Create binary data with null characters
        binary_data = b"\x00\x01\x02\x03\xff\xfe\xfd"
        encoded_data = base64.b64encode(binary_data).decode()

        # Send as album metadata (should be detected as binary)
        xml_line = f'<item><type>636f7265</type><code>6173616c</code><length>{len(binary_data)}</length><data encoding="base64">{encoded_data}</data></item>'

        with patch("nowplaying.metadata_reader.log") as mock_log:
            self.reader.process_line(xml_line)

            # Should log as binary data, not add to metadata
            # The new error handling includes the UnicodeDecodeError details
            mock_log.debug.assert_called()
            # Check that the call includes the expected message pattern
            call_args = mock_log.debug.call_args[0]
            assert "Core metadata" in call_args[0]
            assert "album" in call_args
            assert len(binary_data) in call_args
            assert "album" not in self.reader._current_metadata

    def test_text_with_null_characters_detection(self):
        """Test detection of text containing null characters as binary."""
        # Text with embedded null characters (common in binary data)
        text_with_nulls = "Artist\x00Name\x00\x00"
        encoded_data = base64.b64encode(text_with_nulls.encode()).decode()

        xml_line = f'<item><type>636f7265</type><code>61736172</code><length>{len(text_with_nulls.encode())}</length><data encoding="base64">{encoded_data}</data></item>'

        with patch("nowplaying.metadata_reader.log") as mock_log:
            self.reader.process_line(xml_line)

            # Should be detected as binary due to null characters
            mock_log.debug.assert_called_with(
                "Core metadata %s: <binary data, %d bytes>",
                "artist",
                len(text_with_nulls.encode()),
            )
            assert "artist" not in self.reader._current_metadata

    def test_valid_unicode_text_handling(self):
        """Test that valid Unicode text is handled correctly."""
        # Valid Unicode text
        unicode_text = "Björk & Sigur Rós"
        encoded_data = base64.b64encode(unicode_text.encode()).decode()

        # Start metadata bundle
        self.reader.process_line("<item><type>73736e63</type><code>6d647374</code><length>0</length></item>")

        xml_line = f'<item><type>636f7265</type><code>61736172</code><length>{len(unicode_text.encode())}</length><data encoding="base64">{encoded_data}</data></item>'
        self.reader.process_line(xml_line)

        # End metadata bundle
        self.reader.process_line("<item><type>73736e63</type><code>6d64656e</code><length>0</length></item>")

        # Should be stored correctly
        self.metadata_callback.assert_called_once()
        metadata = self.metadata_callback.call_args[0][0]
        assert metadata["artist"] == unicode_text

    def test_cover_art_jpeg_handling(self):
        """Test JPEG cover art processing and file saving."""
        # JPEG header and some data
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00"
        encoded_data = base64.b64encode(jpeg_data).decode()

        # Start a metadata bundle to provide context for cover art
        self.reader.process_line("<item><type>73736e63</type><code>6d647374</code><length>0</length></item>")

        # Set up album metadata
        album_data = base64.b64encode(b"Test Album").decode()
        self.reader.process_line(
            f'<item><type>636f7265</type><code>6173616c</code><length>10</length><data encoding="base64">{album_data}</data></item>'
        )

        # Send PICT data
        xml_line = f'<item><type>73736e63</type><code>50494354</code><length>{len(jpeg_data)}</length><data encoding="base64">{encoded_data}</data></item>'

        with patch("builtins.open", create=True) as mock_open, patch("time.time", return_value=1234567890):
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            self.reader.process_line(xml_line)

            # Should save file with checksum-based name (checksum: 7dc16757)
            expected_filename = "/tmp/cover_Test_Album_7dc16757.jpg"
            mock_open.assert_called_once_with(expected_filename, "wb")
            mock_file.write.assert_called_once_with(jpeg_data)

            # Should call metadata callback with cover art path
            self.metadata_callback.assert_called_once()
            metadata = self.metadata_callback.call_args[0][0]
            assert metadata["cover_art_path"] == expected_filename

    def test_cover_art_png_handling(self):
        """Test PNG cover art processing."""
        # PNG header
        png_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00"
        encoded_data = base64.b64encode(png_data).decode()

        self.reader._current_metadata = {"album": "PNG Album"}

        xml_line = f'<item><type>73736e63</type><code>50494354</code><length>{len(png_data)}</length><data encoding="base64">{encoded_data}</data></item>'

        with patch("builtins.open", create=True) as mock_open, patch("time.time", return_value=1234567890):

            self.reader.process_line(xml_line)

            # Should detect PNG format with checksum-based name (checksum: 925f0979)
            expected_filename = "/tmp/cover_PNG_Album_925f0979.png"
            mock_open.assert_called_once_with(expected_filename, "wb")

    def test_cover_art_unknown_format(self):
        """Test cover art with unknown format falls back to .bin extension."""
        # Unknown binary data
        unknown_data = b"\x12\x34\x56\x78unknown format"
        encoded_data = base64.b64encode(unknown_data).decode()

        self.reader._current_metadata = {"album": "Unknown Format"}

        xml_line = f'<item><type>73736e63</type><code>50494354</code><length>{len(unknown_data)}</length><data encoding="base64">{encoded_data}</data></item>'

        with patch("builtins.open", create=True) as mock_open, patch("time.time", return_value=1234567890):

            self.reader.process_line(xml_line)

            # Should use .bin extension for unknown format with checksum (checksum: b06f11a5)
            expected_filename = "/tmp/cover_Unknown_Format_b06f11a5.bin"
            mock_open.assert_called_once_with(expected_filename, "wb")

    def test_cover_art_filename_sanitization(self):
        """Test that album names are properly sanitized for filenames."""
        jpeg_data = b"\xff\xd8\xff\xe0test"
        encoded_data = base64.b64encode(jpeg_data).decode()

        # Album name with special characters
        self.reader._current_metadata = {"album": 'Album/With\\Special:Characters<>|"*?'}

        xml_line = f'<item><type>73736e63</type><code>50494354</code><length>{len(jpeg_data)}</length><data encoding="base64">{encoded_data}</data></item>'

        with patch("builtins.open", create=True) as mock_open, patch("time.time", return_value=1234567890):

            self.reader.process_line(xml_line)

            # Should sanitize special characters with checksum (checksum: 0418619a)
            expected_filename = "/tmp/cover_Album_With_Special_Characters__0418619a.jpg"
            mock_open.assert_called_once_with(expected_filename, "wb")

    def test_cover_art_long_album_name_truncation(self):
        """Test that very long album names are truncated."""
        jpeg_data = b"\xff\xd8\xff\xe0test"
        encoded_data = base64.b64encode(jpeg_data).decode()

        # Very long album name
        long_album = "A" * 100  # 100 characters
        self.reader._current_metadata = {"album": long_album}

        xml_line = f'<item><type>73736e63</type><code>50494354</code><length>{len(jpeg_data)}</length><data encoding="base64">{encoded_data}</data></item>'

        with patch("builtins.open", create=True) as mock_open, patch("time.time", return_value=1234567890):

            self.reader.process_line(xml_line)

            # Should truncate to 30 characters with checksum (checksum: 0418619a)
            expected_filename = f"/tmp/cover_{'A' * 30}_0418619a.jpg"
            mock_open.assert_called_once_with(expected_filename, "wb")

    def test_cover_art_no_album_name(self):
        """Test cover art handling when no album name is available."""
        jpeg_data = b"\xff\xd8\xff\xe0test"
        encoded_data = base64.b64encode(jpeg_data).decode()

        # No album in metadata
        xml_line = f'<item><type>73736e63</type><code>50494354</code><length>{len(jpeg_data)}</length><data encoding="base64">{encoded_data}</data></item>'

        with patch("builtins.open", create=True) as mock_open, patch("time.time", return_value=1234567890):

            self.reader.process_line(xml_line)

            # Should use default album name with checksum (checksum: 0418619a)
            expected_filename = "/tmp/cover_unknown_album_0418619a.jpg"
            mock_open.assert_called_once_with(expected_filename, "wb")

    def test_cover_art_file_write_error(self):
        """Test handling of file write errors when saving cover art."""
        jpeg_data = b"\xff\xd8\xff\xe0test"
        encoded_data = base64.b64encode(jpeg_data).decode()

        xml_line = f'<item><type>73736e63</type><code>50494354</code><length>{len(jpeg_data)}</length><data encoding="base64">{encoded_data}</data></item>'

        permission_error = PermissionError("Permission denied")
        with patch("builtins.open", side_effect=permission_error), patch("nowplaying.metadata_reader.log") as mock_log:

            self.reader.process_line(xml_line)

            # Should log error with exception object
            mock_log.error.assert_called_with("Failed to save cover art: %s", permission_error)

            # Should not call metadata callback
            self.metadata_callback.assert_not_called()

    def test_empty_cover_art_data(self):
        """Test handling of empty cover art data."""
        xml_line = "<item><type>73736e63</type><code>50494354</code><length>0</length></item>"

        with patch("nowplaying.metadata_reader.log") as mock_log:
            self.reader.process_line(xml_line)

            # Should log empty data message
            mock_log.debug.assert_called_with("Empty picture data received")

            # Should not attempt file operations
            self.metadata_callback.assert_not_called()

    def test_comprehensive_dmap_codes(self):
        """Test comprehensive DMAP code handling including newer codes."""
        # Start metadata bundle
        self.reader.process_line("<item><type>73736e63</type><code>6d647374</code><length>0</length></item>")

        # Test some DMAP codes that should be handled
        dmap_tests = [
            (0x61736370, "Composer Name"),  # ascp - Composer
            (0x6173636D, "Comment Text"),  # ascm - Comment
            (0x61736474, "Description"),  # asdt - Description
            (0x61737374, "Sort Artist"),  # asst - Sort Artist
            (0x6173736E, "Sort Title"),  # assn - Sort Title Name
        ]

        for code, test_value in dmap_tests:
            encoded_data = base64.b64encode(test_value.encode()).decode()
            xml_line = f'<item><type>636f7265</type><code>{code:08x}</code><length>{len(test_value.encode())}</length><data encoding="base64">{encoded_data}</data></item>'
            self.reader.process_line(xml_line)

        # End metadata bundle
        self.reader.process_line("<item><type>73736e63</type><code>6d64656e</code><length>0</length></item>")

        # Check that metadata was captured
        self.metadata_callback.assert_called_once()
        metadata = self.metadata_callback.call_args[0][0]

        assert metadata["composer"] == "Composer Name"
        assert metadata["comment"] == "Comment Text"
        assert metadata["description"] == "Description"
        assert metadata["sortartist"] == "Sort Artist"
        assert metadata["sorttitle"] == "Sort Title"

    def test_unknown_dmap_codes_with_binary_detection(self):
        """Test unknown DMAP codes with binary data detection."""
        # Unknown DMAP code with binary data
        binary_data = b"\x00\x01\x02\x03\xff"
        encoded_data = base64.b64encode(binary_data).decode()
        xml_line = f'<item><type>636f7265</type><code>12345678</code><length>{len(binary_data)}</length><data encoding="base64">{encoded_data}</data></item>'

        with patch("nowplaying.metadata_reader.log") as mock_log:
            self.reader.process_line(xml_line)

            # Should log as unknown binary DMAP code (the actual code tries to decode as DMAP first)
            # The code 0x12345678 converts to ASCII '\x124Vx' so it logs as unknown DMAP
            ascii_code = struct.pack(">I", 0x12345678).decode("ascii", errors="replace")
            mock_log.debug.assert_called_with(
                "Unknown DMAP 0x%08x ('%s'): <binary data, %d bytes>",
                0x12345678,
                ascii_code,
                len(binary_data),
            )

    def test_ssnc_codes_comprehensive(self):
        """Test comprehensive SSNC code handling."""
        ssnc_tests = [
            # Known state-changing codes
            (0x70626567, None, PlaybackState.PLAYING),  # pbeg - play begin
            (0x70656E64, None, PlaybackState.STOPPED),  # pend - play end
            (0x61656E64, None, PlaybackState.NO_SESSION),  # aend - active end
            (0x7072736D, None, PlaybackState.PLAYING),  # prsm - play resume
            (
                0x70637374,
                "1",
                PlaybackState.PLAYING,
            ),  # pcst - play control state (playing)
            (
                0x70637374,
                "0",
                PlaybackState.PAUSED,
            ),  # pcst - play control state (paused)
            # Non-state-changing codes (should not trigger state callback)
            (0x636C6970, "192.168.1.100", None),  # clip - client IP
            (0x73766970, "192.168.1.1", None),  # svip - server IP
            (0x61637265, "1234567890", None),  # acre - active remote
            (0x64616964, "DAID12345678", None),  # daid - DACP ID
        ]

        for code, payload, expected_state in ssnc_tests:
            self.state_callback.reset_mock()

            if payload is None:
                # No payload
                xml_line = f"<item><type>73736e63</type><code>{code:08x}</code><length>0</length></item>"
            else:
                # With payload
                encoded_payload = base64.b64encode(payload.encode()).decode()
                xml_line = f'<item><type>73736e63</type><code>{code:08x}</code><length>{len(payload.encode())}</length><data encoding="base64">{encoded_payload}</data></item>'

            self.reader.process_line(xml_line)

            if expected_state is not None:
                self.state_callback.assert_called_once_with(expected_state)
            else:
                self.state_callback.assert_not_called()

    def test_progress_information_handling(self):
        """Test progress information (prgr) handling."""
        # Progress format: start/current/end in RTP timestamps
        progress_info = "1000/5000/10000"
        encoded_data = base64.b64encode(progress_info.encode()).decode()
        xml_line = f'<item><type>73736e63</type><code>70726772</code><length>{len(progress_info.encode())}</length><data encoding="base64">{encoded_data}</data></item>'

        self.reader.process_line(xml_line)

        # Should not trigger state or metadata callbacks
        self.state_callback.assert_not_called()
        self.metadata_callback.assert_not_called()

    def test_volume_control_handling(self):
        """Test volume control (pvol) handling."""
        # Volume data (often binary/structured)
        volume_data = b"\x00\x00\x00\x50"  # Example volume data
        encoded_data = base64.b64encode(volume_data).decode()
        xml_line = f'<item><type>73736e63</type><code>70766f6c</code><length>{len(volume_data)}</length><data encoding="base64">{encoded_data}</data></item>'

        self.reader.process_line(xml_line)

        # Should handle without crashing
        self.state_callback.assert_not_called()
        self.metadata_callback.assert_not_called()

    def test_all_image_formats_detection(self):
        """Test detection of all supported image formats."""
        format_tests = [
            (b"\xff\xd8\xff\xe0", "jpg", "JPEG"),
            (b"\x89PNG\r\n\x1a\n", "png", "PNG"),
            (b"GIF87a", "gif", "GIF87a"),
            (b"GIF89a", "gif", "GIF89a"),
            (b"RIFF\x00\x00\x00\x00WEBP", "webp", "WebP"),
            (b"\x00\x00\x00\x20ftypheic", "heic", "HEIC"),
            (b"\x00\x00\x00\x20ftypmif1", "heif", "HEIF"),
            (b"\x12\x34\x56\x78", "bin", "Unknown"),
        ]

        for header, expected_ext, format_name in format_tests:
            self.metadata_callback.reset_mock()

            # Pad header to ensure minimum size
            image_data = header + b"\x00" * (20 - len(header)) if len(header) < 20 else header
            encoded_data = base64.b64encode(image_data).decode()

            self.reader._current_metadata = {"album": f"Test_{format_name}"}

            xml_line = f'<item><type>73736e63</type><code>50494354</code><length>{len(image_data)}</length><data encoding="base64">{encoded_data}</data></item>'

            with patch("builtins.open", create=True) as mock_open, patch("time.time", return_value=1234567890):

                self.reader.process_line(xml_line)

                # Calculate expected checksum for this image data
                import hashlib

                image_checksum = hashlib.md5(image_data).hexdigest()[:8]

                # Should detect correct format with checksum-based filename
                expected_filename = f"/tmp/cover_Test_{format_name}_{image_checksum}.{expected_ext}"
                mock_open.assert_called_once_with(expected_filename, "wb")

    def test_cover_art_deduplication(self):
        """Test that identical cover art is not regenerated."""
        # Test data
        jpeg_data = b"\xff\xd8\xff\xe0test"
        encoded_data = base64.b64encode(jpeg_data).decode()

        # Start a metadata bundle and add album info
        self.reader.process_line("<item><type>73736e63</type><code>6d647374</code><length>0</length></item>")
        album_data = base64.b64encode(b"Test Album").decode()
        self.reader.process_line(
            f'<item><type>636f7265</type><code>6173616c</code><length>10</length><data encoding="base64">{album_data}</data></item>'
        )

        xml_line = f'<item><type>73736e63</type><code>50494354</code><length>{len(jpeg_data)}</length><data encoding="base64">{encoded_data}</data></item>'

        # Calculate expected filename
        import hashlib

        checksum = hashlib.md5(jpeg_data).hexdigest()[:8]
        expected_filename = f"/tmp/cover_Test_Album_{checksum}.jpg"

        # First time - should create file
        with patch("builtins.open", create=True) as mock_open, patch(
            "os.path.exists", return_value=False
        ) as mock_exists:

            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            self.reader.process_line(xml_line)

            # Should try to create the file
            mock_exists.assert_called_with(expected_filename)
            mock_open.assert_called_once_with(expected_filename, "wb")
            mock_file.write.assert_called_once_with(jpeg_data)

        # Reset mocks for second call
        self.metadata_callback.reset_mock()

        # Second time with same data - should skip file creation
        with patch("builtins.open", create=True) as mock_open, patch(
            "os.path.exists", return_value=True
        ) as mock_exists:

            self.reader.process_line(xml_line)

            # Should check if file exists but not create it
            mock_exists.assert_called_with(expected_filename)
            mock_open.assert_not_called()  # File should not be opened for writing

            # Should still call metadata callback with existing path
            self.metadata_callback.assert_called_once()
            metadata = self.metadata_callback.call_args[0][0]
            assert metadata["cover_art_path"] == expected_filename


if __name__ == "__main__":
    pytest.main([__file__])
