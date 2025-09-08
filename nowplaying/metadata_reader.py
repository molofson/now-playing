"""
Shairport-sync metadata reader for parsing XML format metadata from pipes.
"""

import base64
import hashlib
import re
import struct
import uuid
from typing import Callable, Dict

from .module_registry import module_registry
from .playback_state import PlaybackState


class MetadataParsingError(Exception):
    """Specific error for metadata parsing issues."""

    pass


class InvalidXMLError(MetadataParsingError):
    """Error for invalid XML structure."""

    pass


class Base64DecodeError(MetadataParsingError):
    """Error for base64 decoding issues."""

    pass


class UTF8DecodeError(MetadataParsingError):
    """Error for UTF-8 decoding issues."""

    pass


# Register the shairport-sync pipe reader module
module_registry.register_module(
    name="shairport",
    description="Shairport-sync XML metadata pipe reader",
    logger_name="shairport",
    debug_flag="--debug-shairport",
    enabled=True,
    category="input",
)

# Get logger for this module
log = module_registry.get_module_info("shairport")["logger"]


class ShairportSyncPipeReader:
    """Handles parsing and processing of shairport-sync metadata from XML format."""

    def __init__(
        self,
        state_callback: Callable[[PlaybackState], None],
        metadata_callback: Callable[[dict], None],
    ):
        """Initialize metadata reader with callbacks for state and metadata updates."""
        self._state_callback = state_callback
        self._metadata_callback = metadata_callback
        self._current_metadata: Dict[str, str] = {}
        self._metadata_bundle_active = False
        self._sequence_number = 0
        self._current_metadata_id = None

        # Core metadata codes from iTunes/AirPlay (DMAP format)
        self._core_metadata_codes = {
            0x6173616C: "album",  # 'asal' - Album Name
            0x61736172: "artist",  # 'asar' - Artist
            0x6D696E6D: "title",  # 'minm' - Title
            0x6173676E: "genre",  # 'asgn' - Genre
            0x61736370: "composer",  # 'ascp' - Composer
            0x6173636D: "comment",  # 'ascm' - Comment
            0x61736474: "description",  # 'asdt' - Description
            0x61737374: "sortartist",  # 'asst' - Sort Artist
            0x6173736E: "sorttitle",  # 'assn' - Sort Title
            # Additional iTunes/Apple Music metadata codes
            0x6D696B64: "kind",  # 'mikd' - Media Kind
            0x61736272: "bitrate",  # 'asbr' - Bit Rate
            0x6173636F: "compilation",  # 'asco' - Compilation
            0x6D656961: "media_kind",  # 'meia' - Media Kind (alternative)
            0x61736461: "date_added",  # 'asda' - Date Added
            0x6173646D: "date_modified",  # 'asdm' - Date Modified
            0x61736463: "disc_count",  # 'asdc' - Disc Count
            0x6173646E: "disc_number",  # 'asdn' - Disc Number
            0x61736571: "eq_preset",  # 'aseq' - EQ Preset
            0x61737276: "relative_volume",  # 'asrv' - Relative Volume
            0x61737372: "sample_rate",  # 'assr' - Sample Rate
            0x6173737A: "size",  # 'assz' - Size
            0x61737370: "stop_time",  # 'assp' - Stop Time
            0x6173746D: "time_modified",  # 'astm' - Time Modified
            0x61737463: "track_count",  # 'astc' - Track Count
            0x6173746E: "track_number",  # 'astn' - Track Number
            0x61737572: "user_rating",  # 'asur' - User Rating
            # Metadata start/end markers (can appear in both core and ssnc contexts)
            0x6D647374: "metadata_start",  # 'mdst' - Metadata Start
            0x6D64656E: "metadata_end",  # 'mden' - Metadata End
            # Additional Apple Music/iTunes extended metadata
            0x61654D6B: "apple_extras_make",  # 'aeMk' - Apple Extras Make
            0x61654D58: "apple_extras_mix",  # 'aeMX' - Apple Extras Mix
            0x61737063: "podcast",  # 'aspc' - Song Podcast
            0x61737269: "rating_index",  # 'asri' - Song Rating Index
            0x61654353: "apple_content_source",  # 'aeCS' - Apple Extras Content Source
            0x61655253: "apple_rating_source",  # 'aeRS' - Apple Extras Rating Source
            0x61655244: "apple_rating_date",  # 'aeRD' - Apple Extras Rating Date
            0x61655250: "apple_rating_policy",  # 'aeRP' - Apple Extras Rating Policy
            0x61655255: "apple_rating_url",  # 'aeRU' - Apple Extras Rating URL
            0x61736B70: "keep_flag",  # 'askp' - Song Keep
            0x61736163: "audio_codec",  # 'asac' - Song Audio Codec
            0x61736B64: "keep_date",  # 'askd' - Song Keep Date
            0x61736573: "equalizer_setting",  # 'ases' - Song Equalizer Setting
            0x6165434D: "apple_content_manager",  # 'aeCM' - Apple Extras Content Manager
            0x61737273: "random_seed",  # 'asrs' - Song Random Seed
            0x61736C72: "logic_rule",  # 'aslr' - Song Logic Rule
            0x61736173: "auto_skip",  # 'asas' - Song Auto Skip
            0x61654773: "apple_genre_source",  # 'aeGs' - Apple Extras Genre Source
            0x61656C73: "apple_language_source",  # 'aels' - Apple Extras Language Source
            # AirPlay specific metadata
            0x616A616C: "airplay_audio_latency",  # 'ajal' - AirPlay Audio Latency
            0x616A6341: "airplay_connection_audio",  # 'ajcA' - AirPlay Connection Audio
            0x6177726B: "airplay_work",  # 'awrk' - AirPlay Work
            0x616D766D: "airplay_volume_master",  # 'amvm' - AirPlay Media Volume Master
            0x616D7663: "airplay_volume_current",  # 'amvc' - AirPlay Media Volume Current
            0x616D766E: "airplay_volume_normal",  # 'amvn' - AirPlay Media Volume Normal
            0x616A7577: "airplay_user_workflow",  # 'ajuw' - AirPlay User Workflow
            0x616A4156: "airplay_av_sync",  # 'ajAV' - AirPlay Audio/Video sync
            0x616A4154: "airplay_audio_track",  # 'ajAT' - AirPlay Audio Track
            0x616A4145: "airplay_audio_encoding",  # 'ajAE' - AirPlay Audio Encoding
            0x616A4153: "airplay_audio_stream",  # 'ajAS' - AirPlay Audio Stream
        }

        # SSNC (shairport-sync) codes for state changes
        self._ssnc_state_codes = {
            0x70637374: "pcst",  # 'pcst' - Play/Control State
            0x70656E64: "pend",  # 'pend' - Play Session End
            0x6D647374: "mdst",  # 'mdst' - Metadata Start
            0x6D64656E: "mden",  # 'mden' - Metadata End
            0x70626567: "pbeg",  # 'pbeg' - Play Session Begin
            0x70666C73: "pfls",  # 'pfls' - Play Stream Flush
            0x70666672: "pffr",  # 'pffr' - Play Stream First Frame Received
            0x7072736D: "prsm",  # 'prsm' - Play Stream Resume
            0x50494354: "PICT",  # 'PICT' - Picture Data
            0x70726772: "prgr",  # 'prgr' - Progress Information
            0x61637265: "acre",  # 'acre' - Active Remote Token
            0x64616964: "daid",  # 'daid' - DACP ID
            0x636C6970: "clip",  # 'clip' - Client IP
            0x73766970: "svip",  # 'svip' - Server IP
            0x61626567: "abeg",  # 'abeg' - Active Begin
            0x61656E64: "aend",  # 'aend' - Active End
        }

        # Common DMAP code descriptions for unknown codes
        self._dmap_descriptions = {
            # Common iTunes/Music metadata
            "mper": "Media Player Persistent ID",
            "mpco": "Media Player Container",
            "mlit": "Media List Item",
            "aply": "Apple Playlist",
            "apso": "Apple Playlist Sort Order",
            "arif": "Artist Information",
            "daap": "Digital Audio Access Protocol",
            "dmap": "Digital Media Access Protocol",
            "mstt": "Media Server Status",
            "muty": "Media Server Update Type",
            "mtco": "Media Server Total Count",
            "mrco": "Media Server Return Count",
            "mlcl": "Media List Container List",
            "mlog": "Media Server Login",
            "mlid": "Media List ID",
            "msur": "Media Server Update Response",
            "msdc": "Media Server Database Count",
            "msix": "Media Server Index",
            "msal": "Media Server Album List",
            "msar": "Media Server Artist List",
            "msbr": "Media Server Browse",
            "msqy": "Media Server Query",
            "msrs": "Media Server Resolve",
            "mstm": "Media Server Timeout",
            "msts": "Media Server Status String",
            "msup": "Media Server Update",
            "mtcl": "Media Server Container List",
            "mudl": "Media Server Database List",
            "mute": "Media Server Edit",
            "mupd": "Media Server Update",
            "musr": "Media Server User",
            "mccr": "Media Content Code Response",
            "mcna": "Media Content Codes Name",
            "mcnm": "Media Content Codes Number",
            "mcty": "Media Content Codes Type",
            "mdcl": "Media Dictionary",
            "meds": "Media Edit Status",
            "mikd": "Media Item Kind",
            "minm": "Media Item Name",
            "miid": "Media Item ID",
            "mimc": "Media Item Media Count",
            "mctc": "Media Container Total Count",
            "aeNV": "Audio Equalizer",
            "aeMK": "Audio Equalizer Make",
            "aeMk": "Apple Extras Make",
            "aeMX": "Apple Extras Mix",
            "aeCS": "Apple Extras Content Source",
            "aeRS": "Apple Extras Rating Source",
            "aeRD": "Apple Extras Rating Date",
            "aeRP": "Apple Extras Rating Policy",
            "aeRU": "Apple Extras Rating URL",
            "aeCM": "Apple Extras Content Manager",
            "aeGs": "Apple Extras Genre Source",
            "aels": "Apple Extras Language Source",
            # Additional DMAP codes from real-world usage
            "asdk": "Song Data Kind",
            "asbt": "Song Beats Per Minute",
            "agrp": "Album Grouping",
            "aeSI": "Apple Extras Store ID",
            "aeAI": "Apple Extras Album ID",
            "aePI": "Apple Extras Playlist ID",
            "asct": "Song Category",
            "ascn": "Song Content Rating",
            "ascr": "Song Copyright",
            "aeHV": "Apple Extras Has Video",
            # Additional Apple Music/iTunes DMAP codes
            "aeSN": "Apple Extras Store Name",
            "aeEN": "Apple Extras Episode Number",
            "aeES": "Apple Extras Episode Sort",
            "aeSU": "Apple Extras Store URL",
            "aeGH": "Apple Extras Gapless Heuristic",
            "aeGD": "Apple Extras Gapless Data",
            "aeGU": "Apple Extras Gapless Duration",
            "aeGR": "Apple Extras Gapless Resy",
            "aeGE": "Apple Extras Gapless Encoding",
            "asaa": "Song Album Artist",
            "asgp": "Song Gapless",
            "mext": "Media File Extension",
            "ased": "Song Episode ID",
            "asdr": "Song Date Released",
            "ashp": "Song Has Been Played",
            "assa": "Song Sort Album",
            "assl": "Song Sort Album Artist",
            "assu": "Song Sort User",
            "assc": "Song Sort Composer",
            "asss": "Song Sort Show",
            "asbk": "Song Bookmark",
            "aeCR": "Apple Extras Content Rating",
            "asai": "Song Album ID",
            "asls": "Song Last Skip",
            "aeHD": "Apple Extras HD",
            "meip": "Media Edit Commands",
            "aspl": "Song Play Count",
            "aeSE": "Apple Extras Season",
            "aeDV": "Apple Extras Digital Video",
            "aeDP": "Apple Extras Digital Purchase",
            "aeDR": "Apple Extras Digital Rental",
            "aeND": "Apple Extras Network Name",
            "aeK1": "Apple Extras Key 1",
            "aeK2": "Apple Extras Key 2",
            "aeDL": "Apple Extras Download",
            "aeFA": "Apple Extras Format Audio",
            "aeXD": "Apple Extras Extra Data",
        }

        # XML parsing state
        self._current_item = None
        self._collecting_data = False
        self._data_buffer = ""

    def process_line(self, line: str) -> None:
        """Process a single line of metadata output in XML format."""
        line = line.strip()
        if not line:
            return

        # Handle XML item start
        if line.startswith("<item>"):
            self._start_new_item(line)
        # Handle data collection
        elif self._collecting_data:
            if line.startswith("</data></item>"):
                self._complete_current_item()
            elif line.endswith("</data></item>"):
                # Data ends on this line
                data_part = line.replace("</data></item>", "")
                if data_part:
                    self._data_buffer += data_part
                self._complete_current_item()
            else:
                # Continue collecting data
                self._data_buffer += line
        # Handle item end without data
        elif line == "</item>" and self._current_item:
            self._complete_current_item()
        # Handle data start
        elif line.startswith('<data encoding="base64">'):
            self._start_data_collection(line)
        else:
            # Unhandled line
            log.debug("Unhandled line: %s", line)

    def _start_new_item(self, line: str) -> None:
        """Start processing a new XML item."""
        try:
            # Extract type, code, and length from the item line
            type_match = re.search(r"<type>([0-9a-fA-F]{8})</type>", line)
            code_match = re.search(r"<code>([0-9a-fA-F]{8})</code>", line)
            length_match = re.search(r"<length>(\d+)</length>", line)

            if not (type_match and code_match and length_match):
                raise InvalidXMLError(f"Invalid metadata item format: {line}")

            self._current_item = {
                "type": int(type_match.group(1), 16),
                "code": int(code_match.group(1), 16),
                "length": int(length_match.group(1)),
            }

            # Reset data collection state
            self._collecting_data = False
            self._data_buffer = ""

            # Check if this line also contains data or ends immediately
            if "</item>" in line:
                # Single line item with embedded data
                data_match = re.search(r'<data encoding="base64">([^<]+)</data>', line)
                if data_match:
                    self._data_buffer = data_match.group(1)
                self._complete_current_item()
            elif '<data encoding="base64">' in line:
                # Data starts on same line
                self._start_data_collection(line)

        except InvalidXMLError as e:
            log.warning("XML parsing error: %s", e)
            self._reset_item_state()
        except (ValueError, OverflowError) as e:
            log.warning("Invalid number in XML item: %s - %s", line.strip(), e)
            self._reset_item_state()
        except Exception as e:
            log.error("Unexpected error starting new item: %s - %s", line.strip(), e)
            self._reset_item_state()

    def _start_data_collection(self, line: str) -> None:
        """Start collecting base64 data."""
        self._collecting_data = True

        # Extract any data that might be on the same line
        if '<data encoding="base64">' in line:
            data_start = line.find('<data encoding="base64">') + len('<data encoding="base64">')
            data_part = line[data_start:]

            # Check if data also ends on this line
            if "</data></item>" in data_part:
                self._data_buffer = data_part.replace("</data></item>", "")
                self._complete_current_item()
            else:
                self._data_buffer = data_part

    def _complete_current_item(self) -> None:
        """Complete processing of the current XML item."""
        if not self._current_item:
            return

        try:
            type_code = self._current_item["type"]
            code = self._current_item["code"]
            length = self._current_item["length"]

            # Decode payload if present
            payload = b""
            if length > 0 and self._data_buffer:
                try:
                    payload = base64.b64decode(self._data_buffer)
                except Exception as e:
                    raise Base64DecodeError(f"Failed to decode base64 data: {e}") from e

            # Process based on type
            if type_code == 0x636F7265:  # 'core' - iTunes metadata
                self._handle_core_metadata(code, payload)
            elif type_code == 0x73736E63:  # 'ssnc' - shairport-sync metadata
                self._handle_ssnc_metadata(code, payload)
            else:
                log.debug("Unknown metadata type: 0x%08x", type_code)

        except MetadataParsingError as e:
            log.error("Metadata parsing error: %s", e)
        except Exception as e:
            log.error("Unexpected error completing item: %s", e)
        finally:
            self._reset_item_state()

    def _handle_core_metadata(self, code: int, payload: bytes) -> None:
        """Handle core iTunes/AirPlay metadata."""
        if code in self._core_metadata_codes:
            field_name = self._core_metadata_codes[code]
            try:
                # Most metadata is UTF-8 encoded text
                value = payload.decode("utf-8").strip()
                # Check if the decoded string contains null characters or other control chars
                # which indicates binary data that shouldn't be treated as text
                if "\x00" in value or any(ord(c) < 32 and c not in "\n\r\t" for c in value):
                    log.debug("Core metadata %s: <binary data, %d bytes>", field_name, len(payload))
                else:
                    self._current_metadata[field_name] = value
                    log.debug("Core metadata %s: %s", field_name, value)
            except UnicodeDecodeError as e:
                # Some fields contain binary data (timestamps, IDs, etc.)
                log.debug("Core metadata %s: <binary data, %d bytes> - %s", field_name, len(payload), e)
        else:
            # Convert hex code to ASCII for better readability and try to decode value
            try:
                import struct

                ascii_code = struct.pack(">I", code).decode("ascii")
                description = self._dmap_descriptions.get(ascii_code)
                if description:
                    # Known DMAP field - don't show hex
                    try:
                        value = payload.decode("utf-8").strip()
                        # Check for binary data disguised as text
                        if "\x00" in value or any(ord(c) < 32 and c not in "\n\r\t" for c in value):
                            log.debug("DMAP %s (%s): <binary data, %d bytes>", ascii_code, description, len(payload))
                        else:
                            log.debug("DMAP %s (%s): %s", ascii_code, description, value)
                    except UnicodeDecodeError as e:
                        log.debug(
                            "DMAP %s (%s): <binary data, %d bytes> - %s", ascii_code, description, len(payload), e
                        )
                else:
                    # Unknown DMAP field - show hex
                    try:
                        value = payload.decode("utf-8").strip()
                        # Check for binary data disguised as text
                        if "\x00" in value or any(ord(c) < 32 and c not in "\n\r\t" for c in value):
                            log.debug(
                                "Unknown DMAP 0x%08x ('%s'): <binary data, %d bytes>", code, ascii_code, len(payload)
                            )
                        else:
                            log.debug("Unknown DMAP 0x%08x ('%s'): %s", code, ascii_code, value)
                    except UnicodeDecodeError:
                        log.debug("Unknown DMAP 0x%08x ('%s'): <binary data, %d bytes>", code, ascii_code, len(payload))
            except (UnicodeDecodeError, struct.error):
                try:
                    value = payload.decode("utf-8").strip()
                    log.debug("Unknown core metadata code: 0x%08x: %s", code, value)
                except UnicodeDecodeError:
                    log.debug("Unknown core metadata code: 0x%08x: <binary data, %d bytes>", code, len(payload))

    def _handle_ssnc_metadata(self, code: int, payload: bytes) -> None:
        """Handle shairport-sync specific metadata and state changes."""
        if code == 0x70637374:  # 'pcst' - Play/Control State
            self._handle_play_control_state(payload)
        elif code == 0x6D647374:  # 'mdst' - Metadata Start
            self._handle_metadata_start(payload)
        elif code == 0x6D64656E:  # 'mden' - Metadata End
            self._handle_metadata_end(payload)
        elif code == 0x70626567:  # 'pbeg' - Play Session Begin
            log.debug("Play session begin")
            self._state_callback(PlaybackState.PLAYING)
        elif code == 0x70656E64:  # 'pend' - Play Session End
            log.debug("Play session end")
            self._state_callback(PlaybackState.STOPPED)
        elif code == 0x7072736D:  # 'prsm' - Play Stream Resume
            log.debug("Play stream resume")
            self._state_callback(PlaybackState.PLAYING)
        elif code == 0x70666C73:  # 'pfls' - Play Stream Flush
            log.debug("Play stream flush")
            # Flush typically indicates buffering/waiting
        elif code == 0x70666672:  # 'pffr' - Play Stream First Frame Received
            log.debug("Play stream first frame received")
            # First frame received indicates buffering complete, playback starting
        elif code == 0x7063656E:  # 'pcen' - Play Stream Connection End
            log.debug("Play stream connection end")
            # Connection end, typically before new session
        elif code == 0x50494354:  # 'PICT' - Picture Data
            self._handle_picture_data(payload)
        elif code == 0x70726772:  # 'prgr' - Progress Information
            self._handle_progress_info(payload)
        elif code == 0x61637265:  # 'acre' - Active Remote Token
            self._handle_active_remote_token(payload)
        elif code == 0x64616964:  # 'daid' - DACP ID
            self._handle_dacp_id(payload)
        elif code == 0x636C6970:  # 'clip' - Client IP Address
            self._handle_client_ip(payload)
        elif code == 0x73766970:  # 'svip' - Server IP Address
            self._handle_server_ip(payload)
        elif code == 0x61626567:  # 'abeg' - Enter Active State
            log.debug("Enter active state")
            # This indicates the player is becoming active/ready
        elif code == 0x61656E64:  # 'aend' - Exit Active State
            log.debug("Exit active state")
            self._state_callback(PlaybackState.NO_SESSION)
        else:
            # Convert code to 4-character string for logging
            code_str = struct.pack(">I", code).decode("ascii", errors="ignore")
            log.debug("Unknown ssnc code: %s (0x%08x)", code_str, code)

    def _handle_play_control_state(self, payload: bytes) -> None:
        """Handle play/control state changes."""
        try:
            # pcst payload is typically "0" or "1" as ASCII
            state_str = payload.decode("ascii").strip()
            if state_str == "1":
                log.debug("Play control state: playing")
                self._state_callback(PlaybackState.PLAYING)
            elif state_str == "0":
                log.debug("Play control state: paused")
                self._state_callback(PlaybackState.PAUSED)
            else:
                log.debug("Unknown play control state: %s", state_str)
        except UnicodeDecodeError:
            log.warning("Failed to decode play control state payload")

    def _handle_metadata_start(self, payload: bytes) -> None:
        """Handle start of metadata bundle."""
        log.debug("Metadata bundle start")
        self._metadata_bundle_active = True
        self._current_metadata.clear()

        # Create new metadata ID and increment sequence number
        self._current_metadata_id = str(uuid.uuid4())
        self._sequence_number += 1

        # Initialize metadata structure with ID and sequence
        self._current_metadata["metadata_id"] = self._current_metadata_id
        self._current_metadata["sequence_number"] = str(self._sequence_number)

        # Payload contains RTP timestamp if available
        if payload:
            try:
                # RTP timestamp is typically a hex string
                rtp_timestamp = payload.decode("ascii").strip()
                log.debug("Metadata RTP timestamp: %s", rtp_timestamp)
                self._current_metadata["rtp_timestamp"] = rtp_timestamp
            except UnicodeDecodeError:
                pass

    def _handle_metadata_end(self, payload: bytes) -> None:
        """Handle end of metadata bundle."""
        log.debug("Metadata bundle end")
        if self._metadata_bundle_active and self._current_metadata:
            # Dispatch the completed metadata
            log.info("Dispatching metadata: %s", self._current_metadata)
            self._metadata_callback(self._current_metadata.copy())

        self._metadata_bundle_active = False
        # Don't clear current_metadata here - preserve it for cover art updates

        # Payload contains RTP timestamp if available - log it if present
        if payload:
            try:
                rtp_timestamp = payload.decode("ascii").strip()
                log.debug("Metadata end RTP timestamp: %s", rtp_timestamp)
            except UnicodeDecodeError:
                pass

    def _handle_progress_info(self, payload: bytes) -> None:
        """Handle progress information."""
        try:
            progress_str = payload.decode("ascii").strip()
            log.debug("Progress info: %s", progress_str)
            # Progress format is typically "start/current/end" RTP timestamps
        except UnicodeDecodeError:
            log.debug("Failed to decode progress info payload")

    def _handle_active_remote_token(self, payload: bytes) -> None:
        """Handle Active Remote token for remote control."""
        try:
            token = payload.decode("ascii").strip()
            log.debug("Active Remote token: %s", token)
            # This token is used for remote control of the source
        except UnicodeDecodeError:
            log.debug("Failed to decode Active Remote token")

    def _handle_dacp_id(self, payload: bytes) -> None:
        """Handle DACP (Digital Audio Control Protocol) ID."""
        try:
            dacp_id = payload.decode("ascii").strip()
            log.debug("DACP ID: %s", dacp_id)
            # Used to identify the source for remote control
        except UnicodeDecodeError:
            log.debug("Failed to decode DACP ID")

    def _handle_client_ip(self, payload: bytes) -> None:
        """Handle client IP address."""
        try:
            client_ip = payload.decode("ascii").strip()
            log.debug("Client IP: %s", client_ip)
            # IP address of the device sending audio
        except UnicodeDecodeError:
            log.debug("Failed to decode client IP")

    def _handle_server_ip(self, payload: bytes) -> None:
        """Handle server IP address."""
        try:
            server_ip = payload.decode("ascii").strip()
            log.debug("Server IP: %s", server_ip)
            # IP address of this shairport-sync instance
        except UnicodeDecodeError:
            log.debug("Failed to decode server IP")

    def _handle_picture_data(self, payload: bytes) -> None:
        """Handle album art/cover art picture data."""
        if not payload:
            log.debug("Empty picture data received")
            return

        log.debug("Picture data received, length %d bytes", len(payload))

        # Detect image format based on magic bytes
        file_extension = "bin"  # fallback
        if payload.startswith(b"\xff\xd8\xff"):
            file_extension = "jpg"
        elif payload.startswith(b"\x89PNG\r\n\x1a\n"):
            file_extension = "png"
        elif payload.startswith(b"GIF8"):
            file_extension = "gif"
        elif payload.startswith(b"RIFF") and b"WEBP" in payload[:12]:
            file_extension = "webp"
        elif payload.startswith(b"\x00\x00\x00") and b"ftypheic" in payload[:20]:
            file_extension = "heic"
        elif payload.startswith(b"\x00\x00\x00") and b"ftypmif1" in payload[:20]:
            file_extension = "heif"

        # Generate filename with checksum and album name
        import os
        import re

        # Calculate checksum of the image data (truncated to 8 characters)
        image_checksum = hashlib.md5(payload).hexdigest()[:8]

        # Get album name from current metadata, sanitize for filename
        album_name = self._current_metadata.get("album", "unknown_album")
        # Remove or replace characters that aren't safe for filenames
        album_name = re.sub(r"[^\w\-_\.]", "_", album_name)
        # Limit length to avoid overly long filenames
        album_name = album_name[:30]  # Reduced to make room for checksum

        filename = f"/tmp/cover_{album_name}_{image_checksum}.{file_extension}"

        # Check if file already exists with same checksum - avoid regenerating
        if os.path.exists(filename):
            log.debug("Cover art already exists: %s", filename)
            # Only update cover art path in current metadata if we have a complete metadata bundle
            if self._current_metadata and self._current_metadata_id:
                # Increment sequence number for cover art update
                self._sequence_number += 1
                self._current_metadata["sequence_number"] = str(self._sequence_number)
                self._current_metadata["cover_art_path"] = filename
                log.info("Dispatching metadata with existing cover art: %s", self._current_metadata)
                self._metadata_callback(self._current_metadata.copy())
            else:
                log.debug("No current metadata to update with existing cover art path")
            return

        try:
            with open(filename, "wb") as f:
                f.write(payload)
            log.info("Cover art saved to: %s", filename)

            # Only update metadata if we have a complete bundle
            if self._current_metadata and self._current_metadata_id:
                # Increment sequence number for cover art update
                self._sequence_number += 1
                self._current_metadata["sequence_number"] = str(self._sequence_number)
                self._current_metadata["cover_art_path"] = filename
                log.info("Dispatching metadata with cover art: %s", self._current_metadata)
                self._metadata_callback(self._current_metadata.copy())
            else:
                log.debug("No current metadata to update with cover art path")

        except Exception as e:
            log.error("Failed to save cover art: %s", e)

    def _reset_item_state(self) -> None:
        """Reset the current item state to prepare for next item."""
        self._current_item = None
        self._collecting_data = False
        self._data_buffer = ""
