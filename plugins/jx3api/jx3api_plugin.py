from typing import Dict, List, Optional
import json
import os
import requests
from urllib.parse import urljoin
import logging

logger = logging.getLogger(" JX3API Plugins")

class JX3APIPlugin:
    """剑网3 API插件核心类"""

    def __init__(self, config_path: str = None):
        """
        初始化插件
        :param config_path: 配置文件路径，如果为None则使用默认路径
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        self.config_path = config_path
        logger.info(f" 加载配置文件: {config_path}")

        self.config = self._load_config()
        self.base_endpoint = self.config.get("endPoint", "")
        self.api_config = self.config.get("config", {})
        self.api_definitions = self.config.get("api", {})

        logger.info(f" 配置中的API接口: {list(self.api_definitions.keys())}")

    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f" 加载配置文件失败: {str(e)}")
            raise Exception(f"加载配置文件失败: {str(e)}")

    def _build_url(self, api_name: str, is_image: bool, params: Dict) -> str:
        """构建完整的API URL"""
        logger.info(f"Building URL for api={api_name}, is_image={is_image}, params={params}")

        if api_name not in self.api_definitions:
            logger.error(f" 未找到API: {api_name}")
            raise ValueError(f"未找到API: {api_name}")

        api_def = self.api_definitions[api_name]

        # 确定基础URL和端点
        base_url = self.api_config["imageUrl"] if is_image else self.api_config["dataUrl"]
        endpoint = api_def['endPoint']

        # 构建完整的基础URL
        full_base_url = f"{base_url}{endpoint}"
        # logger.info(f" Base URL: {full_base_url}")

        # 添加token参数
        token = self.api_config.get("token_v2") if api_def["isV2"] else self.api_config.get("token_v1")
        params = {**params, "token": token}

        # 获取对应请求模板
        request_template = api_def.get("imageRequest" if is_image else "dataRequest", "")
        if not request_template:
            logger.error(f" {api_name} 并没有图片请求接口 ")
            raise ValueError(f"API {api_name} 未配置{'图片' if is_image else '数据'}请求模板")

        # 替换模板中的参数
        query_params = request_template
        for key, value in params.items():
            placeholder = f"#{key}#"
            if placeholder in query_params:
                if value:  # 如果值非空，进行替换
                    query_params = query_params.replace(placeholder, str(value))
                else:  # 如果值为空，移除该占位符
                    query_params = query_params.replace(placeholder, "")

        # 移除未被替换的占位符以及多余的`&`符号
        query_params = "&".join(
            part for part in query_params.split("&") if "=" in part and not part.endswith("=")
        )
        valid_parts = [
            part for part in query_params.split("&")
            if "=" in part and not part.endswith("=") and "#" not in part
        ]
        query_params = "&".join(valid_parts)
        # 最终的URL
        final_url = f"{full_base_url}?{query_params}".rstrip("?&")
        logger.info(f"Final URL: {final_url}")
        return final_url

    def get_api_data(self, api_name: str, params: Dict) -> Dict:
        """
        获取API数据
        :param api_name: API名称
        :param params: 请求参数
        :return: API响应数据
        """
        logger.info(f"Making data request for api={api_name}, params={params}")
        url = self._build_url(api_name, False, params)
        logger.info(f"Making request to: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise Exception(f"API请求失败: {str(e)}")

    def get_api_image(self, api_name: str, params: Dict) -> Dict:
        """
        获取API图片，返回图片数据的响应
        :param api_name: API名称
        :param params: 请求参数
        :return: API响应数据
        """
        logger.info(f"Making image request for api={api_name}, params={params}")
        url = self._build_url(api_name, True, params)
        logger.info(f"Making request to: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise Exception(f"API请求失败: {str(e)}")

    def get_api_by_alias(self, alias: str) -> Optional[str]:
        """
        通过别名获取API名称
        :param alias: API别名
        :return: API名称，如果未找到则返回None
        """
        logger.info(f"Looking up API by alias: {alias}")
        # 首先检查是否直接是API名称
        if alias in self.api_definitions:
            logger.info(f"Found direct API match: {alias}")
            return alias

        # 然后检查别名
        for api_name, api_def in self.api_definitions.items():
            if alias in api_def.get("alias", []):
                logger.info(f"Found API: {api_name} for alias: {alias}")
                return api_name

        logger.info(f"No API found for alias: {alias}")
        return None

    def list_apis(self) -> List[Dict]:
        """
        列出所有对外开放的API及其信息
        :return: API信息列表
        """
        apis = [
            {
                "name": name,
                "endpoint": api["endPoint"],
                "alias": api.get("alias", []),
                "supports_image": api.get("isImageApi", False),
                "supports_data": api.get("isDataApi", False)
            }
            for name, api in self.api_definitions.items()
            if api.get("isEnable", False)  # 只返回对外开放的API
        ]
        # logger.info(f" Listed APIs: {apis}")
        return apis
