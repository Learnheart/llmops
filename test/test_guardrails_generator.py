"""Test case for Guardrails Generator service."""

import sys
sys.path.insert(0, "C:/Projects/LLMOps_v2")

from llm.models import LLMModel
from config_generator.guardrails_generator.analyzer import analyze_and_generate


def test_guardrails_generator():
    """Test guardrails generator with a sample agent description."""

    # Config - update path to your model
    MODEL_PATH = "C:/Models/your-model.gguf"  # TODO: Update this path

    # Sample agent description
    agent_description = """
    Tạo một AI assistant hỗ trợ khách hàng cho công ty thương mại điện tử.
    Agent cần có khả năng:
    - Trả lời câu hỏi về sản phẩm, giá cả, khuyến mãi
    - Hỗ trợ theo dõi đơn hàng (cần xử lý thông tin cá nhân khách hàng)
    - Xử lý khiếu nại và hoàn tiền
    - Giọng điệu thân thiện, chuyên nghiệp
    - Không được tiết lộ thông tin nội bộ công ty
    - Agent sẽ được deploy public cho khách hàng sử dụng
    """

    print("=" * 60)
    print("GUARDRAILS GENERATOR TEST")
    print("=" * 60)
    print(f"\nAgent Description:\n{agent_description}")
    print("=" * 60)

    # Load LLM
    print("\nLoading LLM model...")
    llm = LLMModel(model_path=MODEL_PATH, n_ctx=4096)
    llm.load()
    print("Model loaded successfully!")

    # Run guardrails generator
    print("\nRunning guardrails generator...")
    result = analyze_and_generate(llm=llm, agent_description=agent_description)

    # Print results
    print("\n" + "=" * 60)
    print("ANALYSIS RESULT")
    print("=" * 60)
    print(f"Domain: {result.analysis.domain}")
    print(f"Sensitivity Level: {result.analysis.sensitivity_level}")
    print(f"Risk Factors: {result.analysis.risk_factors}")
    print(f"Reasoning: {result.analysis.reasoning}")
    print(f"\nSelected Input Guardrails: {[g.value for g in result.analysis.input_guardrails]}")
    print(f"Selected Output Guardrails: {[g.value for g in result.analysis.output_guardrails]}")

    print("\n" + "=" * 60)
    print("INPUT GUARDRAILS")
    print("=" * 60)
    for guardrail in result.input_guardrails:
        print(f"\n--- {guardrail.name} (priority: {guardrail.priority}) ---")
        print(f"Type: {guardrail.type.value}")
        print(f"Config: {guardrail.config}")

    print("\n" + "=" * 60)
    print("OUTPUT GUARDRAILS")
    print("=" * 60)
    for guardrail in result.output_guardrails:
        print(f"\n--- {guardrail.name} (priority: {guardrail.priority}) ---")
        print(f"Type: {guardrail.type.value}")
        print(f"Config: {guardrail.config}")

    # Cleanup
    llm.unload()
    print("\n" + "=" * 60)
    print("Test completed!")


if __name__ == "__main__":
    test_guardrails_generator()
