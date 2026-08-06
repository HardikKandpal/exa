from app.agent.registry import PluginRegistry


def test_plugin_discovery():
    plugins = PluginRegistry.discover_plugins()
    assert "query" in plugins
    assert "chart" in plugins
    assert "excel" in plugins
    assert "powerpoint" in plugins


def test_plugin_descriptions_generation():
    desc = PluginRegistry.build_system_prompt_tools_description()
    assert "Tool: `query`" in desc
    assert "Tool: `chart`" in desc
    assert "Tool: `excel`" in desc
    assert "Tool: `powerpoint`" in desc
