from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Set
from fastapi import APIRouter
import json
import asyncio
import logging
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

logger = logging.getLogger(__name__)

class PluginFileHandler(FileSystemEventHandler):
    """插件文件监控处理器"""

    IGNORE_DIRS = {'assets', 'temp', 'static', '__pycache__'}

    def __init__(self, plugin_instance: 'PluginBase'):
        self.plugin = plugin_instance

    def should_ignore(self, path: str) -> bool:
        path_parts = path.split(os.sep)
        return any(ignored in path_parts for ignored in self.IGNORE_DIRS)

    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent) and not self.should_ignore(event.src_path):
            filename = os.path.basename(event.src_path)
            if filename == 'config.json':
                asyncio.create_task(self.plugin.on_config_changed())
            elif filename == 'plugin.json':
                asyncio.create_task(self.plugin.on_plugin_info_changed())

class PluginBase(ABC):
    def __init__(self, **kwargs):
        """初始化插件基类

        Parameters:
            context (Optional[Dict]): 插件上下文
            metadata (Optional[Dict]): 插件元数据
            config (Optional[Dict]): 插件配置
        """
        super().__init__()
        self.context: Dict[str, Any] = kwargs.get('context', {})
        self.config: Dict[str, Any] = kwargs.get('config', {})
        self.metadata: Dict[str, Any] = kwargs.get('metadata', {})
        self.observer: Optional[Observer] = None
        self._plugin_path: str = ''
        self._watched_paths: Set[str] = set()
        self.is_enabled: bool = False

    async def on_load(self) -> bool:
        """加载时调用"""
        return True

    async def on_enable(self) -> bool:
        """启用时调用"""
        self.is_enabled = True
        return True

    async def on_disable(self) -> bool:
        """禁用时调用"""
        self.is_enabled = False
        return True

    async def on_unload(self) -> bool:
        """卸载时调用"""
        return True

    def setup_file_monitor(self):
        """设置文件监控"""
        if not self._plugin_path:
            self._plugin_path = os.path.dirname(os.path.abspath(self.__class__.__module__.replace('.', os.sep)))

        if not self.observer:
            self.observer = Observer()
            event_handler = PluginFileHandler(self)

            self.observer.schedule(event_handler, self._plugin_path, recursive=True)
            self._watched_paths.add(self._plugin_path)

            self.observer.start()
            logger.info(f"Started file monitoring for plugin directory: {self._plugin_path}")

    def stop_file_monitor(self):
        """停止文件监控"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Stopped file monitoring")

    async def load_configs(self) -> bool:
        """加载配置文件"""
        try:
            # 设置插件路径
            if not self._plugin_path:
                self._plugin_path = os.path.dirname(os.path.abspath(self.__class__.__module__.replace('.', os.sep)))

            # 加载 plugin.json
            plugin_json_path = os.path.join(self._plugin_path, 'plugin.json')
            if os.path.exists(plugin_json_path):
                with open(plugin_json_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)

            # 加载 config.json
            config_json_path = os.path.join(self._plugin_path, 'config.json')
            if os.path.exists(config_json_path):
                with open(config_json_path, 'r', encoding='utf-8') as f:
                    self.config.update(json.load(f))

            return True
        except Exception as e:
            logger.error(f"Failed to load configs: {e}")
            return False

    async def initialize(self) -> bool:
        """插件初始化"""
        try:
            # 加载配置
            if not await self.load_configs():
                return False

            # 设置文件监控
            self.setup_file_monitor()

            return True
        except Exception as e:
            logger.error(f"Plugin initialization failed: {e}")
            return False

    async def cleanup(self) -> bool:
        """插件清理"""
        try:
            self.stop_file_monitor()
            return True
        except Exception as e:
            logger.error(f"Plugin cleanup failed: {e}")
            return False

    async def on_config_changed(self):
        """配置文件变更处理"""
        logger.info("Config file changed, reloading...")
        config_path = os.path.join(self._plugin_path, 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                new_config = json.load(f)
            self.config.update(new_config)
            await self.handle_config_update()
        except Exception as e:
            logger.error(f"Failed to handle config change: {e}")

    async def on_plugin_info_changed(self):
        """插件信息变更处理"""
        logger.info("Plugin info file changed, reloading...")
        try:
            plugin_json_path = os.path.join(self._plugin_path, 'plugin.json')
            with open(plugin_json_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            await self.handle_plugin_info_update()
        except Exception as e:
            logger.error(f"Failed to handle plugin info change: {e}")

    async def handle_config_update(self):
        """配置更新处理（可由子类重写）"""
        pass

    async def handle_plugin_info_update(self):
        """插件信息更新处理（可由子类重写）"""
        pass

    def update_config(self, config: Dict[str, Any]):
        """更新插件配置"""
        self.config.update(config)

    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass

    @abstractmethod
    def get_router(self) -> Optional[APIRouter]:
        """获取路由器"""
        pass
