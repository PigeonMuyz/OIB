from typing import Optional, Dict
from fastapi import APIRouter, HTTPException, Query
import sys
import os

# 添加父目录到 Python 路径以导入 PluginBase
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from plugin_base import PluginBase
from .jx3api_plugin import JX3APIPlugin
import logging
import time
from enum import Enum
from fastapi.responses import JSONResponse, Response, RedirectResponse

logger = logging.getLogger(" JX3API Plugins")

class RequestType(str, Enum):
    DATA = "data"
    IMAGE = "image"

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

    def _normalize_response(self, response_data: Dict) -> Dict:
        """标准化响应格式，将远程API的响应格式转换为本地格式"""
        return {
            "code": response_data.get("code", 200),
            "data": response_data.get("data", None),
            "message": response_data.get("msg", "success"),
            "time": int(time.time())
        }

    async def _process_image(self, image_url: str) -> str:
        """
        处理图片URL，可以在这里添加将图片上传到存储桶的逻辑
        :param image_url: 原始图片URL
        :return: 处理后的图片URL（存储桶URL）
        """
        # TODO: 在此处添加图片处理逻辑
        # 1. 下载图片
        # 2. 上传到存储桶
        # 3. 返回存储桶URL
        return image_url  # 目前直接返回原始URL

    async def _handle_request(self, api_name: str, request_type: RequestType, params: Dict, internal: bool = False) -> Response:
        """统一处理请求"""
        try:
            logger.info(f"Processing request: api_name={api_name}, type={request_type}, params={params}")

            # 检查API是否存在或是别名
            actual_api = self.api.get_api_by_alias(api_name) or api_name
            logger.info(f"Resolved API name: {actual_api}")

            api_def = self.api.api_definitions.get(actual_api)
            logger.info(f"API definition: {api_def}")

            if not api_def:
                logger.error(f"API not found: {api_name}")
                return JSONResponse(
                    status_code=404,
                    content={
                        "code": 404,
                        "data": None,
                        "message": f"未找到API: {api_name}",
                        "time": int(time.time())
                    }
                )

            # 检查API是否启用（仅对外部请求检查）
            if not internal and not api_def.get("isEnable", False):
                logger.error(f" 当前API {actual_api} 未对外开放")
                return JSONResponse(
                    status_code=403,
                    content={
                        "code": 403,
                        "data": None,
                        "message": f"API {actual_api} 未对外开放",
                        "time": int(time.time())
                    }
                )

            try:
                # 根据请求类型获取数据
                if request_type == RequestType.DATA:
                    response_data = self.api.get_api_data(actual_api, params)
                else:
                    # 对于图片请求使用专门的图片API
                    response_data = self.api.get_api_image(actual_api, params)

                # 标准化响应数据
                response = self._normalize_response(response_data)

                # 如果是图片请求且响应成功，处理图片URL
                if request_type == RequestType.IMAGE and response["code"] == 200 and response["data"] and "url" in response["data"]:
                    # 处理图片URL，这里可以添加上传到存储桶的逻辑
                    response["data"]["url"] = await self._process_image(response["data"]["url"])

                if response["code"] != 200:
                    return JSONResponse(status_code=response["code"], content=response)

                return JSONResponse(content=response)

            except Exception as e:
                logger.error(f"API request failed: {str(e)}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "code": 400,
                        "data": None,
                        "message": str(e),
                        "time": int(time.time())
                    }
                )

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=400,
                content={
                    "code": 400,
                    "data": None,
                    "message": str(e),
                    "time": int(time.time())
                }
            )

    def _setup_routes(self):
        """设置路由"""
        @self.router.get("/info")
        async def get_info():
            """获取插件信息"""
            info = {
                "name": self.name,
                "version": self.version,
                "apis": self.api.list_apis() if self.api else []  # 只返回对外开放的API
            }
            return self._normalize_response({"data": info})

        @self.router.get("/data/{api_name}")
        async def get_data(api_name: str, server: str = Query(...), keyword: str = "", table: str = "", name: str = ""):
            """数据API入口"""
            params = {}
            if server:
                params["server"] = server
            if keyword:
                params["keyword"] = keyword
            if table:
                params["table"] = table
            if name:
                params["name"] = name

            return await self._handle_request(api_name, RequestType.DATA, params)

        @self.router.get("/image/{api_name}")
        async def get_image(api_name: str, server: str = Query(...), keyword: str = ""):
            """图片API入口"""
            params = {
                "server": server,
                "keyword": keyword
            }

            return await self._handle_request(api_name, RequestType.IMAGE, params)

        @self.router.get("/{api_name}")
        async def handle_request(
            api_name: str,
            type: RequestType = Query(..., description="请求类型: data 或 image"),
            server: str = Query(..., description="服务器名称"),
            keyword: str = Query("", description="搜索关键词"),
            table: str = Query("", description="数据表名")
        ):
            """统一的API处理入口"""
            params = {
                "server": server,
                "keyword": keyword
            }
            if table:
                params["table"] = table

            return await self._handle_request(api_name, type, params)

        @self.router.get("/internal/{api_name}")
        async def handle_internal_request(
            api_name: str,
            type: RequestType = Query(..., description="请求类型: data 或 image"),
            server: str = Query(..., description="服务器名称"),
            keyword: str = Query("", description="搜索关键词"),
            table: str = Query("", description="数据表名")
        ):
            """内部API处理入口"""
            logger.info(f"Internal API request: {api_name}, type={type}, server={server}, keyword={keyword}, table={table}")
            params = {
                "server": server,
                "keyword": keyword
            }
            if table:
                params["table"] = table

            return await self._handle_request(api_name, type, params, internal=True)

    async def on_load(self) -> bool:
        """加载时调用"""
        try:
            # 初始化API插件
            self.api = JX3APIPlugin()
            apis = self.api.list_apis()
            logger.info(f" 成功加载")
            return True
        except Exception as e:
            logger.error(f" 加载失败 {e}")
            return False

    async def on_enable(self) -> bool:
        """启用时调用"""
        success = await super().on_enable()
        # if success:
        #     logger.info(" JX3API Plugin enabled")
        return success

    async def on_disable(self) -> bool:
        """禁用时调用"""
        success = await super().on_disable()
        # if success:
        #     logger.info("JX3API Plugin disabled")
        return success

    async def on_unload(self) -> bool:
        """卸载时调用"""
        success = await super().on_unload()
        if success:
            logger.info(" 插件卸载 ")
        return success
