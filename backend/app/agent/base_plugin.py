from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field


class PluginError(BaseModel):
    code: str = Field(..., description="Machine-readable error code, e.g. SQL_TIMEOUT, INVALID_SCHEMA")
    message: str = Field(..., description="Human-readable failure description")
    retryable: bool = Field(default=True, description="Whether agent should attempt parameter correction and retry")
    details: dict[str, Any] | None = None


class PluginOutput(BaseModel):
    success: bool = True
    output_type: str = "data"  # 'data', 'chart', 'excel', 'powerpoint', 'file'
    result: Any = None
    artifact_id: str | None = None
    artifact_url: str | None = None
    metadata: dict[str, Any] = {}
    error: PluginError | None = None


class PluginBase(ABC):
    """
    Richer Plugin Interface Contract for Agent Plugins.
    Declares capabilities, input/output schemas, and structured error reporting.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier name for the plugin."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the plugin does for LLM tool selection."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> type[BaseModel]:
        """Pydantic model class specifying the required inputs for the plugin."""
        pass

    @property
    def can_consume(self) -> list[str]:
        """List of output types this plugin can consume from previous step (e.g. ['data'])."""
        return ["data"]

    @property
    def can_produce(self) -> list[str]:
        """List of output types this plugin produces (e.g. ['chart', 'file'])."""
        return ["data"]

    def validate_params(self, params: dict[str, Any]) -> PluginError | None:
        """Validates inputs against input_schema before execution."""
        try:
            self.input_schema(**params)
            return None
        except Exception as e:
            return PluginError(
                code="INVALID_ARGUMENTS",
                message=f"Validation failed for {self.name}: {str(e)}",
                retryable=True
            )

    @abstractmethod
    async def execute(
        self,
        params: dict[str, Any],
        context: dict[str, Any],
        progress_callback: Callable[[str], None] | None = None
    ) -> PluginOutput:
        """
        Executes the plugin logic asynchronously.
        """
        pass
