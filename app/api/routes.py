from fastapi import APIRouter, Depends
from app.core.config import Settings, get_settings
from app.core.logger import get_logger
from app.schemas.request import ChatRequest, ClassifyRequest
from app.schemas.response import ChatResponse, ClassificationResponse, HealthResponse
from app.services.chat_service import ChatService

logger = get_logger(__name__)
router = APIRouter()

_chat_service_instance = None


def get_chat_service(settings: Settings = Depends(get_settings)) -> ChatService:
    global _chat_service_instance
    if _chat_service_instance is None:
        _chat_service_instance = ChatService(settings=settings)
    return _chat_service_instance


def set_chat_service(service: ChatService) -> None:
    global _chat_service_instance
    _chat_service_instance = service


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health check",
    description="Returns service status and operational metadata without exposing secrets or credentials.",
)
async def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version="0.1.0",
        environment=settings.app_env,
        model=settings.gemini_model,
    )


@router.post(
    "/classify",
    response_model=ClassificationResponse,
    summary="Standalone query classification",
    description="Classifies a user query without dispatching to a handler. Useful for testing classification.",
)
async def classify_query(
    request: ClassifyRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ClassificationResponse:
    return await chat_service.process_classification(
        query=request.query,
        user_id=request.user_id,
        session_id=request.session_id,
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="End-to-end chat processing with classification and routing",
    description="Validates request, classifies query, resolves handler, executes handler, and returns answer.",
)
async def chat_endpoint(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    return await chat_service.process_chat(
        query=request.query,
        user_id=request.user_id,
        session_id=request.session_id,
    )