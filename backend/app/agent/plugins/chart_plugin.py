import logging
from typing import Any

import matplotlib
from pydantic import BaseModel, Field, field_validator

from app.agent.base_plugin import PluginBase, PluginError, PluginOutput
from app.agent.registry import register_plugin
from app.services.artifact_service import ArtifactService

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

logger = logging.getLogger(__name__)

MAX_CHART_POINTS = 5000


class ChartPluginInput(BaseModel):
    chart_type: str = Field(..., description="Type of chart: 'bar', 'line', 'pie', or 'distribution'")
    title: str = Field(..., description="Title of the chart")
    x_key: str = Field(..., description="Column key for the X axis")
    y_key: str = Field(..., description="Column key for the Y axis")
    data: list[dict[str, Any]] | str | None = Field(None, description="Optional dataset rows. If omitted or using previous query result, omit or leave null.")

    @field_validator("data", mode="before")
    @classmethod
    def sanitize_data(cls, v: Any) -> list[dict[str, Any]] | None:
        if isinstance(v, str) or not isinstance(v, list):
            return None
        return v


@register_plugin
class ChartPlugin(PluginBase):
    @property
    def name(self) -> str:
        return "chart"

    @property
    def description(self) -> str:
        return "Generates a visualization chart specification and creates a rendered PNG artifact."

    @property
    def input_schema(self) -> type[BaseModel]:
        return ChartPluginInput

    @property
    def can_consume(self) -> list[str]:
        return ["data"]

    @property
    def can_produce(self) -> list[str]:
        return ["chart"]

    async def execute(
        self,
        params: dict[str, Any],
        context: dict[str, Any],
        progress_callback: Any | None = None
    ) -> PluginOutput:
        val_err = self.validate_params(params)
        if val_err:
            return PluginOutput(success=False, output_type="chart", error=val_err)

        chart_type = params.get("chart_type", "bar").lower()
        title = params.get("title", "Analytics Chart")
        x_key = params.get("x_key")
        y_key = params.get("y_key")
        dataset = params.get("data")
        if not isinstance(dataset, list):
            dataset = context.get("last_query_result") or []

        if not dataset:
            return PluginOutput(
                success=False,
                output_type="chart",
                error=PluginError(code="EMPTY_DATASET", message="No dataset provided from previous query step.", retryable=True)
            )

        # Enforce max chart points bound
        if len(dataset) > MAX_CHART_POINTS:
            dataset = dataset[:MAX_CHART_POINTS]

        if progress_callback:
            await progress_callback(f"Rendering {chart_type} chart: {title}...")

        x_vals = [str(row.get(x_key, "")) for row in dataset[:30]]
        try:
            y_vals = [float(row.get(y_key, 0) or 0) for row in dataset[:30]]
        except Exception:
            y_vals = [0] * len(x_vals)

        fig, ax = plt.subplots(figsize=(10, 5), dpi=100)
        fig.patch.set_facecolor('#0f172a')
        ax.set_facecolor('#1e293b')
        ax.tick_params(colors='white', labelsize=10)
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')

        if chart_type == "line":
            ax.plot(x_vals, y_vals, marker='o', color='#38bdf8', linewidth=2.5)
        elif chart_type == "pie":
            ax.pie(y_vals[:10], labels=x_vals[:10], autopct='%1.1f%%', textprops={'color': 'white'})
        else:
            ax.bar(x_vals, y_vals, color='#818cf8', edgecolor='#6366f1')

        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
        ax.set_xlabel(x_key, fontsize=11, labelpad=10)
        ax.set_ylabel(y_key, fontsize=11, labelpad=10)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        artifact_id, filepath = ArtifactService.create_artifact_file(".png")
        fig.savefig(filepath, format="png", bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)

        chart_spec = {
            "chart_type": chart_type,
            "title": title,
            "x_key": x_key,
            "y_key": y_key,
            "data": dataset
        }

        return PluginOutput(
            success=True,
            output_type="chart",
            result=chart_spec,
            artifact_id=artifact_id,
            artifact_url=f"/api/artifacts/{artifact_id}",
            metadata={"chart_type": chart_type, "title": title}
        )
