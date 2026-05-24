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
