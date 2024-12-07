import os
import json
import sys
import importlib.util
import asyncio
from typing import Dict, List, Type, Optional
import logging
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from plugin_base import PluginBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConfigFileHandler(FileSystemEventHandler):
    def __init__(self, plugin_manager):
        self.plugin_manager = plugin_manager
        self.last_reload = {}  # 用于防止重复重载

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('config.json'):
            # 获取插件名称（从路径中提取）
            plugin_dir = os.path.dirname(event.src_path)
            plugin_name = os.path.basename(plugin_dir)

            # 防止重复重载（文件系统可能触发多次事件）
            current_time = time.time()
            if plugin_name in self.last_reload and current_time - self.last_reload[plugin_name] < 1:
                return

            self.last_reload[plugin_name] = current_time
            logger.info(f"Config file changed for plugin: {plugin_name}")

            # 使用异步事件循环重载插件
            asyncio.run(self.plugin_manager.reload_plugin(plugin_name))

class PluginManager:
    def __init__(self, plugin_dir: str = "plugins", context: Dict = None):
        """
        初始化插件管理器
        :param plugin_dir: 插件目录
        :param context: 上下文信息，将传递给插件
        """
        self.plugin_dir = plugin_dir
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_classes: Dict[str, Type[PluginBase]] = {}
        self.context = context or {}

        # 设置文件监视器
        self.observer = Observer()
        self.observer.schedule(
            ConfigFileHandler(self),
            path=self.plugin_dir,
            recursive=True
        )
        self.observer.start()

    def __del__(self):
        """确保清理文件监视器"""
        if hasattr(self, 'observer'):
            self.observer.stop()
            self.observer.join()

    def discover_plugins(self) -> List[str]:
        """发现插件目录中的所有插件"""
        plugin_dirs = []
        try:
            for item in os.listdir(self.plugin_dir):
                item_path = os.path.join(self.plugin_dir, item)
                if (os.path.isdir(item_path) and
                    not item.startswith('__') and
                    os.path.exists(os.path.join(item_path, "config.json"))):
                    plugin_dirs.append(item)
        except Exception as e:
            logger.error(f"Error discovering plugins: {str(e)}")
        return plugin_dirs

    def load_plugin_metadata(self, plugin_name: str) -> Optional[Dict]:
        """加载插件元数据"""
        try:
            config_path = os.path.join(self.plugin_dir, plugin_name, "config.json")
            if not os.path.exists(config_path):
                logger.error(f"No config.json found for plugin {plugin_name}")
                return None

            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading metadata for plugin {plugin_name}: {str(e)}")
            return None

    async def reload_plugin(self, plugin_name: str) -> bool:
        """重新加载插件"""
        try:
            logger.info(f"Reloading plugin: {plugin_name}")

            # 如果插件已加载，先卸载
            if plugin_name in self.plugins:
                was_enabled = self.plugins[plugin_name].is_enabled
                await self.unload_plugin(plugin_name)

                # 重新加载
                success = await self.load_plugin(plugin_name)
                if success and was_enabled:
                    await self.enable_plugin(plugin_name)

                return success

            return False

        except Exception as e:
            logger.error(f"Error reloading plugin {plugin_name}: {str(e)}")
            return False

    async def load_plugin(self, plugin_name: str) -> bool:
        """加载并初始化插件"""
        try:
            if plugin_name in self.plugins:
                logger.warning(f"Plugin {plugin_name} already loaded")
                return False

            # 首先加载元数据
            metadata = self.load_plugin_metadata(plugin_name)
            if metadata is None:
                return False

            # 加载插件主模块
            main_file = metadata.get("main", "main.py")
            plugin_path = os.path.join(self.plugin_dir, plugin_name, main_file)

            if not os.path.exists(plugin_path):
                logger.error(f"Plugin main file not found: {plugin_path}")
                return False

            # 重新加载模块（如果已经加载过）
            module_name = f"plugins.{plugin_name}.{main_file[:-3]}"
            if module_name in sys.modules:
                del sys.modules[module_name]

            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load spec for plugin: {plugin_name}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找插件类
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and
                    issubclass(attr, PluginBase) and
                    attr != PluginBase):
                    plugin_class = attr
                    break

            if plugin_class is None:
                raise ValueError(f"No valid plugin class found in {plugin_name}")

            # 创建插件实例，传入元数据和配置
            plugin_instance = plugin_class(
                context=self.context,
                metadata=metadata,
                config=metadata.get("config", {})
            )
            await plugin_instance.on_load()

            self.plugins[plugin_name] = plugin_instance
            self.plugin_classes[plugin_name] = plugin_class
            logger.info(f"Successfully loaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Error initializing plugin {plugin_name}: {str(e)}")
            return False

    async def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        try:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin {plugin_name} not loaded")
                return False

            plugin = self.plugins[plugin_name]
            if plugin.is_enabled:
                await plugin.on_disable()
            await plugin.on_unload()

            del self.plugins[plugin_name]
            del self.plugin_classes[plugin_name]
            logger.info(f"Successfully unloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {str(e)}")
            return False

    async def enable_plugin(self, plugin_name: str) -> bool:
        """启用插件"""
        try:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin {plugin_name} not loaded")
                return False

            plugin = self.plugins[plugin_name]
            if plugin.is_enabled:
                logger.warning(f"Plugin {plugin_name} already enabled")
                return False

            await plugin.on_enable()
            logger.info(f"Successfully enabled plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Error enabling plugin {plugin_name}: {str(e)}")
            return False

    async def disable_plugin(self, plugin_name: str) -> bool:
        """禁用插件"""
        try:
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin {plugin_name} not loaded")
                return False

            plugin = self.plugins[plugin_name]
            if not plugin.is_enabled:
                logger.warning(f"Plugin {plugin_name} already disabled")
                return False

            await plugin.on_disable()
            logger.info(f"Successfully disabled plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Error disabling plugin {plugin_name}: {str(e)}")
            return False

    def get_plugin_status(self, plugin_name: str) -> Dict:
        """获取插件状态"""
        if plugin_name not in self.plugins:
            metadata = self.load_plugin_metadata(plugin_name)
            return {
                "status": "not_loaded",
                "enabled": False,
                "metadata": metadata
            }

        plugin = self.plugins[plugin_name]
        return {
            "status": "loaded",
            "enabled": plugin.is_enabled,
            "metadata": plugin.metadata,
            "config": plugin.config
        }

    def update_plugin_config(self, plugin_name: str, config: Dict) -> bool:
        """更新插件配置"""
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin {plugin_name} not loaded")
            return False

        try:
            self.plugins[plugin_name].update_config(config)
            logger.info(f"Successfully updated config for plugin: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"Error updating config for plugin {plugin_name}: {str(e)}")
            return False
