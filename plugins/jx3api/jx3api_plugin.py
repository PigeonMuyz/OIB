from typing import Dict, List, Optional
import json
import os
import requests
from urllib.parse import urljoin
import sys

# 添加父目录到 Python 路径以导入 utils
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from utils import setup_logger

logger = setup_logger("JX3API.Core")  # 使用子logger名称区分不同模块

class JX3APIPlugin:
    """剑网3 API插件核心类"""

    def __init__(self, config_path: str = None):
        """
        初始化插件
        :param config_path: 配置文件路径，如果为None则使用默认路径
        """
        if config_path is None:
            self.config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            self.endpoints_path = os.path.join(os.path.dirname(__file__), 'endpoints.json')
        else:
            self.config_path = config_path
            self.endpoints_path = os.path.join(os.path.dirname(config_path), 'endpoints.json')

        logger.info(f"加载配置文件: {self.config_path}")
        logger.info(f"加载端点配置: {self.endpoints_path}")

        self.config = self._load_config()
        self.base_endpoint = self.config.get("endPoint", "")
        self.api_config = self.config.get("config", {})
        self.api_definitions = self._load_endpoints()

    def _load_config(self) -> Dict:
        """加载主配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            raise Exception(f"加载配置文件失败: {str(e)}")

    def _load_endpoints(self) -> Dict:
        """加载API端点配置文件"""
        try:
            with open(self.endpoints_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载API端点配置失败: {str(e)}")
            raise Exception(f"加载API端点配置失败: {str(e)}")

    def reload(self):
        """重新加载所有配置"""
        try:
            self.config = self._load_config()
            self.base_endpoint = self.config.get("endPoint", "")
            self.api_config = self.config.get("config", {})
            self.api_definitions = self._load_endpoints()
            logger.info("配置重新加载完成")
        except Exception as e:
            logger.error(f"重新加载配置失败: {str(e)}")
            raise

    def _build_url(self, api_name: str, is_image: bool, params: Dict) -> str:
        """构建完整的API URL"""
        if api_name not in self.api_definitions:
            logger.error(f"未找到API: {api_name}")
            raise ValueError(f"未找到API: {api_name}")

        api_def = self.api_definitions[api_name]

        # 确定基础URL和端点
        base_url = self.api_config["imageUrl"] if is_image else self.api_config["dataUrl"]
        endpoint = api_def['endPoint']

        # 构建完整的基础URL
        full_base_url = f"{base_url}{endpoint}"

        # 添加token参数
        token = self.api_config.get("token_v2") if api_def["isV2"] else self.api_config.get("token_v1")
        params = {**params, "token": token}

        # 获取对应请求模板
        request_template = api_def.get("imageRequest" if is_image else "dataRequest", "")
        if not request_template:
            logger.error(f"{api_name} 并没有{('图片' if is_image else '数据')}请求接口")
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
        valid_parts = [
            part for part in query_params.split("&")
            if "=" in part and not part.endswith("=") and "#" not in part
        ]
        query_params = "&".join(valid_parts)
        # 最终的URL
        final_url = f"{full_base_url}?{query_params}".rstrip("?&")
        logger.debug(f"构建URL: {final_url}")
        return final_url

    def get_api_data(self, api_name: str, params: Dict) -> Dict:
        """
        获取API数据
        :param api_name: API名称
        :param params: 请求参数
        :return: API响应数据
        """
        logger.info(f"请求数据: api={api_name}, 参数={params}")
        url = self._build_url(api_name, False, params)
        logger.debug(f"请求URL: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API请求失败: {str(e)}")
            raise Exception(f"API请求失败: {str(e)}")

    def get_api_image(self, api_name: str, params: Dict) -> Dict:
        """
        获取API图片，返回图片数据的响应
        :param api_name: API名称
        :param params: 请求参数
        :return: API响应数据
        """
        logger.info(f"请求图片: api={api_name}, 参数={params}")
        url = self._build_url(api_name, True, params)
        logger.debug(f"请求URL: {url}")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API请求失败: {str(e)}")
            raise Exception(f"API请求失败: {str(e)}")

    def get_api_by_alias(self, alias: str) -> Optional[str]:
        """
        通过别名获取API名称
        :param alias: API别名
        :return: API名称，如果未找到则返回None
        """
        # 首先检查是否直接是API名称
        if alias in self.api_definitions:
            return alias

        # 然后检查别名
        for api_name, api_def in self.api_definitions.items():
            if alias in api_def.get("alias", []):
                return api_name

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
        return apis
