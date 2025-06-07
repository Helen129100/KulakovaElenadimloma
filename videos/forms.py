from django import forms

from videos.models import Video


class VideoForm(forms.ModelForm):
    post = forms.CharField(
        label="",
        widget=forms.TextInput(
            attrs={
                "class": "form-control input_login_style",
                "placeholder": "Введите название видео",
            }
        ),
        max_length=255,
    )

    description = forms.CharField(
        label="Описание",
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control input_login_style",
                "rows": 4,
                "placeholder": "Введите описание видео...",
            }
        ),
    )

    tags = forms.CharField(
        label="Теги (через запятую)",
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control input_login_style",
                "placeholder": "например: музыка, блог",
            }
        ),
    )

    class Meta:
        model = Video
        fields = ["post", "description", "video_file", "tags"]

    def clean_video_file(self):
        VIDEO_FILE_TYPES = ["mp4"]
        uploaded_video = self.cleaned_data.get("video_file", False)
        extension = str(uploaded_video).split(".")[-1].lower()

        if not uploaded_video:
            raise forms.ValidationError("Загрузите видео")
        if extension not in VIDEO_FILE_TYPES:
            raise forms.ValidationError("Разрешены только .mp4 файлы")
        return uploaded_video

    def save(self, commit=True):
        instance = super().save(commit=False)
        tags_raw = self.cleaned_data.get("tags", "")
        tag_names = [name.strip() for name in tags_raw.split(",") if name.strip()]

        if commit:
            instance.save()
            instance.tags.clear()
            for name in tag_names:
                tag, created = Tag.objects.get_or_create(name=name)
                instance.tags.add(tag)
        return instance
