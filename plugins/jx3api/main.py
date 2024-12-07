from typing import Optional, Dict
from fastapi import APIRouter, HTTPException
from plugin_base import PluginBase
from .jx3api_plugin import JX3APIPlugin
import logging
import time

logger = logging.getLogger(__name__)

class JX3Plugin(PluginBase):
    """剑网3 API插件主类"""
    
    def __init__(self, **kwargs):
        """初始化插件"""
        super().__init__(**kwargs)
        self.api = None
        self.router = APIRouter(prefix="/api/jx3api", tags=["jx3api"])
        self._setup_routes()
        
    @property
    def name(self) -> str:
        return "jx3api"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    def get_router(self) -> Optional[APIRouter]:
        return self.router
        
    def _normalize_response(self, data) -> Dict:
        """标准化响应格式"""
        return {
            "code": 200,
            "data": data,
            "message": "success",
            "time": int(time.time())
        }
        
    def _setup_routes(self):
        """设置路由"""
        @self.router.get("/info")
        async def get_info():
            """获取插件信息"""
            info = {
                "name": self.name,
                "version": self.version,
                "apis": self.api.list_apis() if self.api else []
            }
            return self._normalize_response(info)
            
        @self.router.get("/data/{api_name}")
        async def get_data(api_name: str, server: str, keyword: str = "", table: str = ""):
            """获取API数据"""
            try:
                # 检查是否为别名，如果是则获取实际API名称
                actual_api = self.api.get_api_by_alias(api_name)
                if actual_api:
                    api_name = actual_api
                    
                params = {
                    "server": server,
                    "keyword": keyword
                }
                if table:
                    params["table"] = table
                    
                data = self.api.get_api_data(api_name, params)
                return self._normalize_response(data)
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
                
        @self.router.get("/image/{api_name}")
        async def get_image(api_name: str, server: str, keyword: str = ""):
            """获取API图片"""
            try:
                # 检查是否为别名，如果是则获取实际API名称
                actual_api = self.api.get_api_by_alias(api_name)
                if actual_api:
                    api_name = actual_api
                    
                params = {
                    "server": server,
                    "keyword": keyword
                }
                
                image_data = self.api.get_api_image(api_name, params)
                return self._normalize_response({"image": image_data})
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
                
        # 添加别名访问支持
        @self.router.get("/{alias}")
        async def handle_alias(alias: str, server: str, keyword: str = "", table: str = ""):
            """通过别名访问API"""
            try:
                api_name = self.api.get_api_by_alias(alias)
                if not api_name:
                    raise HTTPException(status_code=404, detail=f"未找到API: {alias}")
                    
                params = {
                    "server": server,
                    "keyword": keyword
                }
                if table:
                    params["table"] = table
                    
                api_def = self.api.api_definitions.get(api_name)
                if not api_def:
                    raise HTTPException(status_code=404, detail=f"未找到API定义: {api_name}")
                
                # 根据API支持的类型返回数据
                if api_def.get("isDataApi"):
                    data = self.api.get_api_data(api_name, params)
                    return self._normalize_response(data)
                elif api_def.get("isImageApi"):
                    image_data = self.api.get_api_image(api_name, params)
                    return self._normalize_response({"image": image_data})
                else:
                    raise HTTPException(status_code=400, detail=f"API {api_name} 不支持任何请求类型")
                    
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))
    
    async def on_load(self) -> bool:
        """加载时调用"""
        try:
            # 初始化API插件
            self.api = JX3APIPlugin()
            logger.info(f"JX3API Plugin loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load JX3API Plugin: {e}")
            return False
            
    async def on_enable(self) -> bool:
        """启用时调用"""
        success = await super().on_enable()
        if success:
            logger.info("JX3API Plugin enabled")
        return success
        
    async def on_disable(self) -> bool:
        """禁用时调用"""
        success = await super().on_disable()
        if success:
            logger.info("JX3API Plugin disabled")
        return success
        
    async def on_unload(self) -> bool:
        """卸载时调用"""
        success = await super().on_unload()
        if success:
            logger.info("JX3API Plugin unloaded")
        return success
        
    async def handle_config_update(self):
        """处理配置更新"""
        logger.info("Reloading JX3API configuration")
        if self.api:
            self.api = JX3APIPlugin()  # 重新创建API实例以加载新配置