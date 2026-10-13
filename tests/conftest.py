from typing import AsyncIterator, Optional

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.classifier import set_classifier_agent
from app.api.routes import set_chat_service
from app.core.config import Settings
from app.main import create_app
from app.schemas.classification import QueryClassification
from app.services.chat_service import ChatService
from app.services.classifier_service import ClassifierService
from app.services.router_service import DeterministicRouter


class MockClassifierAgent:
    """Provide a deterministic classifier for automated tests."""

    def __init__(
        self,
        default_classification: Optional[QueryClassification] = None,
    ) -> None:
        """
        Initialize the mock classifier.

        Args:
            default_classification: Optional classification returned when
                the query does not match a predefined test scenario.
        """
        self.default_classification = (
            default_classification
            or QueryClassification(
                category="general",
                urgency="normal",
                complexity="simple",
                confidence=0.95,
                target_agent="general_handler",
                reason="Mock general query greeting",
                requires_clarification=False,
            )
        )
        self.last_query: Optional[str] = None
        self.call_count = 0
        self.simulate_exception: Optional[Exception] = None

    async def classify(self, query: str) -> QueryClassification:
        """
        Return a deterministic classification based on query keywords.

        Args:
            query: User query submitted to the mock classifier.

        Returns:
            QueryClassification: Classification matching a predefined
                scenario or the configured default.

        Raises:
            Exception: Propagates the configured simulated exception.
        """
        self.last_query = query
        self.call_count += 1

        if self.simulate_exception is not None:
            raise self.simulate_exception

        query_lower = query.lower()
        query_words = query_lower.split()

        if any(
            keyword in query_lower
            for keyword in ("invoice", "bill", "payment")
        ):
            return QueryClassification(
                category="billing",
                urgency="normal",
                complexity="simple",
                confidence=0.92,
                target_agent="billing_handler",
                reason="Billing and payment inquiry",
                requires_clarification=False,
            )

        if (
            any(keyword in query_lower for keyword in ("crash", "api"))
            or any(word in query_words for word in ("down", "down!"))
        ):
            return QueryClassification(
                category="technical",
                urgency="critical",
                complexity="medium",
                confidence=0.96,
                target_agent="technical_handler",
                reason="Production incident detected",
                requires_clarification=False,
            )

        if any(
            keyword in query_lower
            for keyword in ("password", "account", "login")
        ):
            return QueryClassification(
                category="account",
                urgency="normal",
                complexity="simple",
                confidence=0.90,
                target_agent="account_handler",
                reason="User account administration",
                requires_clarification=False,
            )

        if any(
            keyword in query_lower
            for keyword in ("architect", "multi-step")
        ):
            return QueryClassification(
                category="complex",
                urgency="high",
                complexity="complex",
                confidence=0.88,
                target_agent="complex_handler",
                reason="Multi-step complex architecture inquiry",
                requires_clarification=False,
            )

        if (
            "not working" in query_lower
            or query_lower.strip() == "help me"
        ):
            return QueryClassification(
                category="unknown",
                urgency="normal",
                complexity="simple",
                confidence=0.40,
                target_agent="fallback_handler",
                reason="Insufficient context provided",
                requires_clarification=True,
            )

        return self.default_classification


@pytest.fixture
def test_settings() -> Settings:
    """
    Provide isolated application settings for tests.

    Returns:
        Settings: Configuration with short timeouts and minimal retry delays.
    """
    return Settings(
        app_name="Test Query Classifier",
        app_env="testing",
        gemini_model="gemini-3.6-flash",
        classification_confidence_threshold=0.70,
        max_concurrent_requests=6,
        request_timeout_seconds=5.0,
        max_retries=1,
        retry_backoff_base_seconds=0.01,
    )


@pytest.fixture
def mock_classifier() -> MockClassifierAgent:
    """
    Create a fresh mock classifier for each test.

    Returns:
        MockClassifierAgent: Deterministic classifier with call tracking.
    """
    return MockClassifierAgent()


@pytest.fixture
def chat_service(
    test_settings: Settings,
    mock_classifier: MockClassifierAgent,
) -> ChatService:
    """
    Create a chat service using test dependencies.

    Registers the service with the API dependency override helper so
    endpoints use the mock classifier instead of an external provider.

    Args:
        test_settings: Isolated application settings.
        mock_classifier: Mock classifier used for query classification.

    Returns:
        ChatService: Configured service instance for testing.
    """
    classifier_service = ClassifierService(
        classifier_agent=mock_classifier,
        settings=test_settings,
    )

    router = DeterministicRouter(settings=test_settings)

    service = ChatService(
        classifier_service=classifier_service,
        router=router,
        settings=test_settings,
    )

    set_chat_service(service)
    return service


@pytest.fixture
async def async_client(
    chat_service: ChatService,
) -> AsyncIterator[AsyncClient]:
    """
    Create an asynchronous HTTP client for API integration tests.

    Uses ASGITransport to invoke the FastAPI application directly without
    starting a network server.

    Args:
        chat_service: Service fixture ensuring test dependencies are set.

    Yields:
        AsyncClient: Client configured for the test application.
    """
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client