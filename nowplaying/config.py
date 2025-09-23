"""
Configuration management for the now-playing application.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StateMonitorConfig:
    """Configuration for StateMonitor component."""

    # Timing configuration
    wait_timeout_seconds: float = 2.0
    thread_join_timeout: float = 1.0
    select_timeout: float = 0.1

    # Pipe configuration
    pipe_path: Optional[str] = None
    default_pipe_path: str = "/tmp/shairport-sync-metadata"

    # Retry and resilience
    max_retries: int = 3
    retry_delay_seconds: float = 1.0

    # Threading
    daemon_threads: bool = True

    def get_effective_pipe_path(self) -> str:
        """Get the effective pipe path, falling back to default if not set."""
        return self.pipe_path or self.default_pipe_path


@dataclass
class MetadataReaderConfig:
    """Configuration for metadata reader component."""

    # XML parsing
    max_xml_line_length: int = 8192
    max_base64_data_size: int = 1024 * 1024  # 1MB

    # Cover art handling
    cover_art_temp_dir: str = "/tmp"
    cover_art_prefix: str = "cover_"
    max_cover_art_size: int = 10 * 1024 * 1024  # 10MB

    # Error handling
    ignore_unknown_codes: bool = True
    log_parsing_errors: bool = True


@dataclass
class EnrichmentConfig:
    """Configuration for enrichment services."""

    # Service API keys (set these to enable real API calls)
    lastfm_api_key: Optional[str] = None
    discogs_user_token: Optional[str] = None
    
    # Rate limiting
    musicbrainz_rate_limit: float = 1.0  # seconds between requests
    discogs_rate_limit: float = 1.5  # seconds between requests
    lastfm_rate_limit: float = 0.5  # seconds between requests
    
    # Timeouts
    request_timeout: float = 10.0  # seconds
    
    # Cache settings
    cache_timeout: float = 3600.0  # 1 hour cache timeout
    max_cache_size: int = 1000  # max cached enrichments
    
    # Service enablement
    enable_musicbrainz: bool = True
    enable_discogs: bool = True
    enable_lastfm: bool = True
    
    # Fallback behavior
    use_mock_data_on_failure: bool = True


@dataclass
class UIConfig:
    """Configuration for UI components."""

    # Display settings
    target_fps: int = 30
    font_size_log: int = 20
    font_size_meta: int = 24
    font_size_title: int = 28

    # Layout
    margin: int = 16
    max_log_lines: int = 500
    visible_log_lines: int = 40

    # Colors (RGB tuples)
    color_dark_bg: tuple = (10, 10, 14)
    color_text: tuple = (230, 230, 230)
    color_dim_text: tuple = (170, 170, 170)
    color_accent: tuple = (120, 170, 255)
    color_error: tuple = (255, 120, 120)
    color_warn: tuple = (255, 210, 140)
    color_debug: tuple = (140, 160, 255)
    color_divider: tuple = (28, 28, 36)

    # Cover art caching
    cover_cache_size: int = 10  # Number of covers to cache


@dataclass
class AppConfig:
    """Main application configuration container."""

    state_monitor: StateMonitorConfig = field(default_factory=StateMonitorConfig)
    metadata_reader: MetadataReaderConfig = field(default_factory=MetadataReaderConfig)
    enrichment: EnrichmentConfig = field(default_factory=EnrichmentConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    # Global settings
    debug: bool = False
    log_level: str = "INFO"

    @classmethod
    def create_default(cls) -> "AppConfig":
        """Create a default configuration instance."""
        return cls()

    @classmethod
    def create_for_testing(cls) -> "AppConfig":
        """Create a configuration suitable for testing."""
        config = cls()
        config.state_monitor.wait_timeout_seconds = 0.1
        config.state_monitor.thread_join_timeout = 0.1
        config.state_monitor.select_timeout = 0.01
        config.debug = True
        config.log_level = "DEBUG"
        return config
