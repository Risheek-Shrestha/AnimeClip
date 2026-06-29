"""
Sitemap definitions for search engines.

robots_txt (see views.py) has always advertised `Sitemap: .../sitemap.xml`,
but nothing actually served that URL — it 404'd. This module fills that gap.

Only genuinely public, unauthenticated pages are listed here. Anything
behind @login_required (streaming pages, profile, playlists, watch
history, …) is deliberately excluded: a crawler hitting one of those
URLs without a session just gets redirected to /login/, so there's
nothing useful to index and no reason to invite the crawl traffic.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Genre


class StaticViewSitemap(Sitemap):
    """The handful of public, login-free pages that don't take a slug/id."""

    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return ['index', 'movies', 'all_categories']

    def location(self, item):
        return reverse(item)


class GenreSitemap(Sitemap):
    """One entry per genre — these power the public /category/<genre>/ pages."""

    priority = 0.6
    changefreq = 'weekly'

    def items(self):
        # distinct() because the same genre name could theoretically be
        # entered more than once via the admin; we only want one URL per name.
        return Genre.objects.order_by('name').values_list('name', flat=True).distinct()

    def location(self, name):
        return reverse('category_page', args=[name])


class AnimeSitemap(Sitemap):
    """One entry per Anime series — public detail pages (/anime/<slug>/)."""

    priority = 0.9
    changefreq = 'weekly'

    def items(self):
        from .models import Anime
        return Anime.objects.exclude(slug='').order_by('slug')

    def location(self, obj):
        return reverse('anime_detail', args=[obj.slug])

    def lastmod(self, obj):
        # Use the most recently updated episode as the last-modified date.
        from .models import Episode
        ep = Episode.objects.filter(season__anime=obj).order_by('-updated_at').first()
        return ep.updated_at if ep else None


sitemaps = {
    'static': StaticViewSitemap,
    'genres': GenreSitemap,
    'anime': AnimeSitemap,
}
