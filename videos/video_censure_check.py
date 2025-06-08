import cv2
import torch
import sys
import os
import json
import subprocess
from pathlib import Path

# Добавляем yolov5 в путь
FILE = Path(__file__).resolve().parent
YOLOV5_DIR = FILE / "yolov5"
sys.path.append(str(YOLOV5_DIR))

from models.experimental import attempt_load
from utils.general import non_max_suppression
from utils.torch_utils import select_device


class VideoCensorship:
    def __init__(self):
        self.weights = (
            "/video/aicensure/censure/yolov5/runs/train/my_yolov5_run6/weights/best.pt"
        )
        self.device = select_device("")
        self.model = attempt_load(self.weights)
        self.model.to(self.device).eval()
        self.names = (
            self.model.module.names
            if hasattr(self.model, "module")
            else self.model.names
        )
        self.conf_thres = 0.50

    def analyze_video(self, video_path, json_output_path):
        """Анализирует видео и сохраняет данные о детекциях в JSON"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Ошибка: не удалось открыть видео.")

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        frame_count = 0
        blur_data = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            time_sec = frame_count / fps

            # Детекция объектов
            img = cv2.resize(frame, (640, 640))
            img_tensor = (
                torch.from_numpy(img).to(self.device).permute(2, 0, 1).float() / 255.0
            )
            img_tensor = img_tensor.unsqueeze(0)

            with torch.no_grad():
                pred = self.model(img_tensor)[0]
                pred = non_max_suppression(pred, conf_thres=self.conf_thres)[0]

            if pred is not None and len(pred):
                for *xyxy, conf, cls in pred:
                    class_id = int(cls.item())
                    if class_id == 0:  # Только нужные классы
                        x1, y1, x2, y2 = map(float, xyxy)
                        x1 = int(x1 / 640 * width)
                        x2 = int(x2 / 640 * width)
                        y1 = int(y1 / 640 * height)
                        y2 = int(y2 / 640 * height)

                        x1 = max(0, min(x1, width - 1))
                        x2 = max(0, min(x2, width - 1))
                        y1 = max(0, min(y1, height - 1))
                        y2 = max(0, min(y2, height - 1))

                        blur_data.append(
                            {
                                "start": round(time_sec, 2),
                                "end": round(time_sec + 1.0, 2),
                                "x": x1,
                                "y": y1,
                                "width": x2 - x1,
                                "height": y2 - y1,
                                "active": True,
                            }
                        )

        cap.release()

        # Сохраняем JSON
        os.makedirs(os.path.dirname(json_output_path), exist_ok=True)
        with open(json_output_path, "w") as f:
            json.dump(
                {
                    "video_path": video_path,
                    "fps": fps,
                    "width": width,
                    "height": height,
                    "detections": blur_data,
                },
                f,
                indent=2,
            )

        print(f"✅ Анализ завершен. JSON сохранен в: {json_output_path}")
        return json_output_path

    def apply_blur(self, video_path, json_path, output_path):
        """Применяет размытие на основе данных из JSON"""
        with open(json_path) as f:
            data = json.load(f)

        cap = cv2.VideoCapture(data["video_path"])
        if not cap.isOpened():
            raise Exception("Ошибка: не удалось открыть видео.")

        fps = data["fps"]
        width = data["width"]
        height = data["height"]

        out = cv2.VideoWriter(
            output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
        )

        frame_count = 0
        detections = data["detections"]
        detections_by_frame = {d["frame"]: d for d in detections}

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            if frame_count in detections_by_frame:
                det = detections_by_frame[frame_count]
                x1, y1 = det["x"], det["y"]
                x2, y2 = x1 + det["width"], y1 + det["height"]

                roi = frame[y1:y2, x1:x2]
                if roi.size > 0:
                    roi_blurred = cv2.GaussianBlur(roi, (51, 51), 30)
                    frame[y1:y2, x1:x2] = roi_blurred
                    print(f"🚀 Применено размытие на кадре {frame_count}")

            out.write(frame)

        cap.release()
        out.release()

        # Перекодировка для браузера
        final_output = output_path.replace(".mp4", "_encoded.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                output_path,
                "-vcodec",
                "libx264",
                "-acodec",
                "aac",
                "-movflags",
                "+faststart",
                final_output,
            ]
        )

        print(f"🎥 Видео с размытием сохранено: {final_output}")
        return final_output


# Пример использования
if __name__ == "__main__":
    processor = VideoCensorship()

    # 1. Сначала анализируем видео
    json_path = processor.analyze_video(
        "yolov5/data/images/video2.mp4", "blur_data/video_2.json"
    )

    # 2. Затем (по нажатию кнопки) применяем размытие
    # processor.apply_blur(
    #     "yolov5/data/images/video2.mp4",
    #     "blur_data/video_2.json",
    #     "/video/aicensure/censure/result/video_blurred.mp4"
    # )
