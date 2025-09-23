"""
Music Discovery panel implementation.

Displays enriched metadata from all services in a unified discovery interface,
focusing on helping users discover new music and explore artist information.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class DiscoveryPanel(ContentPanel):
    """Panel for displaying unified music discovery information."""

    def __init__(self):
        """Initialize the DiscoveryPanel."""
        super().__init__(
            PanelInfo(
                id="discovery",
                name="Music Discovery",
                description="Unified music discovery with enriched metadata",
                icon="🔍",
                category="discovery",
                requires_metadata=True,
                requires_network=True,
            )
        )

    def handle_event(self, event: pygame.event.Event) -> bool:  # noqa: U100
        """Handle events (not used in this panel)."""
        return False

    def can_display(self, context: ContentContext) -> bool:
        """Check if this panel can display the given context."""
        return context is not None and (context.artist or context.album or context.title)

    def update_context(self, context: ContentContext) -> None:
        """Update with new content context."""
        self._context = context

    def render(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render the discovery panel."""
        if not self._context:
            self._render_no_context(surface, rect)
            return

        # Get enrichment data
        enrichment = getattr(self._context, "enrichment_data", None)

        # Define sections
        margin = 20
        section_height = (rect.height - margin * 3) // 2
        
        # Top section: Artist discovery
        artist_rect = pygame.Rect(rect.left + margin, rect.top + margin, rect.width - 2 * margin, section_height)
        self._render_artist_discovery(surface, artist_rect, enrichment)

        # Bottom section: Album/Track discovery
        album_rect = pygame.Rect(
            rect.left + margin, 
            rect.top + margin + section_height + margin, 
            rect.width - 2 * margin, 
            section_height
        )
        self._render_album_discovery(surface, album_rect, enrichment)

    def _render_no_context(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        """Render when no context is available."""
        font = pygame.font.Font(None, 32)
        text = font.render("No music playing - discovery panel inactive", True, (140, 140, 140))
        text_rect = text.get_rect(center=rect.center)
        surface.blit(text, text_rect)

    def _render_artist_discovery(self, surface: pygame.Surface, rect: pygame.Rect, enrichment) -> None:
        """Render artist discovery section."""
        # Section title
        title_font = pygame.font.Font(None, 28)
        content_font = pygame.font.Font(None, 22)
        small_font = pygame.font.Font(None, 18)

        y = rect.top
        section_title = title_font.render(f"🎤 Discover: {self._context.artist}", True, (255, 255, 255))
        surface.blit(section_title, (rect.left, y))
        y += 35

        if enrichment:
            # Artist bio (truncated)
            if enrichment.artist_bio:
                bio_lines = self._wrap_text(enrichment.artist_bio, content_font, rect.width - 20, max_lines=3)
                for line in bio_lines:
                    bio_surface = content_font.render(line, True, (200, 200, 200))
                    surface.blit(bio_surface, (rect.left + 10, y))
                    y += 25

            # Tags/genres
            if enrichment.artist_tags:
                tags_text = "Genres: " + ", ".join(enrichment.artist_tags[:6])
                tags_surface = small_font.render(tags_text, True, (180, 180, 255))
                surface.blit(tags_surface, (rect.left + 10, y))
                y += 22

            # Similar artists
            if enrichment.similar_artists:
                similar_title = small_font.render("Similar Artists:", True, (255, 200, 100))
                surface.blit(similar_title, (rect.left + 10, y))
                y += 20

                for i, artist in enumerate(enrichment.similar_artists[:3]):
                    name = artist.get("name", "Unknown")
                    match = artist.get("match", 0)
                    similar_text = f"  • {name} ({match:.0%} match)" if match else f"  • {name}"
                    similar_surface = small_font.render(similar_text, True, (170, 170, 170))
                    surface.blit(similar_surface, (rect.left + 20, y))
                    y += 18

            # Popularity/stats
            stats_y = rect.bottom - 25
            if enrichment.scrobble_count:
                scrobbles = f"🎵 {enrichment.scrobble_count:,} plays"
                scrobble_surface = small_font.render(scrobbles, True, (140, 200, 140))
                surface.blit(scrobble_surface, (rect.left + 10, stats_y))

            if enrichment.popularity_score:
                popularity = f"📈 {enrichment.popularity_score:.1%} popularity"
                pop_surface = small_font.render(popularity, True, (255, 200, 100))
                surface.blit(pop_surface, (rect.right - 200, stats_y))

        else:
            # No enrichment data
            no_data_text = content_font.render("Loading discovery data...", True, (140, 140, 140))
            surface.blit(no_data_text, (rect.left + 10, y))

    def _render_album_discovery(self, surface: pygame.Surface, rect: pygame.Rect, enrichment) -> None:
        """Render album/track discovery section."""
        title_font = pygame.font.Font(None, 28)
        content_font = pygame.font.Font(None, 22)
        small_font = pygame.font.Font(None, 18)

        y = rect.top
        album_name = self._context.album or "Current Track"
        section_title = title_font.render(f"💿 Album: {album_name}", True, (255, 255, 255))
        surface.blit(section_title, (rect.left, y))
        y += 35

        if enrichment:
            # Album credits
            if enrichment.album_credits:
                credits_title = small_font.render("Credits:", True, (255, 200, 100))
                surface.blit(credits_title, (rect.left + 10, y))
                y += 20

                for credit in enrichment.album_credits[:3]:
                    role = credit.get("role", "artist")
                    artist = credit.get("artist", "Unknown")
                    credit_text = f"  • {role.title()}: {artist}"
                    credit_surface = small_font.render(credit_text, True, (170, 170, 170))
                    surface.blit(credit_surface, (rect.left + 20, y))
                    y += 18

            # Album reviews/info
            if enrichment.album_reviews:
                review_title = small_font.render("Release Info:", True, (255, 200, 100))
                surface.blit(review_title, (rect.left + 10, y))
                y += 20

                for review in enrichment.album_reviews[:2]:
                    summary = review.get("summary", "")
                    if summary:
                        review_surface = small_font.render(f"  • {summary}", True, (170, 170, 170))
                        surface.blit(review_surface, (rect.left + 20, y))
                        y += 18

            # Artist discography
            if enrichment.artist_discography:
                disco_title = small_font.render("Other Releases:", True, (255, 200, 100))
                surface.blit(disco_title, (rect.left + 10, y))
                y += 20

                for release in enrichment.artist_discography[:4]:
                    title = release.get("title", "Unknown")
                    year = release.get("year", "")
                    format_info = release.get("format", "")
                    
                    # Create release text
                    release_parts = [title]
                    if year:
                        release_parts.append(f"({year})")
                    if format_info:
                        release_parts.append(f"[{format_info}]")
                    
                    release_text = f"  • {' '.join(release_parts)}"
                    
                    # Truncate if too long
                    if len(release_text) > 50:
                        release_text = release_text[:47] + "..."
                    
                    release_surface = small_font.render(release_text, True, (170, 170, 170))
                    surface.blit(release_surface, (rect.left + 20, y))
                    y += 18

        else:
            # No enrichment data
            no_data_text = content_font.render("Loading album info...", True, (140, 140, 140))
            surface.blit(no_data_text, (rect.left + 10, y))

        # Service status indicators
        self._render_service_status(surface, rect, enrichment)

    def _render_service_status(self, surface: pygame.Surface, rect: pygame.Rect, enrichment) -> None:
        """Render status indicators for enrichment services."""
        small_font = pygame.font.Font(None, 16)
        y = rect.bottom - 20

        if enrichment and enrichment.last_updated:
            # Show which services provided data
            services = []
            if "musicbrainz" in enrichment.last_updated:
                services.append("MusicBrainz")
            if "discogs" in enrichment.last_updated:
                services.append("Discogs")
            if "lastfm" in enrichment.last_updated:
                services.append("Last.fm")

            if services:
                status_text = f"Data from: {', '.join(services)}"
                status_surface = small_font.render(status_text, True, (100, 100, 100))
                surface.blit(status_surface, (rect.left + 10, y))

        # Show errors if any
        if enrichment and enrichment.service_errors:
            error_services = list(enrichment.service_errors.keys())
            error_text = f"Errors: {', '.join(error_services)}"
            error_surface = small_font.render(error_text, True, (200, 100, 100))
            surface.blit(error_surface, (rect.right - 200, y))

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int, max_lines: int = None) -> list:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            # Test if adding this word would exceed width
            test_line = " ".join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                # Start a new line
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Single word is too long, truncate it
                    lines.append(word[:20] + "...")

                # Check max lines limit
                if max_lines and len(lines) >= max_lines:
                    break

        # Add remaining words
        if current_line and (not max_lines or len(lines) < max_lines):
            lines.append(" ".join(current_line))

        return lines