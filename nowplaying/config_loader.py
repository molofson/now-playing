"""
Configuration loader for music discovery app.

Supports loading configuration from YAML files with environment variable overrides.
"""

import os
from typing import Optional

from .config import AppConfig, EnrichmentConfig

# Try to import yaml, but handle graceful fallback
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """
    Load configuration from file with environment variable overrides.
    
    Args:
        config_path: Path to YAML config file. Defaults to "config.yaml"
    
    Returns:
        AppConfig instance with loaded settings
    """
    # Start with default configuration
    config = AppConfig.create_default()
    
    # Try to load from file if YAML is available
    config_path = config_path or "config.yaml"
    if HAS_YAML and os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                
            if config_data:
                # Apply enrichment config if present
                if 'enrichment' in config_data:
                    enrich_data = config_data['enrichment']
                    config.enrichment = EnrichmentConfig(
                        lastfm_api_key=enrich_data.get('lastfm_api_key'),
                        discogs_user_token=enrich_data.get('discogs_user_token'),
                        musicbrainz_rate_limit=enrich_data.get('musicbrainz_rate_limit', 1.0),
                        discogs_rate_limit=enrich_data.get('discogs_rate_limit', 1.5),
                        lastfm_rate_limit=enrich_data.get('lastfm_rate_limit', 0.5),
                        cache_timeout=enrich_data.get('cache_timeout', 3600.0),
                        max_cache_size=enrich_data.get('max_cache_size', 1000),
                        enable_musicbrainz=enrich_data.get('enable_musicbrainz', True),
                        enable_discogs=enrich_data.get('enable_discogs', True),
                        enable_lastfm=enrich_data.get('enable_lastfm', True),
                        use_mock_data_on_failure=enrich_data.get('use_mock_data_on_failure', True),
                    )
                
                # Apply global config
                config.debug = config_data.get('debug', False)
                config.log_level = config_data.get('log_level', 'INFO')
                
        except Exception as e:
            # Log error but continue with defaults
            print(f"Warning: Could not load config from {config_path}: {e}")
    elif config_path and os.path.exists(config_path) and not HAS_YAML:
        print(f"Warning: YAML config file {config_path} found but PyYAML not installed. Using defaults.")
    
    # Apply environment variable overrides
    apply_env_overrides(config)
    
    return config


def apply_env_overrides(config: AppConfig) -> None:
    """Apply environment variable overrides to configuration."""
    
    # Enrichment API keys
    if os.getenv('LASTFM_API_KEY'):
        config.enrichment.lastfm_api_key = os.getenv('LASTFM_API_KEY')
    
    if os.getenv('DISCOGS_USER_TOKEN'):
        config.enrichment.discogs_user_token = os.getenv('DISCOGS_USER_TOKEN')
    
    # Global settings
    if os.getenv('DEBUG'):
        config.debug = os.getenv('DEBUG').lower() in ('true', '1', 'yes')
    
    if os.getenv('LOG_LEVEL'):
        config.log_level = os.getenv('LOG_LEVEL').upper()


def has_real_api_keys(config: AppConfig) -> bool:
    """Check if real API keys are configured (not placeholders)."""
    return bool(
        config.enrichment.lastfm_api_key and 
        config.enrichment.lastfm_api_key != "YOUR_LASTFM_API_KEY_HERE"
    ) or bool(
        config.enrichment.discogs_user_token and
        config.enrichment.discogs_user_token != "YOUR_DISCOGS_TOKEN_HERE"
    )


def print_config_status(config: AppConfig) -> None:
    """Print configuration status for debugging."""
    print("🎵 Music Discovery Configuration Status:")
    print(f"  Debug mode: {config.debug}")
    print(f"  Log level: {config.log_level}")
    print("\n🔌 Enrichment Services:")
    print(f"  MusicBrainz: {'✓ Enabled' if config.enrichment.enable_musicbrainz else '✗ Disabled'}")
    print(f"  Last.fm: {'✓ Enabled' if config.enrichment.enable_lastfm else '✗ Disabled'}")
    if config.enrichment.lastfm_api_key:
        if config.enrichment.lastfm_api_key == "YOUR_LASTFM_API_KEY_HERE":
            print("    ⚠️  Using mock data (no API key configured)")
        else:
            print("    ✓ Real API key configured")
    else:
        print("    ⚠️  Using mock data (no API key configured)")
    
    print(f"  Discogs: {'✓ Enabled' if config.enrichment.enable_discogs else '✗ Disabled'}")
    if config.enrichment.discogs_user_token:
        if config.enrichment.discogs_user_token == "YOUR_DISCOGS_TOKEN_HERE":
            print("    ⚠️  Using mock data (no token configured)")
        else:
            print("    ✓ Real token configured")
    else:
        print("    ⚠️  Using mock data (no token configured)")
    print()