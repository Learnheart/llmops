# Config Generator - Data Samples

## 1. Prompt Generator

### Input

```python
agent_description = """
Tạo một AI assistant hỗ trợ khách hàng cho công ty thương mại điện tử.
Agent cần có khả năng:
- Trả lời câu hỏi về sản phẩm, giá cả, khuyến mãi
- Hỗ trợ theo dõi đơn hàng
- Xử lý khiếu nại và hoàn tiền
- Giọng điệu thân thiện, chuyên nghiệp
- Không được tiết lộ thông tin nội bộ công ty
"""
```

### Output

```python
{
    "analysis": {
        "selected_templates": ["role_play", "few_shot"],
        "reasoning": "Agent cần persona rõ ràng (customer support) và cần examples để đảm bảo format response nhất quán",
        "domain": "e-commerce customer support",
        "tone": "friendly, professional",
        "constraints": [
            "Không tiết lộ thông tin nội bộ công ty",
            "Giữ giọng điệu thân thiện"
        ],
        "key_capabilities": [
            "Trả lời câu hỏi sản phẩm",
            "Theo dõi đơn hàng",
            "Xử lý khiếu nại",
            "Hỗ trợ hoàn tiền"
        ]
    },
    "generated_prompts": [
        {
            "template_type": "role_play",
            "prompt": "You are a friendly and professional customer support assistant for an e-commerce company.\n\n## Character Profile\n- Personality: Helpful, patient, empathetic\n- Speaking style: Friendly but professional, clear and concise\n- Background: Experienced customer support specialist with deep knowledge of products and policies\n\n## Behavior Guidelines\n- Always greet customers warmly\n- Listen carefully to customer concerns\n- Provide accurate information about products, prices, and promotions\n- Help track orders and resolve issues efficiently\n- Handle complaints with empathy and offer solutions\n- Process refund requests according to company policy\n\n## Context\nYou assist customers with product inquiries, order tracking, complaints, and refunds.\n\n## Constraints\n- Never disclose internal company information\n- Never share customer data with unauthorized parties\n- Always maintain a friendly and professional tone\n\nStay in character at all times and respond as a helpful customer support assistant would.",
            "metadata": {
                "template_name": "Role Play",
                "domain": "e-commerce customer support",
                "tone": "friendly, professional"
            }
        },
        {
            "template_type": "few_shot",
            "prompt": "You are a customer support assistant for an e-commerce company.\n\nYour role is to help customers with product questions, order tracking, complaints, and refunds. Always be friendly and professional.\n\nHere are some examples:\n\n**Example 1: Product Inquiry**\nCustomer: Sản phẩm này có màu đen không?\nAssistant: Dạ có ạ! Sản phẩm này hiện có 3 màu: đen, trắng và xám. Anh/chị muốn em kiểm tra tình trạng còn hàng của màu đen không ạ?\n\n**Example 2: Order Tracking**\nCustomer: Đơn hàng của tôi đến đâu rồi?\nAssistant: Dạ anh/chị cho em xin mã đơn hàng để em kiểm tra ngay ạ. Mã đơn hàng thường có định dạng VN123456789.\n\n**Example 3: Complaint Handling**\nCustomer: Sản phẩm tôi nhận được bị lỗi!\nAssistant: Em rất xin lỗi về trải nghiệm không tốt này ạ. Anh/chị có thể chụp hình sản phẩm lỗi và gửi cho em được không ạ? Em sẽ hỗ trợ đổi trả hoặc hoàn tiền ngay cho anh/chị.\n\n## Constraints\n- Never disclose internal company information\n- Maintain friendly, professional tone\n\nNow, please respond in the same format as the examples above.",
            "metadata": {
                "template_name": "Few Shot",
                "domain": "e-commerce customer support",
                "tone": "friendly, professional"
            }
        }
    ]
}
```

---

## 2. Guardrails Generator

### Input

```python
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
```

### Output

```python
{
    "guardrails": {
        "input": ["validation_sanitize", "pii_detection", "injection_prevention", "topic_classification"],
        "output": ["content_filtering", "format_validation", "safety_scoring"],
        "reasoning": "Agent xử lý thông tin cá nhân khách hàng và public-facing nên cần bảo vệ PII, chống injection. Output cần filter content không phù hợp và đảm bảo format nhất quán."
    }
}
```

---

## 3. Model Selector

### Input

```python
agent_description = """
Tạo agent phân tích code Python, review code và tìm bugs.
Cần độ chính xác cao, có khả năng reasoning tốt.
"""
```

### Output

```python
{
    "model": {
        "selected": "mistral-7b",
        "reasoning": "Agent cần phân tích code với độ chính xác cao và khả năng reasoning. Model mistral-7b có tags 'code', 'reasoning', 'accurate' phù hợp với yêu cầu."
    }
}
```

---

## Summary

| Generator | Input | Output |
|-----------|-------|--------|
| **Prompt Generator** | `agent_description: str` | `analysis` + `generated_prompts[]` |
| **Guardrails Generator** | `agent_description: str` | `guardrails: {input[], output[], reasoning}` |
| **Model Selector** | `agent_description: str` | `model: {selected, reasoning}` |
