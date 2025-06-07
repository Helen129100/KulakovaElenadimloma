from django.db import models
from django.conf import settings


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Video(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    post = models.TextField(max_length=255)
    description = models.TextField(blank=True)  # 🆕 Добавлено поле
    video_file = models.FileField(upload_to="videos/", blank=True, null=True)
    parent = models.ForeignKey("Video", null=True, blank=True, on_delete=models.CASCADE)
    comments = models.IntegerField(default=0)
    views = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    tags = models.ManyToManyField("Tag", blank=True, related_name="videos")

    def __str__(self):
        return self.post

    def get_comments(self):
        return Video.objects.filter(parent=self).order_by("-date")

    def calculate_comments(self):
        self.comments = Video.objects.filter(parent=self).count()
        self.save()
        return self.comments

    def comment(self, user, post):
        video_comment = Video(user=user, post=post, parent=self)
        video_comment.save()
        self.comments = Video.objects.filter(parent=self).count()
        self.save()
        return video_comment

    def increment_views(self):
        self.views += 1
        self.save()

    def like(self, user):
        Like.objects.create(video=self, user=user)


class Like(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} liked {self.video.post}"


class Subscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriber"
    )
    channel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription_set",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} subscribed to {self.channel.username}"
