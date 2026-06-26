"""
signals.py — fires notifications when new episodes are added to a
followed anime.

Movies are handled differently (see notify_movie_releases management
command, not a signal here): a brand-new Movie row can't have any
followers yet — nobody can follow something that doesn't have an ID
to follow. The actual moment that matters for a movie is its release
date arriving, which is why that's a periodic job rather than a
post_save signal.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Episode, Notification, WatchLater, WatchHistory, Follow


def _users_interested_in_anime(anime):
    """Users who follow, watch-later'd, or have history for this anime."""
    follow_ids = set(Follow.objects.filter(anime=anime).values_list('user_id', flat=True))
    wl_ids = set(WatchLater.objects.filter(episode__season__anime=anime).values_list('user_id', flat=True))
    wh_ids = set(WatchHistory.objects.filter(episode__season__anime=anime).values_list('user_id', flat=True))
    ids = follow_ids | wl_ids | wh_ids
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