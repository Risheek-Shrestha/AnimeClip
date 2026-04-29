from django.contrib import admin
from .models import Profile, Anime, Movie, Genre, Season, Episode, VideoSource, MovieSource, Comment, CommentLike, \
    MediaImage

admin.site.register(Genre)
admin.site.register(Anime)
admin.site.register(Movie)
admin.site.register(Season)
admin.site.register(Episode)
admin.site.register(VideoSource)
admin.site.register(MovieSource)
admin.site.register(Comment)
admin.site.register(CommentLike)
admin.site.register(Profile)
admin.site.register(MediaImage)

