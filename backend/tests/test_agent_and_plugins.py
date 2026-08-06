
import pytest
from app.agent.plugins.chart_plugin import MAX_CHART_POINTS, ChartPlugin
from app.agent.plugins.excel_plugin import ExcelPlugin
from app.agent.plugins.powerpoint_plugin import PowerPointPlugin
from app.agent.registry import PluginRegistry


def test_registry_discovery():
    plugins = PluginRegistry.get_all_plugins()
    assert "query" in plugins
    assert "chart" in plugins
    assert "excel" in plugins
    assert "powerpoint" in plugins


def test_system_prompt_generation():
    desc = PluginRegistry.build_system_prompt_tools_description()
    assert "Tool: `query`" in desc
    assert "Consumes:" in desc
    assert "Produces:" in desc


@pytest.mark.asyncio
async def test_chart_plugin_limits():
    plugin = ChartPlugin()
    large_dataset = [{"x": i, "y": i * 10} for i in range(MAX_CHART_POINTS + 500)]
    output = await plugin.execute(
        {"chart_type": "bar", "title": "Test Bound", "x_key": "x", "y_key": "y", "data": large_dataset},
        context={}
    )
    assert output.success
    assert output.artifact_id is not None
    assert len(output.result["data"]) == MAX_CHART_POINTS


@pytest.mark.asyncio
async def test_excel_plugin_limits():
    plugin = ExcelPlugin()
    dataset = [{"col1": f"val_{i}", "col2": i} for i in range(100)]
    output = await plugin.execute(
        {"title": "Excel Bound Test", "data": dataset},
        context={}
    )
    assert output.success
    assert output.artifact_id is not None
    assert output.output_type == "excel"


@pytest.mark.asyncio
async def test_powerpoint_plugin_deck():
    plugin = PowerPointPlugin()
    dataset = [{"metric": "Volume", "value": 1500}]
    output = await plugin.execute(
        {"title": "Deck Bound Test", "data": dataset},
        context={}
    )
    assert output.success
    assert output.artifact_id is not None
    assert output.output_type == "powerpoint"


@pytest.mark.asyncio
async def test_chart_plugin_string_data_fallback():
    plugin = ChartPlugin()
    context_data = [{"server_name": "Server A", "member_count": 100}]
    output = await plugin.execute(
        {
            "chart_type": "bar",
            "title": "String Data Test",
            "x_key": "server_name",
            "y_key": "member_count",
            "data": "query_result"
        },
        context={"last_query_result": context_data}
    )
    assert output.success
    assert output.result["data"] == context_data


@pytest.mark.asyncio
async def test_excel_plugin_string_data_fallback():
    plugin = ExcelPlugin()
    context_data = [{"col1": "A", "col2": 1}]
    output = await plugin.execute(
        {
            "title": "Excel String Data Test",
            "data": "last_query_result"
        },
        context={"last_query_result": context_data}
    )
    assert output.success
    assert output.result["rows_count"] == 1

