"""
Song Enrichment panel implementation.

Displays track-specific information and enrichment data.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class SongEnrichmentPanel(ContentPanel):
    """Panel for displaying song/track enrichment data."""

    def __init__(self):
        """Initialize the SongEnrichmentPanel."""
        super().__init__(
            PanelInfo(
                id="song_enrichment",
                name="Song Enrichment",
                description="Track information and song-specific data",
                icon="🎵",
                category="discovery",
            )
        )

    def can_display(self, context: ContentContext) -> bool:
        """Check if song/title context is available."""
        return context is not None and bool(context.title)

    def update_context(self, context: ContentContext) -> None:
        """Update panel with new context."""
        self._context = context

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render panel content."""
        if not self._context:
            return

        font = pygame.font.Font(None, 20)
        small_font = pygame.font.Font(None, 16)
        y = rect.top + 10

        enrichment = getattr(self._context, "enrichment_data", None)

        # Title
        title_text = font.render("Song Enrichment", True, (120, 170, 255))
        surface.blit(title_text, (rect.left + 20, y))
        y += 35

        # Basic track information
        track_info_title = small_font.render("Track Information:", True, (230, 230, 230))
        surface.blit(track_info_title, (rect.left + 20, y))
        y += 20

        # Track title
        if self._context.title:
            title_label = small_font.render("Title:", True, (200, 200, 200))
            surface.blit(title_label, (rect.left + 30, y))
            title_value = small_font.render(self._context.title, True, (180, 180, 180))
            surface.blit(title_value, (rect.left + 80, y))
            y += 18

        # Artist
        if self._context.artist:
            artist_label = small_font.render("Artist:", True, (200, 200, 200))
            surface.blit(artist_label, (rect.left + 30, y))
            artist_value = small_font.render(self._context.artist, True, (180, 180, 180))
            surface.blit(artist_value, (rect.left + 80, y))
            y += 18

        # Album
        if self._context.album:
            album_label = small_font.render("Album:", True, (200, 200, 200))
            surface.blit(album_label, (rect.left + 30, y))
            album_value = small_font.render(self._context.album, True, (180, 180, 180))
            surface.blit(album_value, (rect.left + 80, y))
            y += 18

        # Track number
        if self._context.track_number:
            track_num_label = small_font.render("Track:", True, (200, 200, 200))
            surface.blit(track_num_label, (rect.left + 30, y))
            track_num_value = small_font.render(self._context.track_number, True, (180, 180, 180))
            surface.blit(track_num_value, (rect.left + 80, y))
            y += 18

        # Duration
        if self._context.duration:
            duration_label = small_font.render("Duration:", True, (200, 200, 200))
            surface.blit(duration_label, (rect.left + 30, y))
            # Format duration as MM:SS
            duration_seconds = int(self._context.duration)
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            duration_str = f"{minutes}:{seconds:02d}"
            duration_value = small_font.render(duration_str, True, (180, 180, 180))
            surface.blit(duration_value, (rect.left + 80, y))
            y += 18

        # Genre
        if self._context.genre:
            genre_label = small_font.render("Genre:", True, (200, 200, 200))
            surface.blit(genre_label, (rect.left + 30, y))
            genre_value = small_font.render(self._context.genre, True, (180, 180, 180))
            surface.blit(genre_value, (rect.left + 80, y))
            y += 18

        y += 10  # Spacing

        # Song credits section
        if enrichment and enrichment.get("song_credits"):
            credits_title = small_font.render("Song Credits:", True, (230, 230, 230))
            surface.blit(credits_title, (rect.left + 20, y))
            y += 20

            for _i, credit in enumerate(enrichment["song_credits"][:8]):  # Limit to 8 credits
                role = credit.get("role", "Unknown")
                artist = credit.get("artist", "Unknown")
                credit_text = small_font.render(f"{role}: {artist}", True, (180, 180, 180))
                surface.blit(credit_text, (rect.left + 30, y))
                y += 18

            if len(enrichment["song_credits"]) > 8:
                more_credits = small_font.render(
                    f"... and {len(enrichment['song_credits']) - 8} more", True, (150, 150, 150)
                )
                surface.blit(more_credits, (rect.left + 30, y))
                y += 18

            y += 10  # Spacing

        # Enrichment data section
        if enrichment:
            # MusicBrainz Track ID
            if enrichment.get("musicbrainz_track_id"):
                mb_track_title = small_font.render("MusicBrainz Track ID:", True, (230, 230, 230))
                surface.blit(mb_track_title, (rect.left + 20, y))
                y += 20
                mb_track_text = small_font.render(enrichment["musicbrainz_track_id"], True, (180, 180, 180))
                surface.blit(mb_track_text, (rect.left + 30, y))
                y += 18

            # Spotify IDs (if available)
            if enrichment.get("spotify_artist_id") or enrichment.get("spotify_album_id"):
                spotify_title = small_font.render("Spotify IDs:", True, (230, 230, 230))
                surface.blit(spotify_title, (rect.left + 20, y))
                y += 20
                if enrichment.get("spotify_artist_id"):
                    spotify_artist_text = small_font.render(
                        f"Artist: {enrichment['spotify_artist_id']}", True, (180, 180, 180)
                    )
                    surface.blit(spotify_artist_text, (rect.left + 30, y))
                    y += 18
                if enrichment.get("spotify_album_id"):
                    spotify_album_text = small_font.render(
                        f"Album: {enrichment['spotify_album_id']}", True, (180, 180, 180)
                    )
                    surface.blit(spotify_album_text, (rect.left + 30, y))
                    y += 18

            # Technical info
            tech_info = []
            if self._context.bitrate:
                tech_info.append(("Bitrate", self._context.bitrate))
            if self._context.format:
                tech_info.append(("Format", self._context.format.upper()))

            if tech_info:
                tech_title = small_font.render("Technical Info:", True, (230, 230, 230))
                surface.blit(tech_title, (rect.left + 20, y))
                y += 20
                for label, value in tech_info:
                    tech_text = small_font.render(f"{label}: {value}", True, (160, 160, 160))
                    surface.blit(tech_text, (rect.left + 30, y))
                    y += 18
        else:
            no_enrichment = small_font.render("No additional enrichment data available", True, (150, 150, 150))
            surface.blit(no_enrichment, (rect.left + 20, y))
