import logging
from typing import Any

from app.agent.base_plugin import PluginBase, PluginError, PluginOutput
from app.agent.registry import register_plugin
from app.db.database import AsyncSessionReadonly
from app.services.sql_safety import SQLValidationError, validate_and_sanitize_sql
from pydantic import BaseModel, Field
from sqlalchemy import text

logger = logging.getLogger(__name__)


class QueryPluginInput(BaseModel):
    sql: str = Field(..., description="PostgreSQL SELECT query to execute against discord_analytics schema.")
    explanation: str | None = Field(None, description="Brief rationale for the generated SQL query.")


@register_plugin
class QueryPlugin(PluginBase):
    @property
    def name(self) -> str:
        return "query"

    @property
    def description(self) -> str:
        return "Executes a validated read-only PostgreSQL SQL query against the Discord analytics dataset and returns structured rows."

    @property
    def input_schema(self) -> type[BaseModel]:
        return QueryPluginInput

    @property
    def can_consume(self) -> list[str]:
        return []

    @property
    def can_produce(self) -> list[str]:
        return ["data"]

    async def execute(
        self,
        params: dict[str, Any],
        context: dict[str, Any],
        progress_callback: Any | None = None
    ) -> PluginOutput:
        val_err = self.validate_params(params)
        if val_err:
            return PluginOutput(success=False, output_type="data", error=val_err)

        sql = params.get("sql", "").strip()
        explanation = params.get("explanation", "")

        if progress_callback:
            await progress_callback("Validating SQL query safety...")

        try:
            sanitized_sql = validate_and_sanitize_sql(sql)
        except SQLValidationError as e:
            return PluginOutput(
                success=False,
                output_type="data",
                error=PluginError(code="SQL_VALIDATION_ERROR", message=str(e), retryable=True),
                metadata={"original_sql": sql}
            )

        if progress_callback:
            await progress_callback("Executing SQL query against read-only pool...")

        try:
            async with AsyncSessionReadonly() as session:
                result = await session.execute(text(sanitized_sql))
                raw_rows = result.mappings().all()
                rows = []
                for r in raw_rows:
                    row_dict = {}
                    for k, v in dict(r).items():
                        if hasattr(v, "isoformat"):
                            row_dict[k] = v.isoformat()
                        else:
                            row_dict[k] = v
                    rows.append(row_dict)

            return PluginOutput(
                success=True,
                output_type="data",
                result=rows,
                metadata={"sql": sanitized_sql, "row_count": len(rows), "explanation": explanation}
            )
        except Exception as e:
            logger.error(f"SQL Execution Error: {e}")
            return PluginOutput(
                success=False,
                output_type="data",
                error=PluginError(code="DATABASE_QUERY_ERROR", message=str(e), retryable=True),
                metadata={"sql": sanitized_sql}
            )
