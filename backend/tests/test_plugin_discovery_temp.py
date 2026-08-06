import os

from app.agent.registry import PluginRegistry


def test_dynamic_temp_plugin_discovery():
    """
    Integration test proving true automatic plugin discovery:
    Creates a temporary plugin file, triggers discovery, verifies registration, and cleans up.
    """
    plugins_dir = os.path.join(os.path.dirname(__file__), "..", "app", "agent", "plugins")
    temp_plugin_path = os.path.join(plugins_dir, "temp_dummy_plugin.py")

    plugin_code = """
from typing import Any, Dict, Optional, Type, List
from pydantic import BaseModel, Field
from app.agent.base_plugin import PluginBase, PluginOutput
from app.agent.registry import register_plugin

class TempDummyInput(BaseModel):
    test_arg: str = Field(..., description="Test parameter")

@register_plugin
class TempDummyPlugin(PluginBase):
    @property
    def name(self) -> str:
        return "temp_dummy"

    @property
    def description(self) -> str:
        return "Temporary dummy plugin for zero-touch discovery verification."

    @property
    def input_schema(self) -> Type[BaseModel]:
        return TempDummyInput

    @property
    def can_consume(self) -> List[str]:
        return ["data"]

    @property
    def can_produce(self) -> List[str]:
        return ["data"]

    async def execute(self, params: Dict[str, Any], context: Dict[str, Any], progress_callback=None) -> PluginOutput:
        return PluginOutput(success=True, result="Dummy Success")
"""

    try:
        # 1. Create temporary plugin file
        with open(temp_plugin_path, "w", encoding="utf-8") as f:
            f.write(plugin_code)

        # 2. Trigger dynamic discovery with force_reload=True
        discovered = PluginRegistry.discover_plugins(force_reload=True)

        # 3. Assert plugin is automatically discovered without editing any core file
        assert "temp_dummy" in discovered
        plugin_instance = PluginRegistry.get_plugin("temp_dummy")
        assert plugin_instance is not None
        assert plugin_instance.description == "Temporary dummy plugin for zero-touch discovery verification."

        # 4. Verify system prompt tool description includes new plugin
        system_desc = PluginRegistry.build_system_prompt_tools_description()
        assert "Tool: `temp_dummy`" in system_desc

    finally:
        # Clean up temporary file
        if os.path.exists(temp_plugin_path):
            os.remove(temp_plugin_path)
            # Reload registry to restore clean state
            PluginRegistry.discover_plugins(force_reload=True)
