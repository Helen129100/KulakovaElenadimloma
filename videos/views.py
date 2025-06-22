# Импорт библиотек
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from videos.models import Video
from videos.forms import VideoForm
from django.db.models import Q  # Импортируем Q
from .models import Like, Subscription
import os
from django.conf import settings
from .video_censure_check import VideoCensorship
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
import cv2
import torch
import subprocess
import sys
import numpy as np
import speech_recognition as sr
from moviepy.editor import *
import string
from pydub import AudioSegment
import whisper
import math
from moviepy.editor import VideoFileClip
import shutil  # Добавляем импорт shutil
from django.core.files import File
from urllib.parse import unquote  # Добавьте этот импорт

User = get_user_model()
censored_words = {"бежать", "говорить", "писать"}  # Пример для русского
weights = "./yolov5/runs/train/my_yolov5_run6/weights/"

conf_thres = 0.50
censored_words = [
    "убивать",
    "резать",
    "вешаться",
    "труп",
    "изнасилование",
    "педофил",
    "нацист",
    "фашист",
    "террорист",
    "зомбировать",
    "педераст",
    "трансгендер",  # в оскорбительном контексте
    "дауненок",
    "выкидыш",
    "сдохнуть",
    "гнида",
    "клоп",
    "сучонок",
    "ублюдок",
    "недочеловек",
    # Существительные
    "человек",
    "время",
    "дело",
    "жизнь",
    "работа",
    # Глаголы
    "быть",
    "делать",
    "говорить",
    "иметь",
    "знать",
]


def remove_punctuation(text):
    return text.translate(str.maketrans("", "", string.punctuation))


def extract_from_video(video_path, output_audio_path=None):
    """Извлекает аудио из видео с улучшенной обработкой ошибок"""
    try:
        # Проверка существования видеофайла
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Видеофайл не найден: {video_path}")

        # Создаем путь для аудио, если не указан
        if output_audio_path is None:
            output_audio_path = os.path.splitext(video_path)[0] + "_audio.wav"

        # Проверяем доступность FFmpeg
        try:
            # Извлекаем аудио
            audio = AudioSegment.from_file(video_path)

            # Проверяем, что аудио было успешно извлечено
            if audio.duration_seconds == 0:
                raise ValueError(
                    "Видео не содержит аудиодорожки или длительность равна 0"
                )

            # Экспортируем в WAV
            audio.export(
                output_audio_path, format="wav", parameters=["-ac", "2", "-ar", "44100"]
            )

            return output_audio_path

        except Exception as e:
            # Удаляем файл, если он был частично создан
            if os.path.exists(output_audio_path):
                os.remove(output_audio_path)
            raise  # Повторно поднимаем исключение

    except Exception as e:
        print(f"Ошибка при извлечении аудио: {e}")
        return None


def video_audio_censure(video_path, output_audio_path):
    """
    Применяет аудио-цензуру и сохраняет файл в output_audio_path.
    Возвращает путь к новому аудиофайлу.
    """
    import os
    import shutil
    import whisper
    from pydub import AudioSegment
    import uuid

    temp_files = []

    try:

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Входной видеофайл не найден: {video_path}")

        # 1. Извлекаем аудио
        temp_audio_path = f"temp_audio_{uuid.uuid4()}.wav"
        audio_path = extract_from_video(video_path, temp_audio_path)
        if audio_path is None or not os.path.exists(audio_path):
            raise ValueError("Не удалось извлечь аудио из видео")
        temp_files.append(audio_path)

        # 2. Whisper распознавание
        model = whisper.load_model("base", device="cpu")
        result = model.transcribe(audio_path, word_timestamps=True)

        # 3. Загружаем аудио
        audio_segment = AudioSegment.from_wav(audio_path)
        morph = MorphAnalyzer()
        output_audio = AudioSegment.silent(duration=0)
        last_end = 0

        for segment in result["segments"]:
            for word in segment["words"]:
                cleaned_word = remove_punctuation(word["word"])
                start_ms = int(word["start"] * 1000)
                end_ms = int(word["end"] * 1000)
                parsed = morph.parse(cleaned_word.strip().lower())[0]
                cleaned_word = parsed.normal_form
                if cleaned_word in censored_words:
                    print(f"🚫 Цензурируем слово: {cleaned_word}")
                    output_audio += AudioSegment.silent(duration=end_ms - last_end)
                else:
                    output_audio += audio_segment[last_end:end_ms]

                last_end = end_ms

        # Добавим оставшийся хвост
        output_audio += audio_segment[last_end:]

        # 4. Сохраняем в указанный путь
        output_audio.export(output_audio_path, format="wav")
        print(f"✅ Аудиофайл сохранен: {output_audio_path}")

        return output_audio_path

    except Exception as e:
        print(f"❌ Ошибка в video_audio_censure: {e}")
        shutil.copy2(video_path, output_audio_path)
        return output_audio_path

    finally:
        for file_path in temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Ошибка при удалении временного файла {file_path}: {e}")


def delete_video_before(request):
    try:
        video_id = int(request.POST.get("video_id"))
        video = get_object_or_404(Video, id=video_id)
        video.delete()
        return JsonResponse(
            {"status": "success", "message": "Video deleted successfully"}
        )
    except ValueError:
        return JsonResponse(
            {"status": "error", "message": "Invalid video ID"}, status=400
        )
    except Video.DoesNotExist:
        return JsonResponse(
            {"status": "error", "message": "Video not found"}, status=404
        )


def delete_video(request, video_id):
    video = get_object_or_404(Video, id=video_id)

    if video.user == request.user:
        video.delete()

    else:
        messages.error(request, "У вас нет прав для удаления этого видео.")

    return redirect(
        "profile", username=request.user.username
    )  # перенаправления на профиль


def blur_video(video_path, json_path, output_path):
    cap = None
    out = None
    print("Заходит в блюр")
    try:
        # Проверка существования файлов
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Видео файл не найден: {video_path}")
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON файл не найден: {json_path}")

        # Загрузка данных из JSON
        try:
            with open(json_path, "r") as f:
                blur_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка парсинга JSON: {str(e)}") from e

        # Проверка структуры JSON
        required_keys = ["fps", "width", "height", "detections"]
        if not all(key in blur_data for key in required_keys):
            raise ValueError(
                "Некорректная структура JSON: отсутствуют обязательные поля"
            )

        # Получаем параметры видео
        fps = blur_data["fps"]
        width = blur_data["width"]
        height = blur_data["height"]
        detections = blur_data["detections"]

        # Открываем видео
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError("Не удалось открыть видео файл")

        # Создаем writer для выходного видео
        try:
            out = cv2.VideoWriter(
                output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
            )
            if not out.isOpened():
                raise IOError("Не удалось создать выходной видео файл")
        except Exception as e:
            raise IOError(f"Ошибка при создании VideoWriter: {str(e)}")

        frame_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            current_time = frame_count / fps

            # Применяем размытия
            for detection in detections:
                try:
                    if not detection.get("active", False):
                        continue

                    if detection["start"] <= current_time <= detection["end"]:
                        x = int(detection["x"])
                        y = int(detection["y"])
                        w = int(detection["width"])
                        h = int(detection["height"])

                        # Проверка границ
                        x1 = max(0, min(x, width - 1))
                        y1 = max(0, min(y, height - 1))
                        x2 = max(0, min(x + w, width - 1))
                        y2 = max(0, min(y + h, height - 1))

                        if x2 > x1 and y2 > y1:
                            roi = frame[y1:y2, x1:x2]
                            roi_blurred = cv2.GaussianBlur(roi, (51, 51), 30)
                            frame[y1:y2, x1:x2] = roi_blurred
                except Exception as e:
                    print(f"Ошибка при обработке детекции: {str(e)}")
                    continue

            out.write(frame)

        # Закрываем ресурсы
        if cap:
            cap.release()
        if out:
            out.release()

        # Перекодируем видео
        final_output_path = output_path.replace(".mp4", "_encoded.mp4")
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    output_path,  # видео без аудио
                    "-i",
                    video_path,  # оригинальное видео с аудио
                    "-c:v",
                    "libx264",  # кодек для видео
                    "-c:a",
                    "aac",  # кодек для аудио
                    "-map",
                    "0:v:0",  # взять видео-дорожку из первого файла
                    "-map",
                    "1:a:0",  # взять аудио-дорожку из второго файла
                    "-movflags",
                    "+faststart",
                    final_output_path,
                ],
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Ошибка ffmpeg: {e.stderr.decode()}") from e
        except FileNotFoundError:
            raise RuntimeError(
                "ffmpeg не найден. Убедитесь, что ffmpeg установлен и добавлен в PATH"
            )

        # Удаляем временный файл
        if os.path.exists(output_path):
            os.remove(output_path)

        return final_output_path

    except Exception as e:
        # Удаляем частично созданные файлы при ошибке
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        if "final_output_path" in locals() and os.path.exists(final_output_path):
            try:
                os.remove(final_output_path)
            except:
                pass
        raise  # Повторно поднимаем исключение для обработки в вызывающем коде
    finally:
        # Гарантированно освобождаем ресурсы
        if cap and cap.isOpened():
            cap.release()
        if out and out.isOpened():
            out.release()


def check_censure_view(request):
    # Инициализируем стандартный ответ
    response_data = {
        "success": False,
        "message": "Неверный запрос",
        "censorship_result": 0,
        "video_url": "",
        "json_video_path": "",
        "video_id": "",
    }

    # Проверяем условия
    if request.method == "POST" and request.FILES.get("video_file"):
        form = VideoForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                # Сохраняем видео
                video = form.save(commit=False)
                video.user = request.user
                video.video_file = form.cleaned_data["video_file"]
                video.post = form.cleaned_data["post"]
                video.description = form.cleaned_data["description"]

                print(video.description)

                video.censorship_flag = 0

                video.save()
                # video.tags.set(form.cleaned_data["tags"])  # Затем устанавливаем теги

                # Получаем данные о видео
                video_path = video.video_file.path
                video_url = video.video_file.url

                # Проверяем цензуру
                censure_result = check_censure(video_path)

                # Обрабатываем разные форматы возврата check_censure
                if isinstance(censure_result, JsonResponse):
                    data = json.loads(censure_result.content)
                    response_data.update(data)
                else:
                    response_data.update(
                        {
                            "success": censure_result.get("success", True),
                            "message": censure_result.get("message", ""),
                            "censorship_result": censure_result.get(
                                "censorship_result", 0
                            ),
                            "json_video_path": censure_result.get(
                                "json_video_path", ""
                            ),
                            "video_url": video_url,
                            "video_id": video.id,
                        }
                    )

                response_data["success"] = True

            except Exception as e:

                response_data.update(
                    {"success": False, "message": f"Ошибка обработки: {str(e)}"}
                )
                # В случае ошибки удаляем видео, если оно было сохранено
                if "video" in locals() and video.pk:
                    video.video_file.delete(save=False)
                    video.delete()
        else:
            response_data.update(
                {"success": False, "message": "Форма невалидна: " + str(form.errors)}
            )

    # Единый возврат в конце функции

    return JsonResponse(response_data)


def check_censure(video_path):
    result_censure = 4
    result_text = ""

    video_name = os.path.splitext(os.path.basename(video_path))[0]
    json_name = video_name + ".json"
    json_video_path = os.path.join("media", "json_video", json_name)
    print(f"json_video_path {json_video_path}")
    processor = VideoCensorship()
    result_video = processor.analyze_video(video_path, json_video_path)
    result_audio = process_video(video_path)

    if result_video:
        result_text += "📛 Видео не прошло цензуру.\n"
        result_censure = 1
    else:
        result_text += "✅ Видео прошло цензуру.\n"

    if result_audio:
        result_text += "📛 Аудио не прошло цензуру."
        if result_censure == 1:
            result_censure = 3
        else:
            result_censure = 2
    else:
        result_text += "✅ Аудио прошло цензуру."

    # Возвращаем словарь вместо JsonResponse
    return {
        "success": True,
        "message": result_text,
        "censorship_result": result_censure,
        "json_video_path": json_name,
    }


# Функция извлечения аудио


def extract_audio_from_video(video_path):
    """
    Извлекает аудио из видео и сохраняет его в mp3.
    Возвращает путь к аудио-файлу или None, если не удалось.
    """

    print(video_path)
    if not os.path.exists(video_path):
        print("❌ Файл не найден.")
        return None

    try:
        clip = VideoFileClip(video_path)

        if not clip.audio:
            print("❌ В видео нет аудио-дорожки.")
            clip.close()
            return None

        base, _ = os.path.splitext(video_path)
        audio_path = base + ".mp3"

        clip.audio.write_audiofile(audio_path)
        clip.close()
        return audio_path

    except Exception as e:
        print(f"❌ Ошибка при извлечении аудио: {e}")
        return None


def add_video(request):
    import os
    import shutil
    from django.conf import settings
    from django.core.files import File
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    from django.template.loader import render_to_string

    from .forms import VideoForm
    from .models import Video

    from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip

    response_data = {"form_is_valid": False, "error": "", "video_form": ""}
    form = VideoForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        video_id = int(request.POST.get("video_id", 0))
        censorship_flag = int(request.POST.get("censorship_flag", 0))
        json_name = request.POST.get("json_name", "")

        try:
            # Создание или обновление объекта Video
            if video_id == 0:
                form = VideoForm(request.POST or None, request.FILES or None)
                video_by_form = form.save(commit=False)
                video_by_form.user = request.user
                video_by_form.video_file = form.cleaned_data["video_file"]
                video_by_form.post = form.cleaned_data["post"]
                video = video_by_form
            else:
                video = get_object_or_404(Video, id=video_id, user=request.user)
                video.censorship_flag = censorship_flag

            video.save()
            original_path = video.video_file.path
            print(f"✅ Оригинальный файл сохранен: {original_path}")

            processed_path = None
            if censorship_flag in {1, 2, 3}:
                print(f"⚙️ Применяем цензуру типа {censorship_flag}")
                temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_censored")
                os.makedirs(temp_dir, exist_ok=True)
                temp_output = os.path.join(
                    temp_dir, f"censored_{os.path.basename(original_path)}"
                )

                if censorship_flag == 1:
                    # Видео цензура
                    json_path = os.path.join(
                        settings.MEDIA_ROOT, "json_video", json_name
                    )
                    processed_path = blur_video(original_path, json_path, temp_output)

                elif censorship_flag == 2:
                    # Аудио цензура
                    processed_path = video_audio_censure(original_path, temp_output)

                elif censorship_flag == 3:
                    # Видео + Аудио
                    json_path = os.path.join(
                        settings.MEDIA_ROOT, "json_video", json_name
                    )
                    temp_video_path = blur_video(original_path, json_path, temp_output)
                    output_audio_file = video_audio_censure(
                        temp_video_path, temp_output
                    )

                    # Сборка нового видео с новым аудио
                    video_clip = VideoFileClip(temp_video_path)
                    new_audio = AudioFileClip(output_audio_file)
                    final_clip = video_clip.set_audio(CompositeAudioClip([new_audio]))

                    final_clip.write_videofile(
                        original_path, codec="libx264", audio_codec="aac"
                    )

                    # Очистка
                    video_clip.close()
                    new_audio.close()
                    final_clip.close()

                    if os.path.exists(temp_video_path):
                        os.remove(temp_video_path)
                    if os.path.exists(output_audio_file):
                        os.remove(output_audio_file)

                    processed_path = original_path

                # Замена оригинального файла (если цензура 1 или 2)
                if (
                    censorship_flag in {1, 2}
                    and processed_path
                    and os.path.exists(processed_path)
                ):
                    if os.path.exists(original_path):
                        os.remove(original_path)
                    shutil.move(processed_path, original_path)

                    with open(original_path, "rb") as f:
                        video.video_file.save(
                            os.path.basename(original_path), File(f), save=True
                        )

            response_data["form_is_valid"] = True

        except Exception as e:
            print(f"❌ Ошибка: {str(e)}")

            # Откат изменений
            if "video" in locals() and video.pk:
                if video.video_file and os.path.exists(video.video_file.path):
                    video.video_file.delete(save=False)
                video.delete()

            response_data.update(
                {
                    "error": f"Ошибка обработки видео: {str(e)}",
                    "video_form": render_to_string(
                        "videos/video_form.html", {"form": form}, request=request
                    ),
                }
            )
            return JsonResponse(response_data, status=400)

    else:
        response_data["video_form"] = render_to_string(
            "videos/video_form.html", {"form": form}, request=request
        )

    return JsonResponse(response_data)


def get_form(request):
    response_data = {"form_is_valid": False, "error": "", "video_form": ""}

    # Получаем video_id из GET-параметров
    video_id = request.GET.get("video_id")

    if video_id:
        try:
            video_id = int(video_id)
            video = get_object_or_404(Video, id=video_id, user=request.user)
            form = VideoForm(instance=video)
        except ValueError:
            form = VideoForm()
    else:
        form = VideoForm()

    response_data["video_form"] = render_to_string(
        "videos/video_form.html", {"form": form}, request=request
    )
    return JsonResponse(response_data)


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
        return True

    features = np.expand_dims(features, axis=(0, -1))

    # 3) Загружаем модель и предсказываем
    model_path = os.path.join(os.path.dirname(__file__), "best_model.h5")
    model = load_model(model_path)
    prediction = float(model.predict(features)[0][0])

    print(f"🔍 Вероятность запрещённого слова: {prediction:.3f}")
    return prediction >= 0.7


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
    all_videos = (
        Video.objects.filter(parent=None).filter(user=page_user).order_by("-date")
    )
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


def home(request):
    try:
        # Базовый запрос - только видео без родителей (основные записи)
        videos = Video.objects.filter(parent=None)

        # Исключаем видео без прикрепленных файлов
        videos = videos.exclude(video_file="")

        # Сортировка по дате (новые сначала)
        videos = videos.order_by("-date")

        # Обработка поискового запроса
        search_query = request.GET.get("q", "")
        if search_query:
            videos = videos.filter(
                Q(post__icontains=search_query) | Q(video_file__icontains=search_query)
            )

        # Пагинация
        paginator = Paginator(videos, 20)
        page_number = request.GET.get("page")

        try:
            page_obj = paginator.get_page(page_number)
        except (EmptyPage, PageNotAnInteger):
            page_obj = paginator.get_page(1)

        return render(
            request,
            "videos/home.html",
            {
                "videos": page_obj,
                "search_query": search_query,
            },
        )

    except Exception as e:
        # Логирование ошибки (в продакшне используйте logging)
        print(f"Error in home view: {str(e)}")

        # Возвращаем "безопасный" вариант с ограниченным набором видео
        safe_videos = (
            Video.objects.filter(parent=None)
            .exclude(video_file="")
            .order_by("-date")[:20]
        )

        return render(
            request,
            "videos/home.html",
            {
                "videos": safe_videos,
                "search_query": "",
                "error": "Произошла ошибка при загрузке видео. Показаны последние записи.",
            },
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
    video_url = request.GET.get("video")

    json_video = request.GET.get("json_video")
    video_id = request.GET.get("video_id")
    censorship_flag = request.GET.get("censorship_flag")
    username = request.GET.get("username")
    print(json_video)
    return render(
        request,
        "videos/video_editor.html",
        {
            "video_url": video_url,
            "json_video": json_video,
            "video_id": video_id,
            "censorship_flag": censorship_flag,
            "username": username,
        },
    )


def save_json_video(request):
    if request.method == "POST":
        try:
            # Получаем путь из GET-параметра
            filepath = unquote(request.GET.get("filepath", ""))

            if not filepath:
                return JsonResponse(
                    {"status": "error", "message": "Не указан filepath"}, status=400
                )

            # Безопасная обработка пути
            filename = os.path.basename(filepath)
            if not filename.endswith(".json"):
                filename += ".json"

            save_dir = os.path.join(settings.MEDIA_ROOT, "json_video")
            os.makedirs(save_dir, exist_ok=True)
            file_path = os.path.join(save_dir, filename)

            # Защита от path traversal
            if not os.path.abspath(file_path).startswith(os.path.abspath(save_dir)):
                return JsonResponse(
                    {"status": "error", "message": "Недопустимый путь"}, status=400
                )

            # Получаем и сохраняем данные
            data = json.loads(request.body)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return JsonResponse(
                {"status": "success", "message": "✅ Данные сохранены!"}
            )

        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "error", "message": "Невалидный JSON"}, status=400
            )
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse(
        {"status": "error", "message": "Только POST-запрос"}, status=405
    )


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
