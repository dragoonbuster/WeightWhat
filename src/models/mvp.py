"""
MVP Models for SizeComparator - Simple request/response for demo
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class MVPComparisonRequest(BaseModel):
    """Simple MVP request - just weight input"""
    weight_input: str = Field(
        ..., 
        description="Weight input like '5 kg', '10 pounds', '100 grams'",
        example="5.5 kilograms"
    )
    provider: Optional[Literal["openai", "anthropic", "xai", "auto"]] = "auto"
    style: Optional[Literal["default", "creative", "technical"]] = "default"

class MVPComparisonResponse(BaseModel):
    """Simple MVP response - just the comparison text"""
    comparison_text: str = Field(
        ...,
        description="AI-generated comparison text",
        example="5.5 kilograms is about the weight of a bowling ball or a house cat."
    )
    weight_processed: str = Field(
        ...,
        description="Processed weight in standard format", 
        example="5.50 kg"
    )
    provider_used: str = Field(
        ...,
        description="AI provider that generated the response",
        example="openai"
    )
    response_time_ms: int = Field(
        ...,
        description="Response time in milliseconds",
        example=1250
    )
    cached: bool = Field(
        default=False,
        description="Whether this was served from cache"
    )
    request_id: str = Field(
        ...,
        description="Unique request identifier for debugging"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )

class MVPErrorResponse(BaseModel):
    """Simple error response"""
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code for debugging")
    request_id: str = Field(..., description="Request ID")
    suggestions: Optional[list[str]] = Field(
        default=None,
        description="Suggestions to fix the error"
    )