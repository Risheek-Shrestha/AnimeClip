"""
signals.py — fires notifications when new episodes are added to a
followed anime, and triggers eager transcoding for new/updated video sources.

Movies are handled differently (see notify_movie_releases management
command, not a signal here): a brand-new Movie row can't have any
followers yet — nobody can follow something that doesn't have an ID
to follow. The actual moment that matters for a movie is its release
date arriving, which is why that's a periodic job rather than a
post_save signal.

Transcoding
-----------
When a VideoSource or MovieSource is saved with a Cloudinary video URL,
``trigger_source_transcoding`` asks Cloudinary to eagerly pre-generate all
quality renditions (1080p, 720p, 480p, 360p as mp4 + HLS) via
``transcoding.request_eager_transcoding()``.  This is async on Cloudinary's
side (``eager_async=True``) so the save does not block.
"""

import threading

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Episode, Follow, MovieSource, Notification, VideoSource, WatchHistory, WatchLater


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
    ep_label = f'Episode {instance.number}'
    if instance.title:
        ep_label += f' — {instance.title}'
    message = f'New episode available: {anime.title} · {ep_label}'
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


# ---------------------------------------------------------------------------
# Eager transcoding — triggered whenever a video source URL changes
# ---------------------------------------------------------------------------


def _should_transcode(instance, update_fields):
    """
    Return True if we should queue a transcoding job for *instance*.

    We transcode when:
    - the row is brand new (update_fields is None and it's a create), OR
    - video_url is in the set of fields being updated.

    The actual create/update distinction is handled by the callers since
    Django passes ``created`` to post_save receivers.
    """
    if update_fields is None:
        return True  # full save — always check
    return 'video_url' in update_fields


@receiver(post_save, sender=VideoSource)
def trigger_source_transcoding(sender, instance, created, update_fields, **kwargs):
    """
    Queue eager Cloudinary transcoding whenever a VideoSource is saved
    with a (new) video_url.

    We only transcode Cloudinary-hosted videos — external URLs (e.g. an
    admin paste of a CDN link from another provider) are skipped silently.
    """
    if not instance.video_url:
        return
    if not created and not _should_transcode(instance, update_fields):
        return

    # Run in a background thread so the admin save response is never blocked by
    # a Cloudinary API call. request_eager_transcoding already handles its own
    # exceptions and logs them, so the thread is fire-and-forget safe.
    from .transcoding import request_eager_transcoding  # noqa: PLC0415

    url = instance.video_url
    threading.Thread(target=request_eager_transcoding, args=(url,), daemon=True).start()


@receiver(post_save, sender=MovieSource)
def trigger_movie_source_transcoding(sender, instance, created, update_fields, **kwargs):
    """Same as trigger_source_transcoding but for MovieSource rows."""
    if not instance.video_url:
        return
    if not created and not _should_transcode(instance, update_fields):
        return

    from .transcoding import request_eager_transcoding  # noqa: PLC0415

    url = instance.video_url
    threading.Thread(target=request_eager_transcoding, args=(url,), daemon=True).start()
