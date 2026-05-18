import os
from huggingface_hub import snapshot_download

def download_qwen3_tts_models():
    """
    Downloads the Qwen3-TTS models from Hugging Face to a local directory.
    This prevents the large weights from being downloaded repeatedly or blocking server startup.
    """
    repo_id = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
    local_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", repo_id.replace("/", "_"))
    
    print(f"Downloading {repo_id} to {local_dir}...")
    
    # Download the model snapshot
    # We exclude large unnecessary files if any, but grab the pytorch weights and config
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        ignore_patterns=["*.msgpack", "*.h5"], # Ignore alternative weight formats if present
        local_dir_use_symlinks=False
    )
    
    print(f"Download complete! Models saved to {local_dir}")
    print(f"To use local weights, set QWEN_MODEL_PATH='{local_dir}' in your .env file.")

if __name__ == "__main__":
    download_qwen3_tts_models()
