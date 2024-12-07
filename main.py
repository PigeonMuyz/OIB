from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import uvicorn
import logging
import asyncio
from contextlib import asynccontextmanager

from plugin_manager import PluginManager

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(" 主入口")

# 创建生命周期管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用程序生命周期管理"""
    # 启动时的操作
    # 发现所有插件
    plugins = plugin_manager.discover_plugins()
    logger.info(f" 发现插件: {plugins}")

    # 加载并启用所有插件
    for plugin_name in plugins:
        try:
            # 加载插件
            success = await plugin_manager.load_plugin(plugin_name)
            if success:
                # 获取插件实例
                plugin = plugin_manager.plugins[plugin_name]

                # 如果插件有路由，添加到应用中
                if hasattr(plugin, 'get_router') and callable(plugin.get_router):
                    router = plugin.get_router()
                    if router:
                        app.include_router(router)
                        logger.info(f" 插件 {plugin_name} 添加路由成功")

                # 启用插件
                await plugin_manager.enable_plugin(plugin_name)
                logger.info(f" 启用插件: {plugin_name}")
            else:
                logger.error(f" 加载插件 {plugin_name} 出错")
        except Exception as e:
            logger.error(f" 初始化插件 {plugin_name} 报错: {str(e)}")

    yield

    # 关闭时的操作
    # 禁用所有插件
    for plugin_name in list(plugin_manager.plugins.keys()):
        await plugin_manager.disable_plugin(plugin_name)
        await plugin_manager.unload_plugin(plugin_name)

# 创建FastAPI应用实例
app = FastAPI(
    title="Plugin System Demo",
    lifespan=lifespan
)

# 创建插件管理器实例，传入app上下文
plugin_manager = PluginManager(context={"app": app})

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/plugins")
async def get_plugins() -> List[str]:
    """获取所有可用插件列表"""
    return plugin_manager.discover_plugins()

@app.get("/api/plugins/{plugin_name}/status")
async def get_plugin_status(plugin_name: str) -> Dict:
    """获取插件状态"""
    return plugin_manager.get_plugin_status(plugin_name)

@app.post("/api/plugins/{plugin_name}/load")
async def load_plugin(plugin_name: str):
    """加载插件"""
    success = await plugin_manager.load_plugin(plugin_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to load plugin: {plugin_name}")

    # 如果插件有路由，添加到应用中
    plugin = plugin_manager.plugins.get(plugin_name)
    if plugin and hasattr(plugin, 'get_router') and callable(plugin.get_router):
        router = plugin.get_router()
        if router:
            app.include_router(router)
            logger.info(f" 插件 {plugin_name} 添加路由成功")

    return {"status": "success", "message": f"Plugin {plugin_name} loaded successfully"}

@app.post("/api/plugins/{plugin_name}/unload")
async def unload_plugin(plugin_name: str):
    """卸载插件"""
    success = await plugin_manager.unload_plugin(plugin_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to unload plugin: {plugin_name}")
    return {"status": "success", "message": f"Plugin {plugin_name} unloaded successfully"}

@app.post("/api/plugins/{plugin_name}/enable")
async def enable_plugin(plugin_name: str):
    """启用插件"""
    success = await plugin_manager.enable_plugin(plugin_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to enable plugin: {plugin_name}")
    return {"status": "success", "message": f"Plugin {plugin_name} enabled successfully"}

@app.post("/api/plugins/{plugin_name}/disable")
async def disable_plugin(plugin_name: str):
    """禁用插件"""
    success = await plugin_manager.disable_plugin(plugin_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to disable plugin: {plugin_name}")
    return {"status": "success", "message": f"Plugin {plugin_name} disabled successfully"}

@app.patch("/api/plugins/{plugin_name}/config")
async def update_plugin_config(plugin_name: str, config: Dict):
    """更新插件配置"""
    success = plugin_manager.update_plugin_config(plugin_name, config)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to update config for plugin: {plugin_name}")
    return {"status": "success", "message": f"Plugin {plugin_name} config updated successfully"}

# 程序入口点
if __name__ == "__main__":
    # 启动ASGI服务器
    uvicorn.run(
        "main:app",  # 使用模块路径
        host="0.0.0.0",
        port=8000,
        reload=True  # 启用热重载
    )
