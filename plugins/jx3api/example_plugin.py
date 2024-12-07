from typing import Dict, Any
from .jx3api_plugin import JX3APIPlugin

class ExamplePlugin:
    """示例插件：展示如何使用JX3APIPlugin"""

    def __init__(self):
        """初始化插件"""
        # 创建JX3API插件实例
        self.jx3api = JX3APIPlugin()
        
    def handle_team_recruit(self, server: str, keyword: str = "") -> Dict[str, Any]:
        """
        处理团队招募信息
        :param server: 服务器名称
        :param keyword: 搜索关键词
        :return: 处理结果
        """
        try:
            # 准备请求参数
            params = {
                "server": server,
                "keyword": keyword
            }
            
            # 获取图片数据
            image_data = self.jx3api.get_api_image("团队招募", params)
            
            # 获取详细数据
            params["table"] = "recruit"  # 假设需要指定table参数
            data = self.jx3api.get_api_data("团队招募", params)
            
            return {
                "success": True,
                "image": image_data,
                "data": data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def handle_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        处理用户命令
        :param command: 用户命令
        :param kwargs: 其他参数
        :return: 处理结果
        """
        # 通过别名查找对应的API
        api_name = self.jx3api.get_api_by_alias(command)
        if not api_name:
            return {
                "success": False,
                "error": f"未找到命令: {command}"
            }
            
        # 根据API名称调用相应的处理方法
        if api_name == "团队招募":
            return self.handle_team_recruit(**kwargs)
        
        return {
            "success": False,
            "error": f"未实现的命令处理: {command}"
        }

# 使用示例
if __name__ == "__main__":
    plugin = ExamplePlugin()
    
    # 示例1：使用API名称直接调用
    result = plugin.handle_team_recruit(server="双线一区", keyword="日常")
    if result["success"]:
        print("获取团队招募信息成功")
        print(f"数据：{result['data']}")
        # 这里可以保存或显示图片数据
    else:
        print(f"错误：{result['error']}")
    
    # 示例2：使用别名调用
    result = plugin.handle_command("招募", server="双线一区")
    if result["success"]:
        print("通过别名调用成功")
    else:
        print(f"错误：{result['error']}")
