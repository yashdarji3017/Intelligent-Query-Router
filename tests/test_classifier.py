import pytest
from pydantic import ValidationError
from app.core.exceptions import ClassificationError, ProviderError, ProviderTimeoutError
from app.schemas.classification import QueryClassification
from app.services.classifier_service import ClassifierService
from tests.conftest import MockClassifierAgent


def test_query_classification_model_valid():
    model = QueryClassification(
        category="technical",
        urgency="critical",
        complexity="medium",
        confidence=0.98,
        target_agent="technical_handler",
        reason="Production database connection failure",
        requires_clarification=False,
    )
    assert model.category == "technical"
    assert model.urgency == "critical"
    assert model.confidence == 0.98
    assert not model.requires_clarification


def test_query_classification_invalid_category():
    with pytest.raises(ValidationError):
        QueryClassification(
            category="unsupported_category",
            urgency="normal",
            complexity="simple",
            confidence=0.9,
            target_agent="handler",
            reason="testing",
        )


def test_query_classification_confidence_bounds():
    with pytest.raises(ValidationError):
        QueryClassification(
            category="general",
            urgency="normal",
            complexity="simple",
            confidence=1.5,
            target_agent="handler",
            reason="testing",
        )

    with pytest.raises(ValidationError):
        QueryClassification(
            category="general",
            urgency="normal",
            complexity="simple",
            confidence=-0.1,
            target_agent="handler",
            reason="testing",
        )


@pytest.mark.asyncio
async def test_mock_classifier_all_categories(mock_classifier: MockClassifierAgent, test_settings):
    service = ClassifierService(classifier_agent=mock_classifier, settings=test_settings)

    result, _ = await service.classify_query("Hello there, how are you?")
    assert result.category == "general"
    assert result.urgency == "normal"
    assert not result.requires_clarification

    result, _ = await service.classify_query("Our production API is down and throwing 500s!")
    assert result.category == "technical"
    assert result.urgency == "critical"
    assert not result.requires_clarification

    result, _ = await service.classify_query("Where can I download my latest invoice for payment?")
    assert result.category == "billing"
    assert not result.requires_clarification

    result, _ = await service.classify_query("I need to reset my account password.")
    assert result.category == "account"
    assert not result.requires_clarification

    result, _ = await service.classify_query("Please architect a multi-step migration strategy.")
    assert result.category == "complex"
    assert result.complexity == "complex"

    result, _ = await service.classify_query("It is not working.")
    assert result.category == "unknown"
    assert result.requires_clarification is True
    assert result.confidence < test_settings.classification_confidence_threshold


@pytest.mark.asyncio
async def test_classifier_service_timeout(test_settings):
    import asyncio

    class HangingClassifier:
        async def classify(self, query: str):
            await asyncio.sleep(10.0)

    test_settings.request_timeout_seconds = 0.05
    test_settings.max_retries = 0
    service = ClassifierService(classifier_agent=HangingClassifier(), settings=test_settings)

    with pytest.raises(ProviderTimeoutError):
        await service.classify_query("Should timeout")


@pytest.mark.asyncio
async def test_classifier_service_provider_error(test_settings):
    class FailingClassifier:
        async def classify(self, query: str):
            raise RuntimeError("Gemini API connection refused")

    test_settings.max_retries = 0
    service = ClassifierService(classifier_agent=FailingClassifier(), settings=test_settings)

    with pytest.raises(ProviderError):
        await service.classify_query("Will fail")
