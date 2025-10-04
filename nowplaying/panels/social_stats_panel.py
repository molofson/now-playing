"""
Social Statistics enrichment panel implementation.

Displays social metrics like scrobble counts, popularity scores, and user data.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class SocialStatsPanel(ContentPanel):
    """Panel for displaying social statistics from enrichment."""

    def __init__(self):
        """Initialize the SocialStatsPanel."""
        super().__init__(
            PanelInfo(
                id="social_stats",
                name="Social Stats",
                description="Scrobble counts, popularity, and social metrics",
                icon="📊",
                category="discovery",
            )
        )

    def can_display(self, context: ContentContext) -> bool:
        """Check if artist or album context is available."""
        return context is not None

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
        title_text = font.render("Social Statistics", True, (120, 170, 255))
        surface.blit(title_text, (rect.left + 20, y))
        y += 35

        if enrichment:
            # Scrobble Count
            if enrichment.get("scrobble_count") is not None:
                scrobble_title = small_font.render("Scrobble Count:", True, (230, 230, 230))
                surface.blit(scrobble_title, (rect.left + 20, y))
                y += 20
                count = enrichment["scrobble_count"]
                if count >= 1000000:
                    display_count = f"{count/1000000:.1f}M"
                elif count >= 1000:
                    display_count = f"{count/1000:.1f}K"
                else:
                    display_count = str(count)
                count_text = font.render(display_count, True, (255, 210, 140))
                surface.blit(count_text, (rect.left + 30, y))
                y += 30

            # Popularity Score
            if enrichment.get("popularity_score") is not None:
                pop_title = small_font.render("Popularity Score:", True, (230, 230, 230))
                surface.blit(pop_title, (rect.left + 20, y))
                y += 20
                score = enrichment["popularity_score"]
                # Create a simple bar visualization
                bar_width = min(int(score * 2), 200)  # Scale to 200px max
                bar_rect = pygame.Rect(rect.left + 30, y, bar_width, 20)
                pygame.draw.rect(surface, (120, 170, 255), bar_rect)
                score_text = small_font.render(f"{score:.1f}/100", True, (230, 230, 230))
                surface.blit(score_text, (rect.left + 240, y + 2))
                y += 30

            # User Tags
            if enrichment.get("user_tags"):
                tags_title = small_font.render("User Tags:", True, (230, 230, 230))
                surface.blit(tags_title, (rect.left + 20, y))
                y += 20
                tags_text = ", ".join(enrichment["user_tags"][:6])  # Limit tags
                tags_lines = self._wrap_text(tags_text, 50)
                for line in tags_lines:
                    tag_text = small_font.render(line, True, (180, 180, 180))
                    surface.blit(tag_text, (rect.left + 30, y))
                    y += 18
                y += 10

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
                        show_text = small_font.render(f"{date} - {venue}, {city}", True, (160, 160, 160))
                        surface.blit(show_text, (rect.left + 30, y))
                        y += 18
        else:
            no_data = font.render("No social statistics available", True, (150, 150, 150))
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
