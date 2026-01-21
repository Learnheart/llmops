"""Test case for Prompt Generator service."""

import sys
sys.path.insert(0, "C:/Projects/LLMOps_v2")

from llm.models import LLMModel
from config_generator.prompt_generator.analyzer import analyze_and_generate


def test_prompt_generator():
    """Test prompt generator with a sample agent description."""

    # Config - update path to your model
    MODEL_PATH = "C:/Models/your-model.gguf"  # TODO: Update this path

    # Sample agent description
    agent_description = """
    Tạo một AI assistant hỗ trợ khách hàng cho công ty thương mại điện tử.
    Agent cần có khả năng:
    - Trả lời câu hỏi về sản phẩm, giá cả, khuyến mãi
    - Hỗ trợ theo dõi đơn hàng
    - Xử lý khiếu nại và hoàn tiền
    - Giọng điệu thân thiện, chuyên nghiệp
    - Không được tiết lộ thông tin nội bộ công ty
    """

    print("=" * 60)
    print("PROMPT GENERATOR TEST")
    print("=" * 60)
    print(f"\nAgent Description:\n{agent_description}")
    print("=" * 60)

    # Load LLM
    print("\nLoading LLM model...")
    llm = LLMModel(model_path=MODEL_PATH, n_ctx=4096)
    llm.load()
    print("Model loaded successfully!")

    # Run prompt generator
    print("\nRunning prompt generator...")
    result = analyze_and_generate(llm=llm, agent_description=agent_description)

    # Print results
    print("\n" + "=" * 60)
    print("ANALYSIS RESULT")
    print("=" * 60)
    print(f"Selected Templates: {[t.value for t in result.analysis.selected_templates]}")
    print(f"Domain: {result.analysis.domain}")
    print(f"Tone: {result.analysis.tone}")
    print(f"Key Capabilities: {result.analysis.key_capabilities}")
    print(f"Constraints: {result.analysis.constraints}")
    print(f"Reasoning: {result.analysis.reasoning}")

    print("\n" + "=" * 60)
    print("GENERATED PROMPTS")
    print("=" * 60)
    for i, prompt in enumerate(result.generated_prompts, 1):
        print(f"\n--- Prompt {i} ({prompt.template_type.value}) ---")
        print(prompt.prompt)
        print("-" * 40)

    # Cleanup
    llm.unload()
    print("\nTest completed!")


if __name__ == "__main__":
    test_prompt_generator()
