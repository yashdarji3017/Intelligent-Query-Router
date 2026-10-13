import pytest
from app.schemas.classification import QueryClassification
from app.services.router_service import DeterministicRouter


def test_deterministic_router_categories(test_settings):
    router = DeterministicRouter(settings=test_settings)

    test_cases = [
        ("general", "general_handler"),
        ("technical", "technical_handler"),
        ("account", "account_handler"),
        ("billing", "billing_handler"),
        ("complex", "complex_handler"),
        ("unknown", "fallback_handler"),
    ]

    for category, expected_handler in test_cases:
        classification = QueryClassification(
            category=category,
            urgency="normal",
            complexity="simple",
            confidence=0.90,
            target_agent="suggested_handler",
            reason="standard test",
            requires_clarification=False,
        )
        resolved = router.resolve_target(classification)
        assert resolved == expected_handler, f"Category {category} should resolve to {expected_handler}"


def test_routing_low_confidence_fallback(test_settings):
    test_settings.classification_confidence_threshold = 0.75
    router = DeterministicRouter(settings=test_settings)

    classification = QueryClassification(
        category="technical",
        urgency="high",
        complexity="medium",
        confidence=0.70,
        target_agent="technical_handler",
        reason="Uncertain classification",
        requires_clarification=False,
    )
    resolved = router.resolve_target(classification)
    assert resolved == "fallback_handler"


def test_routing_requires_clarification_fallback(test_settings):
    router = DeterministicRouter(settings=test_settings)

    classification = QueryClassification(
        category="technical",
        urgency="normal",
        complexity="simple",
        confidence=0.95,
        target_agent="technical_handler",
        reason="Ambiguous input",
        requires_clarification=True,
    )
    resolved = router.resolve_target(classification)
    assert resolved == "fallback_handler"


def test_routing_prevents_llm_handler_tampering(test_settings):
    router = DeterministicRouter(settings=test_settings)

    classification = QueryClassification(
        category="general",
        urgency="normal",
        complexity="simple",
        confidence=0.95,
        target_agent="unauthorized_system_shell",
        reason="Attempted override",
        requires_clarification=False,
    )
    resolved = router.resolve_target(classification)
    assert resolved == "general_handler"
    assert resolved != "unauthorized_system_shell"


def test_urgency_independent_from_category(test_settings):
    router = DeterministicRouter(settings=test_settings)

    critical_billing = QueryClassification(
        category="billing",
        urgency="critical",
        complexity="complex",
        confidence=0.95,
        target_agent="billing_handler",
        reason="Payment processor blocking enterprise operations",
        requires_clarification=False,
    )
    assert router.resolve_target(critical_billing) == "billing_handler"


@pytest.mark.asyncio
async def test_router_dispatch_execution(test_settings):
    router = DeterministicRouter(settings=test_settings)
    classification = QueryClassification(
        category="general",
        urgency="normal",
        complexity="simple",
        confidence=0.95,
        target_agent="general_handler",
        reason="Greeting",
        requires_clarification=False,
    )
    answer = await router.dispatch("general_handler", "Hello!", classification)
    assert "Hello" in answer or "assistant" in answer
