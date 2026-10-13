from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Category(str, Enum):
    """Define supported query classification categories."""

    GENERAL = "general"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    BILLING = "billing"
    COMPLEX = "complex"
    UNKNOWN = "unknown"


class Urgency(str, Enum):
    """Define supported query urgency levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Complexity(str, Enum):
    """Define supported query complexity levels."""

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


CategoryType = Literal[
    "general",
    "technical",
    "account",
    "billing",
    "complex",
    "unknown",
]

UrgencyType = Literal[
    "low",
    "normal",
    "high",
    "critical",
]

ComplexityType = Literal[
    "simple",
    "medium",
    "complex",
]


class QueryClassification(BaseModel):
    """
    Represent the structured classification of a user query.

    Captures the query category, urgency, complexity, confidence, suggested
    handler, classification rationale, and whether additional clarification
    is required before processing.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    category: CategoryType = Field(
        ...,
        description=(
            "Query category: general, technical, account, billing, "
            "complex, or unknown."
        ),
    )

    urgency: UrgencyType = Field(
        ...,
        description=(
            "Urgency level independent of category: low, normal, "
            "high, or critical."
        ),
    )

    complexity: ComplexityType = Field(
        ...,
        description="Query complexity: simple, medium, or complex.",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Classification confidence score between 0.0 and 1.0."
        ),
    )

    target_agent: str = Field(
        ...,
        min_length=1,
        description=(
            "Suggested handler or agent name responsible for processing "
            "the query."
        ),
    )

    reason: str = Field(
        ...,
        min_length=1,
        description=(
            "Brief explanation supporting the classification decision."
        ),
    )

    requires_clarification: bool = Field(
        default=False,
        description=(
            "Whether the query is ambiguous or underspecified and requires "
            "additional information from the user."
        ),
    )