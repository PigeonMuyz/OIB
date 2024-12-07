from typing import Dict, List, Optional
import json
import os
import requests
from urllib.parse import urljoin

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
        self.config = self._load_config()
        self.base_endpoint = self.config.get("endPoint", "")
        self.api_config = self.config.get("config", {})
        self.api_definitions = self.config.get("api", {})

    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"加载配置文件失败: {str(e)}")

    def _replace_params(self, url: str, params: Dict) -> str:
        """替换URL中的参数"""
        for key, value in params.items():
            placeholder = f"#{key}#"
            if placeholder in url:
                url = url.replace(placeholder, str(value))
        return url

    def _build_url(self, api_name: str, is_image: bool, params: Dict) -> str:
        """构建完整的API URL"""
        if api_name not in self.api_definitions:
            raise ValueError(f"未找到API: {api_name}")

        api_def = self.api_definitions[api_name]
        if not api_def.get("isEnable", False):
            raise ValueError(f"API {api_name} 未启用")

        # 确定基础URL
        base_url = self.api_config["imageUrl"] if is_image else self.api_config["dataUrl"]
        
        # 构建请求参数
        request_template = api_def.get("imageRequest" if is_image else "dataRequest", "")
        if not request_template:
            raise ValueError(f"API {api_name} 未配置{'图片' if is_image else '数据'}请求模板")

        # 添加token到参数中
        if "token" not in params:
            params["token"] = self.api_config.get("token_v1", "")

        # 替换参数并构建完整URL
        query_string = self._replace_params(request_template, params)
        return f"{base_url}{api_def['endPoint']}?{query_string}"

    def get_api_data(self, api_name: str, params: Dict) -> Dict:
        """
        获取API数据
        :param api_name: API名称
        :param params: 请求参数
        :return: API响应数据
        """
        if api_name not in self.api_definitions:
            raise ValueError(f"未找到API: {api_name}")

        api_def = self.api_definitions[api_name]
        if not api_def.get("isDataApi", False):
            raise ValueError(f"API {api_name} 不支持数据请求")

        url = self._build_url(api_name, False, params)
        response = requests.get(url)
        return response.json()

    def get_api_image(self, api_name: str, params: Dict) -> bytes:
        """
        获取API图片
        :param api_name: API名称
        :param params: 请求参数
        :return: 图片二进制数据
        """
        if api_name not in self.api_definitions:
            raise ValueError(f"未找到API: {api_name}")

        api_def = self.api_definitions[api_name]
        if not api_def.get("isImageApi", False):
            raise ValueError(f"API {api_name} 不支持图片请求")

        url = self._build_url(api_name, True, params)
        response = requests.get(url)
        return response.content

    def get_api_by_alias(self, alias: str) -> Optional[str]:
        """
        通过别名获取API名称
        :param alias: API别名
        :return: API名称，如果未找到则返回None
        """
        for api_name, api_def in self.api_definitions.items():
            if alias in api_def.get("alias", []):
                return api_name
        return None

    def list_apis(self) -> List[Dict]:
        """
        列出所有启用的API及其信息
        :return: API信息列表
        """
        return [
            {
                "name": name,
                "endpoint": api["endPoint"],
                "alias": api.get("alias", []),
                "supports_image": api.get("isImageApi", False),
                "supports_data": api.get("isDataApi", False)
            }
            for name, api in self.api_definitions.items()
            if api.get("isEnable", False)
        ]