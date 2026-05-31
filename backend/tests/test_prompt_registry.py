from app.prompts import get_prompt, prompt_hash


def test_prompt_registry_returns_versioned_prompt_with_stable_hash() -> None:
    prompt = get_prompt("compliance_extract", "1.1.0")
    messages = prompt.render(chunks_json='[{"chunk_index":1,"text":"投标人须具备营业执照。"}]')
    repeated = prompt.render(chunks_json='[{"chunk_index":1,"text":"投标人须具备营业执照。"}]')

    assert prompt.prompt_version == "compliance_extract@1.1.0"
    assert prompt.output_schema["required"] == ["items"]
    assert "输出 JSON" in messages[0]["content"]
    assert "source_chunk_index" in messages[1]["content"]
    assert prompt_hash(messages) == prompt_hash(repeated)


def test_prompt_registry_contains_risk_assessment_placeholder() -> None:
    prompt = get_prompt("requirement_risk_assess@1.1.0")
    messages = prompt.render(requirement_json='{"requirement_text":"必须按期递交投标文件"}')

    assert prompt.prompt_version == "requirement_risk_assess@1.1.0"
    assert "只做风险初判" in prompt.safety_boundary
    assert messages[0]["role"] == "system"


def test_prompt_registry_contains_sectioned_extraction_prompts() -> None:
    section_plan = get_prompt("document_section_plan", "1.1.0")
    section_extract = get_prompt("compliance_extract_by_section@1.1.0")
    coverage_review = get_prompt("section_coverage_review", "1.1.0")

    assert section_plan.output_schema["required"] == ["sections"]
    assert "start_page" in section_plan.render(pages_json="[]")[1]["content"]
    assert section_extract.output_schema["required"] == ["items"]
    assert "source_quote" in section_extract.render(section_json="{}", chunks_json="[]")[1]["content"]
    assert coverage_review.output_schema["required"] == ["status", "issues"]
    assert "漏抽" in coverage_review.render(section_json="{}", chunks_json="[]", items_json="[]")[1]["content"]
