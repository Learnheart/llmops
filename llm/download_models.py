"""Download models for LLM and Embedding."""

from huggingface_hub import hf_hub_download
from sentence_transformers import SentenceTransformer

MODEL_DIR = "/app/models"


def download_llm():
    """Download LLM model: Qwen2.5-0.5B-Instruct GGUF."""
    print("Downloading LLM model: Qwen2.5-0.5B-Instruct...")
    hf_hub_download(
        repo_id="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        filename="qwen2.5-0.5b-instruct-q4_k_m.gguf",
        local_dir=f"{MODEL_DIR}/llm",
    )
    print("LLM model downloaded!")


def download_embedding():
    """Download Embedding model: all-MiniLM-L6-v2."""
    print("Downloading Embedding model: all-MiniLM-L6-v2...")
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    model.save(f"{MODEL_DIR}/embedding/all-MiniLM-L6-v2")
    print("Embedding model downloaded!")


if __name__ == "__main__":
    download_llm()
    download_embedding()
    print("All models downloaded!")
