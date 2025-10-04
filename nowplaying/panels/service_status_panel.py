"""
Service Status enrichment panel implementation.

Displays service update times, error status, and data freshness.
"""

import time

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class ServiceStatusPanel(ContentPanel):
    """Panel for displaying service status and data freshness."""

    def __init__(self):
        """Initialize the ServiceStatusPanel."""
        super().__init__(
            PanelInfo(
                id="service_status",
                name="Service Status",
                description="Data freshness and service health",
                icon="🔄",
                category="discovery",
            )
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle events (not used)."""
        del event
        return False

    def can_display(self, context: ContentContext) -> bool:
        """Check if any context is available."""
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
        title_text = font.render("Service Status", True, (120, 170, 255))
        surface.blit(title_text, (rect.left + 20, y))
        y += 35

        if enrichment:
            # Service Update Times
            if enrichment.get("last_updated"):
                updates_title = small_font.render("Last Updated:", True, (230, 230, 230))
                surface.blit(updates_title, (rect.left + 20, y))
                y += 20

                current_time = time.time()
                for service, timestamp in enrichment["last_updated"].items():
                    if isinstance(timestamp, (int, float)):
                        age_seconds = current_time - timestamp
                        age_text = self._format_age(age_seconds)
                        status_color = self._get_age_color(age_seconds)

                        service_text = small_font.render(f"{service.title()}:", True, (200, 200, 200))
                        surface.blit(service_text, (rect.left + 30, y))

                        age_render = small_font.render(age_text, True, status_color)
                        surface.blit(age_render, (rect.left + 120, y))
                        y += 18
                y += 10

            # Service Errors
            if enrichment.get("service_errors"):
                errors_title = small_font.render("Service Errors:", True, (230, 230, 230))
                surface.blit(errors_title, (rect.left + 20, y))
                y += 20

                has_errors = False
                for service, error in enrichment["service_errors"].items():
                    if error:
                        has_errors = True
                        error_text = small_font.render(
                            f"{service.title()}: {str(error)[:40]}...", True, (255, 120, 120)
                        )
                        surface.blit(error_text, (rect.left + 30, y))
                        y += 18

                if not has_errors:
                    ok_text = small_font.render("All services OK", True, (120, 255, 120))
                    surface.blit(ok_text, (rect.left + 30, y))
                    y += 18
                y += 10

            # Data Completeness
            completeness_title = small_font.render("Data Completeness:", True, (230, 230, 230))
            surface.blit(completeness_title, (rect.left + 20, y))
            y += 20

            # Check various data fields
            data_fields = {
                "MusicBrainz IDs": bool(
                    enrichment.get("musicbrainz_artist_id") or enrichment.get("musicbrainz_album_id")
                ),
                "Discogs IDs": bool(enrichment.get("discogs_artist_id") or enrichment.get("discogs_release_id")),
                "Artist Bio": bool(enrichment.get("artist_bio")),
                "Artist Tags": bool(enrichment.get("artist_tags")),
                "Similar Artists": bool(enrichment.get("similar_artists")),
                "Album Reviews": bool(enrichment.get("album_reviews")),
                "Cover Art URLs": bool(enrichment.get("cover_art_urls")),
                "Artist Images": bool(enrichment.get("artist_images")),
                "Scrobble Data": enrichment.get("scrobble_count") is not None,
                "Discography": bool(enrichment.get("artist_discography")),
            }

            complete_count = sum(data_fields.values())
            total_count = len(data_fields)

            # Progress bar
            bar_width = 150
            filled_width = int((complete_count / total_count) * bar_width)
            bar_rect = pygame.Rect(rect.left + 30, y, bar_width, 16)
            fill_rect = pygame.Rect(rect.left + 30, y, filled_width, 16)

            pygame.draw.rect(surface, (50, 50, 50), bar_rect)  # Background
            pygame.draw.rect(surface, (120, 170, 255), fill_rect)  # Fill

            completeness_text = small_font.render(
                f"{complete_count}/{total_count} fields populated", True, (200, 200, 200)
            )
            surface.blit(completeness_text, (rect.left + 190, y))
            y += 20

        else:
            no_data = font.render("No enrichment data available", True, (150, 150, 150))
            surface.blit(no_data, (rect.left + 20, y))

    def _format_age(self, seconds: float) -> str:
        """Format age in human readable form."""
        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            return f"{int(seconds/60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds/3600)}h ago"
        else:
            return f"{int(seconds/86400)}d ago"

    def _get_age_color(self, seconds: float) -> tuple:
        """Get color based on data age."""
        if seconds < 3600:  # < 1 hour
            return (120, 255, 120)  # Green
        elif seconds < 86400:  # < 1 day
            return (255, 210, 140)  # Orange
        else:  # > 1 day
            return (255, 120, 120)  # Red
