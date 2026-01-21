"""Simple test for LLM and Embedding models."""

import sys
sys.path.insert(0, "c:/Projects/LLMOps_v2")

from llm import EmbeddingModel


def test_embedding():
    """Test embedding model with HuggingFace model name."""
    print("=== Test Embedding ===")

    # Use HuggingFace model name directly (will auto-download)
    model = EmbeddingModel(model_path="sentence-transformers/all-MiniLM-L6-v2")
    model.load()

    texts = ["Hello world", "Xin chào"]
    vectors = model.embed(texts)

    print(f"Texts: {texts}")
    print(f"Dimension: {model.dimension}")
    print(f"Vector 1 (first 5): {vectors[0][:5]}")
    print("Embedding OK!\n")


if __name__ == "__main__":
    test_embedding()
