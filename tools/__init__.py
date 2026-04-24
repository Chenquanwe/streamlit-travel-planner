"""工具模块 - 包含高德地图工具"""

from tools.amap_tools import (
    search_attractions,
    query_weather,
    search_hotels,
    get_amap_service,
    AMapService,
)

# 注意：MCP 相关导入已移除，因为现在使用 LangChain 官方适配器
# 如果不需要 MCP 模式，可以注释掉以下导入

__all__ = [
    "search_attractions",
    "query_weather",
    "search_hotels",
    "get_amap_service",
    "AMapService",
]