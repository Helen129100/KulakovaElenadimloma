from huggingface_hub import snapshot_download

repo_id = "guillaumekln/faster-whisper-base"
cache_dir = "/video/ConnectUs/whisper-base"

print(f"Скачиваем модель {repo_id} в {cache_dir}...")
snapshot_download(repo_id=repo_id, cache_dir=cache_dir)
print("Скачивание завершено.")
