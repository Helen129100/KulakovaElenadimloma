import numpy as np
import librosa
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, Input
from pydub import AudioSegment
import io

# === Константы ===
SAMPLE_RATE = 16000
DURATION = 1.0
N_MELS = 40
AUDIO_LENGTH = int(SAMPLE_RATE * DURATION)
TARGET_SHAPE = (N_MELS, 32)


# === Аугментации ===
def augment_audio(y, sr):
    if np.random.rand() < 0.5:
        y = librosa.effects.time_stretch(y, rate=np.random.uniform(0.9, 1.1))
    if np.random.rand() < 0.5:
        y = librosa.effects.pitch_shift(y, sr=sr, n_steps=np.random.uniform(-2, 2))
    return y


# === Извлечение мел-спектрограммы ===
def extract_mel_spectrogram(file_path, augment=False):
    if file_path.lower().endswith(".mp3"):

        audio = (
            AudioSegment.from_mp3(file_path).set_frame_rate(SAMPLE_RATE).set_channels(1)
        )
        wav_io = io.BytesIO()
        audio.export(wav_io, format="wav")
        wav_io.seek(0)
        y, sr = librosa.load(wav_io, sr=SAMPLE_RATE)
    else:
        y, sr = librosa.load(file_path, sr=SAMPLE_RATE)

    y = librosa.util.fix_length(y, size=AUDIO_LENGTH)

    if augment:
        y = augment_audio(y, sr)

    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=N_MELS)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    mel_db = (mel_db - np.mean(mel_db)) / (np.std(mel_db) + 1e-6)

    if mel_db.shape[1] > TARGET_SHAPE[1]:
        mel_db = mel_db[:, : TARGET_SHAPE[1]]
    else:
        pad = TARGET_SHAPE[1] - mel_db.shape[1]
        mel_db = np.pad(mel_db, ((0, 0), (0, pad)), mode="constant")

    return mel_db


# === Модель ===
def create_cnn_model(input_shape):
    model = Sequential(
        [
            Input(shape=input_shape),
            Conv2D(32, (3, 3), activation="relu"),
            MaxPooling2D((2, 2)),
            Conv2D(64, (3, 3), activation="relu"),
            MaxPooling2D((2, 2)),
            Flatten(),
            Dense(128, activation="relu"),
            Dropout(0.3),
            Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model
