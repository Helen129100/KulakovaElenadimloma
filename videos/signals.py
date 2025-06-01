from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Video

from django.contrib.contenttypes.models import ContentType


@receiver(post_save, sender=Video)
def increment_views(sender, instance, created, **kwargs):
    if created:
        instance.views += 1
        instance.save()


@receiver(post_save, sender=ContentType)
def register_video_content_type(sender, instance, created, **kwargs):
    if instance.model == Video:
        Video.content_type.name = "Video"
        Video.content_type.description = "A video object"
        Video.content_type.save()
