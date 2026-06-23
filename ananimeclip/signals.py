"""
signals.py — fires notifications when new episodes or movies are created.

For anime: notifies users who Follow the anime (dedicated follow) OR
           who have it in WatchLater / WatchHistory (legacy intent signals).
For movies: notifies users who have it in WatchLater / WatchHistory.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Episode, Movie, Notification, WatchLater, WatchHistory, Follow


def _users_interested_in_anime(anime):
    """Users who follow, watch-later'd, or have history for this anime."""
    follow_ids = set(Follow.objects.filter(anime=anime).values_list('user_id', flat=True))
    wl_ids = set(WatchLater.objects.filter(episode__season__anime=anime).values_list('user_id', flat=True))
    wh_ids = set(WatchHistory.objects.filter(episode__season__anime=anime).values_list('user_id', flat=True))
    ids = follow_ids | wl_ids | wh_ids
    from django.contrib.auth.models import User
    return User.objects.filter(pk__in=ids)


def _users_interested_in_movie(movie):
    wl_ids = set(WatchLater.objects.filter(movie=movie).values_list('user_id', flat=True))
    wh_ids = set(WatchHistory.objects.filter(movie=movie).values_list('user_id', flat=True))
    ids = wl_ids | wh_ids
    from django.contrib.auth.models import User
    return User.objects.filter(pk__in=ids)


@receiver(post_save, sender=Episode)
def notify_new_episode(sender, instance, created, **kwargs):
    if not created:
        return
    anime = instance.season.anime
    users = _users_interested_in_anime(anime)
    ep_label = f"Episode {instance.number}"
    if instance.title:
        ep_label += f" — {instance.title}"
    message = f"New episode available: {anime.title} · {ep_label}"
    notifications = [
        Notification(
            user=user,
            notif_type='new_episode',
            anime=anime,
            episode=instance,
            message=message,
        )
        for user in users
    ]
    if notifications:
        Notification.objects.bulk_create(notifications, ignore_conflicts=True)


@receiver(post_save, sender=Movie)
def notify_new_movie(sender, instance, created, **kwargs):
    if not created:
        return
    users = _users_interested_in_movie(instance)
    message = f"New movie added: {instance.title}"
    notifications = [
        Notification(
            user=user,
            notif_type='new_movie',
            movie=instance,
            message=message,
        )
        for user in users
    ]
    if notifications:
        Notification.objects.bulk_create(notifications, ignore_conflicts=True)