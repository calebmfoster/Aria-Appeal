import os
from huggingface_hub import snapshot_download

def download_models():
    print("Starting download of required models. This may take a while depending on your internet connection...")
    
    models = [
        "Qwen/Qwen2.5-3B-Instruct",
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
    ]
    
    for model_id in models:
        print(f"\nDownloading {model_id}...")
        try:
            # We use snapshot_download to cache the entire repository for local use later
            path = snapshot_download(repo_id=model_id, resume_download=True)
            print(f"Successfully downloaded {model_id} to {path}")
        except Exception as e:
            print(f"Error downloading {model_id}: {e}")
            print("Please ensure you have an active internet connection.")

if __name__ == "__main__":
    download_models()
    print("\nAll model caching complete!")
