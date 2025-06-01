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
    """Извлекает аудио из видеофайла и сохраняет его во временный файл."""
    audio_path = video_path.rsplit(".", 1)[0] + ".mp3"  # Сохраним звук в mp3
    with VideoFileClip(video_path) as video:
        audio = video.audio
        audio.write_audiofile(audio_path)
    return audio_path


def convert_to_wav(audio_path, output_format="wav"):
    """Конвертирует аудиофайл в WAV (если он не в формате WAV)"""
    if not audio_path.lower().endswith(".wav"):
        sound = AudioSegment.from_file(audio_path)
        wav_path = audio_path.rsplit(".", 1)[0] + ".wav"
        sound.export(wav_path, format=output_format)
        return wav_path
    return audio_path


def remove_punctuation(text):
    """Удаляет пунктуацию из текста"""
    return text.translate(str.maketrans("", "", string.punctuation))


@login_required
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

            # Сначала сохраняем, чтобы файл появился на диске
            video.save()

            # Теперь безопасно получить путь
            video_path = video.video_file.path

            # Обработка видео
            if not process_video(video_path):
                # удалим файл из базы и диска, если не прошло проверку
                video.video_file.delete(save=False)
                video.delete()
                print("error")
                data["form_is_valid"] = False
                data["error"] = "Видео содержит запрещенные слова."
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


def remove_punctuation(text):
    """Удаляет пунктуацию из текста"""
    return text.translate(str.maketrans("", "", string.punctuation))


def find_matches(text, censored_words):
    morph = MorphAnalyzer()
    found_words = set()
    clean_text = remove_punctuation(text)
    words = clean_text.split()

    # Генерируем все формы целевых слов
    inflected_words = set()
    for target_word in censored_words:
        parsed_word = morph.parse(target_word)[0]
        inflected_words.update(
            [form.word for form in parsed_word.lexeme]
        )  # Добавляем все формы слова

    for word in words:
        parsed = morph.parse(word)[0]
        lemma = parsed.normal_form.lower()  # Приводим к нижнему регистру

        if lemma in inflected_words:
            found_words.add(lemma)

    return len(found_words) > 0


def audio_to_text(audio_path):
    """Конвертирует аудио в текст"""
    r = sr.Recognizer()
    try:
        # Конвертируем в WAV, если нужно
        wav_path = convert_to_wav(audio_path)

        with sr.AudioFile(wav_path) as source:
            audio = r.record(source)
        text = r.recognize_google(audio, language="ru-RU")  # Для русского
        return text
    except Exception as e:
        print(f"Ошибка распознавания в файле {os.path.basename(audio_path)}: {e}")
        return ""
    finally:
        # Удаляем временный WAV-файл, если он был создан
        if (
            "wav_path" in locals()
            and wav_path != audio_path
            and os.path.exists(wav_path)
        ):
            os.remove(wav_path)


def process_video(video_path):
    """Основная функция обработки видео с проверкой на цензуру"""
    audio_path = extract_audio_from_video(video_path)

    # Конвертируем аудио в текст
    text = audio_to_text(audio_path)
    result = True
    if text:

        has_matches = find_matches(text, censored_words)

        if has_matches:
            result = False
        else:
            result = True

    else:

        result = False
    return result


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
