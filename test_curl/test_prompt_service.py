"""
Test script for Prompt Service API
Run: python test_prompt_service.py
"""

import requests
import json
from typing import Optional

BASE_URL = "http://localhost:8080"
USER_ID = "test-user-001"


def print_response(name: str, response: requests.Response):
    """Pretty print response."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(f"Response:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"Response: {response.text}")
    print()


def test_health():
    """Test health endpoints."""
    # Basic health
    r = requests.get(f"{BASE_URL}/health")
    print_response("Health Check", r)

    # Detailed health
    r = requests.get(f"{BASE_URL}/health/detailed")
    print_response("Detailed Health", r)

    return r.status_code == 200


def test_list_templates():
    """Test listing templates."""
    r = requests.get(f"{BASE_URL}/api/v1/templates")
    print_response("List Templates", r)
    return r.status_code == 200


def test_get_template_keys():
    """Test getting template keys."""
    r = requests.get(f"{BASE_URL}/api/v1/templates/keys")
    print_response("Get Template Keys", r)
    return r.status_code == 200


def test_get_template_detail(key: str = "concise"):
    """Test getting template detail."""
    r = requests.get(f"{BASE_URL}/api/v1/templates/{key}")
    print_response(f"Get Template Detail ({key})", r)
    return r.status_code == 200


def test_preview_template(key: str = "concise"):
    """Test previewing a template."""
    payload = {
        "agent_instruction": "Bạn là một trợ lý AI giúp người dùng viết code Python"
    }
    r = requests.post(f"{BASE_URL}/api/v1/templates/{key}/preview", json=payload)
    print_response(f"Preview Template ({key})", r)
    return r.status_code == 200


def test_compose_prompt(save: bool = True) -> Optional[str]:
    """Test composing a prompt."""
    payload = {
        "user_id": USER_ID,
        "template_key": "detailed",
        "agent_instruction": "Bạn là một chuyên gia phân tích dữ liệu, giúp người dùng xử lý và visualize data bằng Python và Pandas",
        "save": save,
        "metadata": {
            "project": "data-analysis",
            "version": "1.0"
        }
    }
    r = requests.post(f"{BASE_URL}/api/v1/prompts/compose", json=payload)
    print_response("Compose Prompt", r)

    if r.status_code == 200:
        return r.json().get("generation_id")
    return None


def test_batch_compose():
    """Test batch composing prompts."""
    payload = [
        {
            "user_id": USER_ID,
            "template_key": "concise",
            "agent_instruction": "Trợ lý viết email chuyên nghiệp",
            "save": False
        },
        {
            "user_id": USER_ID,
            "template_key": "detailed",
            "agent_instruction": "Trợ lý viết email chuyên nghiệp",
            "save": False
        },
        {
            "user_id": USER_ID,
            "template_key": "step_by_step",
            "agent_instruction": "Trợ lý viết email chuyên nghiệp",
            "save": False
        }
    ]
    r = requests.post(f"{BASE_URL}/api/v1/prompts/batch-compose", json=payload)
    print_response("Batch Compose Prompts", r)
    return r.status_code == 200


def test_compare_templates():
    """Test comparing templates."""
    params = {
        "agent_instruction": "Trợ lý giúp debug code JavaScript",
        "template_keys": ["concise", "detailed", "few_shot"],
        "user_id": USER_ID,
        "save": False
    }
    r = requests.post(f"{BASE_URL}/api/v1/prompts/compare", params=params)
    print_response("Compare Templates", r)
    return r.status_code == 200


def test_list_generations():
    """Test listing user's generations."""
    params = {
        "user_id": USER_ID,
        "page": 1,
        "page_size": 10
    }
    r = requests.get(f"{BASE_URL}/api/v1/generations", params=params)
    print_response("List Generations", r)
    return r.status_code == 200


def test_get_generation(generation_id: str):
    """Test getting a specific generation."""
    r = requests.get(f"{BASE_URL}/api/v1/generations/{generation_id}")
    print_response(f"Get Generation ({generation_id})", r)
    return r.status_code == 200


def test_create_variant(generation_id: str) -> Optional[str]:
    """Test creating a variant from a generation."""
    payload = {
        "user_id": USER_ID,
        "generation_id": generation_id,
        "name": "Production Variant v1",
        "prompt_content": None,  # Use original from generation
        "metadata": {
            "environment": "production",
            "approved_by": "admin"
        }
    }
    r = requests.post(f"{BASE_URL}/api/v1/variants", json=payload)
    print_response("Create Variant", r)

    if r.status_code == 200:
        return r.json().get("id")
    return None


def test_list_variants():
    """Test listing user's variants."""
    params = {
        "user_id": USER_ID,
        "page": 1,
        "page_size": 10
    }
    r = requests.get(f"{BASE_URL}/api/v1/variants", params=params)
    print_response("List Variants", r)
    return r.status_code == 200


def test_get_variant(variant_id: str):
    """Test getting a specific variant."""
    r = requests.get(f"{BASE_URL}/api/v1/variants/{variant_id}")
    print_response(f"Get Variant ({variant_id})", r)
    return r.status_code == 200


def test_update_variant(variant_id: str):
    """Test updating a variant (creates new version)."""
    payload = {
        "user_id": USER_ID,
        "prompt_content": "Bạn là một chuyên gia phân tích dữ liệu cao cấp. Nhiệm vụ của bạn là giúp người dùng xử lý, phân tích và visualize data một cách chuyên nghiệp sử dụng Python, Pandas và Matplotlib.",
        "change_summary": "Cập nhật nội dung prompt chi tiết hơn"
    }
    r = requests.put(f"{BASE_URL}/api/v1/variants/{variant_id}", json=payload)
    print_response(f"Update Variant ({variant_id})", r)
    return r.status_code == 200


def test_activate_variant(variant_id: str, is_active: bool = True):
    """Test activating/deactivating a variant."""
    payload = {
        "user_id": USER_ID,
        "is_active": is_active
    }
    r = requests.post(f"{BASE_URL}/api/v1/variants/{variant_id}/activate", json=payload)
    print_response(f"Activate Variant ({variant_id}, active={is_active})", r)
    return r.status_code == 200


def test_change_variant_status(variant_id: str, status: str = "approved"):
    """Test changing variant status."""
    payload = {
        "user_id": USER_ID,
        "status": status
    }
    r = requests.post(f"{BASE_URL}/api/v1/variants/{variant_id}/status", json=payload)
    print_response(f"Change Variant Status ({variant_id}, status={status})", r)
    return r.status_code == 200


def test_get_variant_history(variant_id: str):
    """Test getting variant history."""
    r = requests.get(f"{BASE_URL}/api/v1/variants/{variant_id}/history")
    print_response(f"Get Variant History ({variant_id})", r)
    return r.status_code == 200


def test_get_generation_variants(generation_id: str):
    """Test getting variants of a generation."""
    r = requests.get(f"{BASE_URL}/api/v1/generations/{generation_id}/variants")
    print_response(f"Get Generation Variants ({generation_id})", r)
    return r.status_code == 200


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("PROMPT SERVICE API TEST")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"User ID: {USER_ID}")

    # 1. Health checks
    print("\n\n>>> HEALTH CHECKS <<<")
    if not test_health():
        print("❌ Service is not healthy. Make sure prompt-service is running.")
        return

    # 2. Template operations
    print("\n\n>>> TEMPLATE OPERATIONS <<<")
    test_list_templates()
    test_get_template_keys()
    test_get_template_detail("concise")
    test_get_template_detail("detailed")
    test_preview_template("step_by_step")

    # 3. Prompt composition
    print("\n\n>>> PROMPT COMPOSITION <<<")
    generation_id = test_compose_prompt(save=True)
    test_batch_compose()
    test_compare_templates()

    # 4. Generation operations
    print("\n\n>>> GENERATION OPERATIONS <<<")
    test_list_generations()
    if generation_id:
        test_get_generation(generation_id)

    # 5. Variant operations
    print("\n\n>>> VARIANT OPERATIONS <<<")
    variant_id = None
    if generation_id:
        variant_id = test_create_variant(generation_id)
        test_get_generation_variants(generation_id)

    test_list_variants()

    if variant_id:
        test_get_variant(variant_id)
        test_update_variant(variant_id)
        test_activate_variant(variant_id, is_active=True)
        test_change_variant_status(variant_id, status="approved")
        test_get_variant_history(variant_id)

    print("\n" + "="*60)
    print("TEST COMPLETED!")
    print("="*60)


def run_quick_test():
    """Run quick test - just health and basic operations."""
    print("\n>>> QUICK TEST <<<")

    if not test_health():
        print("❌ Service is not healthy!")
        return False

    test_list_templates()
    test_compose_prompt(save=False)

    print("\n✅ Quick test passed!")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        run_quick_test()
    else:
        run_all_tests()
