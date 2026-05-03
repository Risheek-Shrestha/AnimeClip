from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    age = models.IntegerField(validators=[MinValueValidator(10), MaxValueValidator(80)])

    def __str__(self):
        return self.user.username


class Genre(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Anime(models.Model):
    AGE_CHOICES = [
        ('pg', 'PG'),
        ('pg13', 'PG-13'),
        ('r', '18+'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField()
    genres = models.ManyToManyField('Genre', blank=True)
    studio = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        default=0
    )
    age_rating = models.CharField(max_length=10, choices=AGE_CHOICES, default='pg13')
    is_featured = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def get_image(self, img_type):
        # FIX: Iterate over the prefetch cache instead of hitting the DB again.
        # The old .filter() call bypassed prefetch_related and fired a new SQL
        # query for every single image lookup on every card rendered on the page.
        for img in self.media_images.all():
            if img.type == img_type:
                return img
        return None

    @property
    def banner_img(self):
        return self.get_image('banner')

    @property
    def thumb_img(self):
        return self.get_image('thumbnail')

    @property
    def poster_img(self):
        return self.get_image('poster')

    @property
    def card_img(self):
        return self.get_image('card')

    @property
    def logo_img(self):
        return self.get_image('logo')


class Movie(models.Model):
    DAY_CHOICES = [
        ('Sunday', 'Sunday'),
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
    ]

    title = models.CharField(max_length=100)
    description = models.TextField()
    genres = models.ManyToManyField('Genre', blank=True)
    studio = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    release_date = models.DateField(null=True, blank=True)
    release_day = models.CharField(max_length=10, choices=DAY_CHOICES, blank=True)
    release_time = models.TimeField(null=True, blank=True)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        default=0
    )
    is_featured = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)
    duration_mins = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title

    def get_image(self, img_type):
        # FIX: Same as Anime.get_image — use prefetch cache, not a new DB query.
        for img in self.media_images.all():
            if img.type == img_type:
                return img
        return None

    @property
    def banner_img(self):
        return self.get_image('banner')

    @property
    def thumb_img(self):
        return self.get_image('thumbnail')

    @property
    def poster_img(self):
        return self.get_image('poster')

    @property
    def card_img(self):
        return self.get_image('card')


class Season(models.Model):
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('upcoming', 'Upcoming'),
    ]

    DAY_CHOICES = [
        ('Sunday', 'Sunday'),
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
    ]

    anime = models.ForeignKey(Anime, on_delete=models.CASCADE, related_name='seasons')
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=100, blank=True)
    release_date = models.DateField(null=True, blank=True)
    release_day = models.CharField(max_length=10, choices=DAY_CHOICES, blank=True)
    release_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ongoing')

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f'{self.anime.title} - {self.number}'


class Episode(models.Model):
    DAY_CHOICES = [
        ('Sunday', 'Sunday'),
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
    ]

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='episodes')
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=100, blank=True)
    release_date = models.DateField(null=True, blank=True)
    release_day = models.CharField(max_length=10, choices=DAY_CHOICES, blank=True)
    release_time = models.TimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f'{self.season} - {self.number}'


class VideoSource(models.Model):
    TYPE_CHOICES = [('sub', 'SUB'), ('dub', 'DUB')]
    episode = models.ForeignKey(Episode, on_delete=models.CASCADE, related_name='sources')
    label = models.CharField(max_length=50)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    video_url = models.URLField(max_length=500, null=True, blank=True)  # changed
    poster = models.ImageField(upload_to='posters/', null=True, blank=True)

    def __str__(self):
        return f"{self.episode} - {self.label} ({self.type})"


class MovieSource(models.Model):
    TYPE_CHOICES = [('sub', 'SUB'), ('dub', 'DUB')]
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='sources')
    label = models.CharField(max_length=50)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    video_url = models.URLField(max_length=500, null=True, blank=True)  # changed
    poster = models.ImageField(upload_to='posters/', null=True, blank=True)

    def __str__(self):
        return f"{self.movie.title} - {self.label} ({self.type})"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    episode = models.ForeignKey(Episode, null=True, blank=True, on_delete=models.CASCADE, related_name='comments')
    movie = models.ForeignKey(Movie, null=True, blank=True, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def total_likes(self):
        return self.likes.count()

    def __str__(self):
        return f"Comment by {self.user.username}"

    def clean(self):
        if not self.episode and not self.movie:
            raise ValidationError("Comment must be linked to either Episode or Movie")
        if self.episode and self.movie:
            raise ValidationError("Comment cannot be linked to both Episode and Movie")


class CommentLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ['user', 'comment']


class MediaImage(models.Model):
    IMAGE_TYPE_CHOICES = [
        ('thumbnail', 'Thumbnail'),
        ('banner', 'Banner'),
        ('logo', 'Logo'),
        ('poster', 'Poster'),
        ('card', 'Card Image'),
        ('background', 'Background'),
    ]

    anime = models.ForeignKey(
        'Anime',
        on_delete=models.CASCADE,
        related_name='media_images',
        null=True,
        blank=True
    )
    movie = models.ForeignKey(
        'Movie',
        on_delete=models.CASCADE,
        related_name='media_images',
        null=True,
        blank=True
    )
    image = models.ImageField(upload_to='media/images/')
    type = models.CharField(max_length=20, choices=IMAGE_TYPE_CHOICES)

    def __str__(self):
        if self.anime:
            return f"{self.anime.title} - {self.type}"
        elif self.movie:
            return f"{self.movie.title} - {self.type}"
        return f"MediaImage - {self.type}"

    def clean(self):
        if not self.anime and not self.movie:
            raise ValidationError("Image must be linked to either Anime or Movie")
        if self.anime and self.movie:
            raise ValidationError("Image cannot be linked to both Anime and Movie")

class WatchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watch_history')
    episode = models.ForeignKey(Episode, null=True, blank=True, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, null=True, blank=True, on_delete=models.CASCADE)
    progress_seconds = models.PositiveIntegerField(default=0)  # how far they watched
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = [['user', 'episode'], ['user', 'movie']]

    def __str__(self):
        return f"{self.user.username} - {self.episode or self.movie}"


class WatchLater(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='watch_later')
    episode = models.ForeignKey(Episode, null=True, blank=True, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, null=True, blank=True, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']
        unique_together = [['user', 'episode'], ['user', 'movie']]

    def __str__(self):
        return f"{self.user.username} - {self.episode or self.movie}"


class Playlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playlists')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class PlaylistItem(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name='items')
    episode = models.ForeignKey(Episode, null=True, blank=True, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, null=True, blank=True, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['added_at']

    def __str__(self):
        return f"{self.playlist.name} - {self.episode or self.movie}"