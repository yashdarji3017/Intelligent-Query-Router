from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """
    Validate incoming chat requests.

    Contains the user query and optional identifiers used for request
    tracing and session correlation.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User inquiry or statement to process.",
    )

    user_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Optional user identifier for request tracing.",
    )

    session_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Optional session identifier for request tracing.",
    )


class ClassifyRequest(BaseModel):
    """
    Validate standalone query classification requests.

    Contains the query to classify and optional identifiers for tracing
    the classification request.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    query: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User inquiry or statement to classify.",
    )

    user_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Optional user identifier for request tracing.",
    )

    session_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Optional session identifier for request tracing.",
    )