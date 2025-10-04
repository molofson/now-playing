"""
Artist Enrichment panel implementation.

Displays comprehensive artist information including bio, tags, similar artists,
social statistics, and popularity metrics.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class ArtistEnrichmentPanel(ContentPanel):
    """Panel for displaying comprehensive artist enrichment data."""

    def __init__(self):
        """Initialize the ArtistEnrichmentPanel."""
        super().__init__(
            PanelInfo(
                id="artist_enrichment",
                name="Artist Enrichment",
                description="Artist biography, tags, similar artists, and social stats",
                icon="👤",
                category="discovery",
            )
        )

    def can_display(self, context: ContentContext) -> bool:
        """Check if artist context is available."""
        return context is not None and bool(context.artist)

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
        title_text = font.render("Artist Enrichment", True, (120, 170, 255))
        surface.blit(title_text, (rect.left + 20, y))
        y += 35

        if enrichment:
            # MusicBrainz Artist ID
            if enrichment.get("musicbrainz_artist_id"):
                mb_id_title = small_font.render("MusicBrainz ID:", True, (230, 230, 230))
                surface.blit(mb_id_title, (rect.left + 20, y))
                y += 20
                mb_id_text = small_font.render(enrichment["musicbrainz_artist_id"], True, (180, 180, 180))
                surface.blit(mb_id_text, (rect.left + 30, y))
                y += 18

            # Social Statistics Section
            social_stats = []
            if enrichment.get("scrobble_count") is not None:
                count = enrichment["scrobble_count"]
                if count >= 1000000:
                    display_count = f"{count/1000000:.1f}M"
                elif count >= 1000:
                    display_count = f"{count/1000:.1f}K"
                else:
                    display_count = str(count)
                social_stats.append(("Scrobbles", display_count))

            if enrichment.get("popularity_score") is not None:
                social_stats.append(("Popularity", f"{enrichment['popularity_score']:.1f}/100"))

            if social_stats:
                stats_title = small_font.render("Social Stats:", True, (230, 230, 230))
                surface.blit(stats_title, (rect.left + 20, y))
                y += 20
                for label, value in social_stats:
                    stat_text = small_font.render(f"{label}: {value}", True, (255, 210, 140))
                    surface.blit(stat_text, (rect.left + 30, y))
                    y += 18
                y += 10

            # Artist Tags
            if enrichment.get("artist_tags"):
                tags_title = small_font.render("Tags:", True, (230, 230, 230))
                surface.blit(tags_title, (rect.left + 20, y))
                y += 20
                tags_text = ", ".join(enrichment["artist_tags"][:8])  # Limit tags
                tags_lines = self._wrap_text(tags_text, 50)
                for line in tags_lines:
                    tag_text = small_font.render(line, True, (180, 180, 180))
                    surface.blit(tag_text, (rect.left + 30, y))
                    y += 18
                y += 10

            # User Tags (from social data)
            if enrichment.get("user_tags"):
                user_tags_title = small_font.render("User Tags:", True, (230, 230, 230))
                surface.blit(user_tags_title, (rect.left + 20, y))
                y += 20
                user_tags_text = ", ".join(enrichment["user_tags"][:6])  # Limit tags
                user_tags_lines = self._wrap_text(user_tags_text, 50)
                for line in user_tags_lines:
                    tag_text = small_font.render(line, True, (160, 160, 160))
                    surface.blit(tag_text, (rect.left + 30, y))
                    y += 18
                y += 10

            # Artist Bio (if available from Last.fm)
            if enrichment.get("artist_bio"):
                bio_lines = self._wrap_text(enrichment["artist_bio"], 60)
                bio_title = small_font.render("Biography:", True, (230, 230, 230))
                surface.blit(bio_title, (rect.left + 20, y))
                y += 20
                for line in bio_lines[:3]:  # Limit to 3 lines
                    bio_text = small_font.render(line, True, (200, 200, 200))
                    surface.blit(bio_text, (rect.left + 30, y))
                    y += 18
                y += 10

            # Similar Artists (if available from Last.fm)
            if enrichment.get("similar_artists"):
                similar_title = small_font.render("Similar Artists:", True, (230, 230, 230))
                surface.blit(similar_title, (rect.left + 20, y))
                y += 20
                for _i, artist in enumerate(enrichment["similar_artists"][:5]):
                    if isinstance(artist, dict) and "name" in artist:
                        match = artist.get("match", 0)
                        artist_text = small_font.render(f"{artist['name']} ({match:.1%})", True, (160, 160, 160))
                        surface.blit(artist_text, (rect.left + 30, y))
                        y += 18

            # Tour Dates (if available)
            if enrichment.get("tour_dates"):
                tour_title = small_font.render("Upcoming Shows:", True, (230, 230, 230))
                surface.blit(tour_title, (rect.left + 20, y))
                y += 20
                for _i, tour_date in enumerate(enrichment["tour_dates"][:3]):  # Limit to 3 shows
                    if isinstance(tour_date, dict):
                        venue = tour_date.get("venue", "")
                        city = tour_date.get("city", "")
                        date = tour_date.get("date", "")
                        show_text = small_font.render(f"{date} - {venue}, {city}", True, (140, 160, 255))
                        surface.blit(show_text, (rect.left + 30, y))
                        y += 18
        else:
            no_data = font.render("No artist enrichment data available", True, (150, 150, 150))
            surface.blit(no_data, (rect.left + 20, y))

    def _wrap_text(self, text: str, max_chars: int) -> list:
        """Wrap text to fit within specified width."""
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line + " " + word) <= max_chars:
                current_line += " " + word if current_line else word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines
