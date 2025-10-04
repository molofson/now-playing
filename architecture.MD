# Now Playing — Architecture & Supported Features

This document summarizes the current architecture, supported features, integration points, and a small prioritized TODO list for new enrichment services and feature work.

## High-level purpose

Now Playing is an AirPlay metadata display and enrichment application that reads shairport-sync metadata and shows a touch-friendly display with multiple enrichment panels. It includes an enrichment engine that aggregates metadata from multiple external services and an MCP server for programmatic access.

## Key components

- CLI entry points
  - `nowplaying-display` -> `nowplaying.cli:display_main` (launch UI)
  - `nowplaying-mcp` -> `nowplaying.cli:mcp_main` (run MCP stdio server)

- Metadata input
  - Shairport-sync XML pipe reader: `nowplaying/metadata_reader.py` (class `ShairportSyncPipeReader`)
  - Handles DMAP codes, ssnc state codes, base64 payloads (cover art), saves cover art to `/tmp/cover_<album>_<checksum>.<ext>`, emits metadata bundles and playback state callbacks.

- Enrichment engine
  - `nowplaying/enrichment/engine.py` -> `EnrichmentEngine` and global `enrichment_engine`.
  - Manages registered `EnrichmentService` implementations, caching (1 hour), threaded execution, rate-limits, and enrichment callbacks.
  - Auto-registers built-in services at startup and enables/disables them based on environment variables (API keys).

- Enrichment services (implemented)
  - MusicBrainz — `nowplaying/enrichment/musicbrainz_service.py` (no token needed)
  - Discogs — `nowplaying/enrichment/discogs_service.py` (requires `DISCOGS_API_TOKEN`, auto-disabled if missing)
  - Last.fm — `nowplaying/enrichment/lastfm_service.py` (requires `LASTFM_API_KEY`, auto-disabled if missing)
  - Setlist.fm — `nowplaying/enrichment/setlistfm_service.py` (requires `SETLISTFM_API_KEY`, auto-disabled if missing)
  - Genius — `nowplaying/enrichment/genius_service.py` (optional `GENIUS_API_KEY`)
  - Songfacts — `nowplaying/enrichment/songfacts_service.py` (enabled by default)
  - AllMusic — `nowplaying/enrichment/allmusic_service.py` (enabled by default)
  - Pitchfork — `nowplaying/enrichment/pitchfork_service.py` (implemented, default-disabled)
  - Songkick — `nowplaying/enrichment/songkick_service.py` (implemented)

- Data model
  - `nowplaying/enrichment/base.py` defines `EnrichmentData` and `EnrichmentRequest`.
  - `EnrichmentData` includes cross-service IDs, artist bio/tags, similar artists, album reviews, credits, lyrics, tour dates, cover art URLs, scrobble/popularity metrics, last_updated map and service_errors.

- Panels / UI
  - Panels are modular and registered in `nowplaying/panels/registry.py`.
  - Provided panels include: Now Playing, Cover Art, Artist Info, Album Info, Discography, Social Stats, Lyrics, VU Meter, Service Status, Debug, Enrichment Log Buffer, and more.
  - Panel files live in `nowplaying/panels/`.

- MCP (Model Context Protocol) server
  - `nowplaying/mcp_server.py` exposes at least the `enrich_music` tool.
  - Input: {artist, album?, title?}
  - Output: `MusicEnrichmentResult` (pydantic model) with many `EnrichmentData` fields serialized to JSON.

- Tests & CI
  - Tests use `pytest`. Integration tests are marked `@pytest.mark.integration` and are skipped in CI.
  - `Makefile` targets: `make test` (full), `make test-ci` (skips integration tests). CI uses `make test-ci`.

## How services are enabled

- The engine checks environment variables at startup for tokens/keys and disables services that require keys if they're missing.
- See `EnrichmentEngine._register_builtin_services` in `nowplaying/enrichment/engine.py`.

## Exposed data fields (selected)

- Cross-service IDs: `musicbrainz_artist_id`, `musicbrainz_album_id`, `musicbrainz_track_id`, `discogs_artist_id`, `discogs_release_id`, `spotify_artist_id`, `spotify_album_id` (placeholders)
- Artist: `artist_bio`, `artist_tags`, `artist_images`, `similar_artists`, `artist_discography`
- Album: `album_reviews`, `album_credits`, `cover_art_urls`
- Track: `song_lyrics`, `song_annotations`
- Discovery: `tour_dates`, `recent_releases`
- Social: `scrobble_count`, `popularity_score`, `user_tags`
- Service metadata: `last_updated`, `service_errors`

(For complete field definitions, see `nowplaying/enrichment/base.py`.)

## Prioritized TODOs (short-term roadmap)

1. High priority
   - Implement Spotify enrichment service (OAuth Client Credentials; fetch artist/album IDs, audio-features & popularity). This will add `spotify_artist_id`/`spotify_album_id` population and audio-feature data for UI panels.
   - Implement AcoustID/Chromaprint fingerprinting service for track identification when metadata is minimal.

2. Medium priority
   - Add lyrics provider fallback strategy: try Genius (if API key), then Songfacts, then a free fallback.
   - Add Bandsintown or Songkick enrichment to improve tour/concert data (Songkick file exists; evaluate completeness).

3. Lower priority / optional
   - Apple Music / Deezer integrations (commercial or OAuth flows) — consider licensing and API costs.
   - Improve caching semantics (per-service TTLs, persisted cache storage).
   - Add telemetry/metrics endpoint for enrichment success rates.

## Implementation notes and pointers

- To add a new enrichment service:
  1. Implement subclass of `EnrichmentService` in `nowplaying/enrichment/`.
  2. Update `EnrichmentEngine._register_builtin_services` to construct and optionally configure (set API keys) the new service.
  3. Add unit tests under `tests/` and integration tests in `tests/` marked `@pytest.mark.integration` if they require external API calls.
  4. Update README and `architecture.MD` with configuration examples and environment variable names.

- MCP client example (quick): call stdio MCP server with `enrich_music` tool; see `nowplaying/mcp_server.py` for tool name and parameters.

## Where to look (file pointers)

- CLI & entry points: `nowplaying/cli.py`, `pyproject.toml` (project.scripts)
- Metadata reader: `nowplaying/metadata_reader.py`
- Enrichment engine: `nowplaying/enrichment/engine.py`
- Enrichment base & services: `nowplaying/enrichment/base.py`, `nowplaying/enrichment/*.py`
- Panels: `nowplaying/panels/` (e.g. `nowplaying/panels/now_playing_panel.py`)
- MCP: `nowplaying/mcp_server.py`
- Tests: `tests/` and Makefile targets

---

Generated by the code review session on behalf of the project. Update this file as planning decisions evolve.
