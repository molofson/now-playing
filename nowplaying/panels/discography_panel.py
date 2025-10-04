"""
Discography panel implementation.

Displays artist discography and release history.
"""

import pygame

from .base import ContentContext, ContentPanel, PanelInfo


class DiscographyPanel(ContentPanel):
    """Panel for displaying artist discography."""

    def __init__(self):
        """Initialize the DiscographyPanel."""
        super().__init__(
            PanelInfo(
                id="discography",
                name="Discography",
                description="Artist discography and release history",
                icon="📚",
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
        title_text = font.render("Artist Discography", True, (120, 170, 255))
        surface.blit(title_text, (rect.left + 20, y))
        y += 35

        if enrichment and enrichment.get("artist_discography"):
            discography = enrichment["artist_discography"]

            # Group releases by type/year for better organization
            releases_by_type = {}
            for release in discography:
                if isinstance(release, dict):
                    release_type = release.get("format", "Album")  # Default to Album
                    year = release.get("year", "Unknown")

                    if release_type not in releases_by_type:
                        releases_by_type[release_type] = {}
                    if year not in releases_by_type[release_type]:
                        releases_by_type[release_type][year] = []

                    releases_by_type[release_type][year].append(release)

            # Display releases grouped by type and year
            for release_type in sorted(releases_by_type.keys()):
                type_title = small_font.render(f"{release_type}s:", True, (230, 230, 230))
                surface.blit(type_title, (rect.left + 20, y))
                y += 20

                type_releases = releases_by_type[release_type]
                for year in sorted(type_releases.keys(), reverse=True):  # Most recent first
                    year_releases = type_releases[year]

                    for release in year_releases[:3]:  # Limit per year
                        title = release.get("title", "Unknown Title")
                        release_text = small_font.render(f"{year} - {title}", True, (180, 180, 180))
                        surface.blit(release_text, (rect.left + 30, y))
                        y += 18

                        # Check if we have enough space for more
                        if y > rect.bottom - 50:
                            break

                    if y > rect.bottom - 50:
                        break

                y += 10  # Spacing between types

                # Check if we need to stop due to space
                if y > rect.bottom - 50:
                    remaining_types = len(releases_by_type) - list(releases_by_type.keys()).index(release_type) - 1
                    if remaining_types > 0:
                        more_text = small_font.render(
                            f"... and {remaining_types} more release types", True, (150, 150, 150)
                        )
                        surface.blit(more_text, (rect.left + 20, y))
                    break

        elif enrichment:
            # Has enrichment data but no discography
            no_discog = font.render("No discography data available", True, (150, 150, 150))
            surface.blit(no_discog, (rect.left + 20, y))
        else:
            # No enrichment data at all
            no_data = font.render("No enrichment data available", True, (150, 150, 150))
            surface.blit(no_data, (rect.left + 20, y))
