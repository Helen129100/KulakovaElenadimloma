# Импорт библиотек
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from videos.models import Video
from videos.forms import VideoForm
from django.db.models import Q  # Импортируем Q
from .models import Like, Subscription
import os
from moviepy.editor import VideoFileClip
import speech_recognition as sr
import string
from pydub import AudioSegment
from pymorphy2 import MorphAnalyzer  # Добавьте этот импорт
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from .model import extract_mel_spectrogram
from tensorflow.keras.models import load_model
import numpy as np
import json

User = get_user_model()
censored_words = {"бежать", "говорить", "писать"}  # Пример для русского


def delete_video(request, video_id):
    video = get_object_or_404(Video, id=video_id)

    if video.user == request.user:
        video.delete()

    else:
        messages.error(request, "У вас нет прав для удаления этого видео.")

    return redirect(
        "profile", username=request.user.username
    )  # перенаправления на профиль


# Функция извлечения аудио
def extract_audio_from_video(video_path):
    """
    Извлекает аудио из видео и сохраняет его в mp3.
    Возвращает путь к аудио-файлу или None, если не удалось.
    """
    try:
        with VideoFileClip(video_path) as clip:
            audio = clip.audio
            if audio is None:
                print("❌ В видео нет аудио-дорожки")
                return None

            base, _ = os.path.splitext(video_path)
            audio_path = base + ".mp3"

            audio.write_audiofile(audio_path)
            return audio_path

    except Exception as e:
        print(f"❌ Ошибка при извлечении аудио: {e}")
        return None


def add_video(request):
    data = {}
    form = VideoForm()

    if request.method == "POST":
        form = VideoForm(request.POST, request.FILES)

        if form.is_valid():
            video = form.save(commit=False)
            video.user = request.user
            video.video_file = form.cleaned_data.get("video_file")
            video.post = form.cleaned_data.get("post")
            video.save()

            video_path = video.video_file.path
            censorship_mode = request.POST.get("censorship_mode")

            # Проверка на цензуру
            if not process_video(video_path):
                if censorship_mode:
                    # Применить автоматическую цензуру
                    # apply_audio_censorship(video_path, censorship_mode)
                    data["form_is_valid"] = True
                    return JsonResponse(data)
                else:
                    # Удалить неподходящее видео
                    video.video_file.delete(save=False)
                    video.delete()
                    data["form_is_valid"] = False
                    data["error"] = "Видео не прошло цензуру"
                    data["video_form"] = render_to_string(
                        "videos/video_form.html", {"form": form}, request=request
                    )
                    return JsonResponse(data)

            data["form_is_valid"] = True
            return JsonResponse(data)

        else:
            data["form_is_valid"] = False
            data["video_form"] = render_to_string(
                "videos/video_form.html", {"form": form}, request=request
            )

    data["video_form"] = render_to_string(
        "videos/video_form.html", {"form": form}, request=request
    )
    return JsonResponse(data)


def process_video(video_path):
    # 1) Извлекаем аудио
    audio_path = extract_audio_from_video(video_path)
    if not audio_path:
        # не смогли получить аудио — отклоняем видео
        return True

    print("🎧 Аудио извлечено:", audio_path)

    # 2) Получаем фичи
    try:
        features = extract_mel_spectrogram(audio_path, augment=False)
    except Exception as e:
        print(f"❌ Ошибка при извлечении мел-спектрограммы: {e}")
        return False

    features = np.expand_dims(features, axis=(0, -1))

    # 3) Загружаем модель и предсказываем
    model_path = os.path.join(os.path.dirname(__file__), "best_model.h5")
    model = load_model(model_path)
    prediction = float(model.predict(features)[0][0])

    print(f"🔍 Вероятность запрещённого слова: {prediction:.3f}")
    return prediction <= 0.7


@login_required
def edit_video(request, id):
    data = {}
    video = get_object_or_404(Video, pk=id)

    if request.method == "POST":
        form = VideoForm(request.POST, request.FILES, instance=video)
        if form.is_valid():
            form.save()
            data["form_is_valid"] = True
            return JsonResponse(data)
        else:
            data["form_is_valid"] = False
            # Исправлено: используем текущую форму с ошибками валидации
            data["edit_video"] = render_to_string(
                "videos/edit_video.html", {"form": form}, request=request
            )
    else:
        form = VideoForm(instance=video)  # Инициализация формы при GET

    data["edit_video"] = render_to_string(
        "videos/edit_video.html", {"form": form}, request=request
    )
    return JsonResponse(data)


@login_required
def video(request, id):
    video = get_object_or_404(Video, id=id)
    is_subscribed = (
        request.user.is_authenticated
        and Subscription.objects.filter(user=request.user, channel=video.user).exists()
    )
    user_liked = Like.objects.filter(
        user=request.user, video=video
    ).exists()  # Проверяем, есть ли лайк
    side_videos = (
        Video.objects.filter(parent=None).order_by("?").exclude(id=id)[:4]
    )  # noqa: E501
    return render(
        request,
        "videos/video.html",
        {
            "video": video,
            "side_videos": side_videos,
            "is_subscribed": is_subscribed,  # Добавим переменную is_subscribed в контекст
            "user_liked": user_liked,  # Добавили переменную user_liked в контекст
        },
    )  # noqa: E501


@login_required
def comment(request):
    data = {}
    if request.method == "POST":
        video_id = request.POST["video_id"]
        video = Video.objects.get(pk=video_id)
        post = request.POST["post"]
        post = post.strip()
        if len(post) > 0:
            user = request.user
            video.comment(user=user, post=post)
            data["partial_video_comments"] = render_to_string(
                "videos/partial_video_comments.html", {"video": video}, request=request
            )  # noqa: E501
            data["comment_count"] = video.calculate_comments()
            return JsonResponse(data)
        else:
            return JsonResponse(data)


@login_required
def profile(request, username):
    page_user = get_object_or_404(User, username=username)
    all_videos = Video.objects.filter(parent=None).filter(user=page_user)
    subscriptions = Subscription.objects.filter(user=request.user)
    return render(
        request,
        "videos/profile.html",
        {
            "page_user": page_user,
            "all_videos": all_videos,
            "subscriptions": subscriptions,
        },
    )  # noqa: E501


@login_required
def subscription(request, username):
    page_user = get_object_or_404(User, username=username)

    subscriptions = Subscription.objects.filter(user=request.user)
    return render(
        request,
        "videos/subscription.html",
        {
            "page_user": page_user,
            "subscriptions": subscriptions,
        },
    )  # noqa: E501


def liked_videos(request, username):
    user = request.user  # или получите пользователя по имени
    liked_videos = Like.objects.filter(user=user).select_related("video")

    return render(
        request,
        "videos/liked_videos.html",
        {"page_user": user, "liked_videos": liked_videos},
    )


@login_required
def remove(request):
    data = {}
    comment_id = request.POST.get("comment_id")
    comment = Video.objects.get(pk=comment_id)
    if comment.user == request.user:
        parent = comment.parent
        comment.delete()
        data["comment_count"] = parent.calculate_comments()

    data["partial_video_comments"] = render_to_string(
        "videos/partial_video_comments.html", {"video": parent}, request=request
    )  # noqa: E501
    return JsonResponse(data)


def increment_views(request):
    video_id = request.POST.get("video_id")
    video = Video.objects.get(id=video_id)
    video.increment_views()
    print("успез")
    return JsonResponse({"success": True})


@login_required
def like(request):
    if request.method == "POST":
        video_id = request.POST.get("video_id")
        video = get_object_or_404(Video, id=video_id)
        user = request.user

        # Check if the user has already liked the video
        like_exists = Like.objects.filter(video=video, user=user).exists()

        if like_exists:
            # Remove the like
            Like.objects.filter(video=video, user=user).delete()
            video.likes -= 1
            video.save()
            return JsonResponse({"likes": video.likes, "action": "removed"})
        else:
            # Add a new like
            Like.objects.create(video=video, user=user)
            video.likes += 1
            video.save()
            return JsonResponse({"likes": video.likes, "action": "added"})


@login_required
def home(request):
    videos = Video.objects.filter(parent=None).order_by("?")
    paginator = Paginator(videos, 20)
    page = request.GET.get("page")
    all_videos = paginator.get_page(page)

    # Add search functionality
    search_query = request.GET.get("q", "")
    if search_query:
        videos = Video.objects.filter(
            Q(post__icontains=search_query) | Q(video_file__icontains=search_query)
        )
        paginator = Paginator(videos, 6)
        page = request.GET.get("page")
        all_videos = paginator.get_page(page)

    return render(
        request,
        "videos/home.html",
        {"videos": all_videos, "search_query": search_query},
    )


@login_required
def subscribe(request):
    if request.method == "POST":
        user = request.user
        channel_id = request.POST.get("channel_id")
        channel = User.objects.get(id=channel_id)

        # Проверка, существует ли уже подписка
        subscription, created = Subscription.objects.get_or_create(
            user=user, channel=channel
        )

        if created:
            return JsonResponse({"status": "subscribed", "channel_id": channel_id})
        else:
            # Если подписка уже существует, удалите её
            subscription.delete()
            return JsonResponse({"status": "unsubscribed", "channel_id": channel_id})


import json
from django.http import JsonResponse
from django.utils import translation


def set_language(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Получаем данные
            language = data.get("lang_code")  # Извлекаем язык

            # Проверяем, находится ли язык в допустимых значениях
            if language not in ["en", "ru"]:
                print("Invalid request method444.")  # Логируем неверный метод
                return JsonResponse({"success": False, "error": "Invalid language."})

            # Устанавливаем язык
            translation.activate(language)
            request.session[translation.LANGUAGE_SESSION_KEY] = language

            print(f"Language set to: {language}")  # Логируем результат
            return JsonResponse({"success": True})  # Возвращаем успешный ответ
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON."})
        except Exception as e:
            print(f"Error occurred: {str(e)}")  # Логируем ошибки
            return JsonResponse({"success": False, "error": str(e)})

    print("Invalid request method.")  # Логируем неверный метод
    return JsonResponse({"success": False, "error": "Invalid request method."})


def video_editor(request):
    return render(request, "videos/video_editor.html")


def blur_data_api(
    request,
):
    blur_file = f"media/json_video/video_blurred.mp4.json"
    if request.method == "GET":
        with open(blur_file) as f:
            return JsonResponse(json.load(f), safe=False)
    elif request.method == "POST":
        with open(blur_file, "w") as f:
            json.dump(json.loads(request.body), f, indent=2)
        return JsonResponse({"status": "ok"})
