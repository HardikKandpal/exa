import importlib
import inspect
import logging
import os
import sys

from app.agent.base_plugin import PluginBase

logger = logging.getLogger(__name__)


def register_plugin(cls: type[PluginBase]) -> type[PluginBase]:
    """Decorator for registering a PluginBase subclass automatically."""
    PluginRegistry.register(cls)
    return cls


class PluginRegistry:
    """
    Dynamic Registry for Agent Plugins.
    Scans plugins directory on startup using importlib, importing all modules
    and registering decorated or subclassed PluginBase implementations automatically.
    """

    _plugins: dict[str, PluginBase] = {}
    _discovered: bool = False

    @classmethod
    def register(cls, plugin_cls: type[PluginBase]):
        instance = plugin_cls()
        cls._plugins[instance.name] = instance
        logger.info(f"Registered plugin: [{instance.name}] -> {plugin_cls.__name__}")

    @classmethod
    def discover_plugins(cls, plugins_dir: str | None = None, force_reload: bool = False) -> dict[str, PluginBase]:
        """Scans plugins directory and instantiates all PluginBase implementations."""
        if cls._discovered and not force_reload and not plugins_dir:
            return cls._plugins

        if plugins_dir is None:
            plugins_dir = os.path.join(os.path.dirname(__file__), "plugins")

        cls._plugins = {}
        logger.info(f"Scanning plugins directory: {plugins_dir}")

        if not os.path.exists(plugins_dir):
            logger.warning(f"Plugins directory not found at {plugins_dir}")
            return cls._plugins

        if plugins_dir not in sys.path:
            sys.path.insert(0, plugins_dir)

        for filename in os.listdir(plugins_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                full_module_name = f"app.agent.plugins.{module_name}"
                try:
                    module = importlib.import_module(full_module_name)
                    importlib.reload(module)

                    for name, obj in inspect.getmembers(module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, PluginBase)
                            and obj is not PluginBase
                        ):
                            cls.register(obj)
                except Exception as e:
                    logger.error(f"Failed to load plugin module {full_module_name}: {e}")

        cls._discovered = True
        return cls._plugins

    @classmethod
    def get_plugin(cls, name: str) -> PluginBase | None:
        cls.discover_plugins()
        return cls._plugins.get(name)

    @classmethod
    def get_all_plugins(cls) -> dict[str, PluginBase]:
        cls.discover_plugins()
        return cls._plugins

    @classmethod
    def build_system_prompt_tools_description(cls) -> str:
        """Dynamically builds system prompt tool descriptions from registered plugins."""
        plugins = cls.get_all_plugins()
        descriptions = []
        for name, plugin in plugins.items():
            schema_json = plugin.input_schema.model_json_schema()
            properties = schema_json.get("properties", {})
            required = schema_json.get("required", [])
            args_str = ", ".join([f"{k}: {v.get('type', 'any')}{' (required)' if k in required else ''}" for k, v in properties.items()])

            desc = (
                f"Tool: `{name}`\n"
                f"Description: {plugin.description}\n"
                f"Consumes: {plugin.can_consume}\n"
                f"Produces: {plugin.can_produce}\n"
                f"Arguments: {{{args_str}}}"
            )
            descriptions.append(desc)

        return "\n\n".join(descriptions)
