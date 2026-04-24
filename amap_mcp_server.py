"""
高德地图 MCP 服务器 - 使用 FastMCP 框架

MCP (Model Context Protocol) 是一种标准化协议，允许 AI 应用发现和调用外部工具。
这个文件实现了一个 MCP 服务器，将高德地图 API 封装成可被 AI Agent 调用的工具。

工作流程：
1. 启动服务器，通过 stdio 监听客户端的 JSON-RPC 请求
2. 客户端发送 "tools/list" 请求时，返回所有 @mcp.tool() 装饰的函数
3. 客户端发送 "tools/call" 请求时，执行对应的函数并返回结果

启动命令：
    python -u amap_mcp_server.py
    -u 参数禁用输出缓冲，确保实时通信
"""

# ==================== 标准库导入 ====================
import os          # 操作系统接口，用于读取环境变量
import json        # JSON 解析，用于格式化路线规划返回结果
import httpx       # 异步 HTTP 客户端，用于调用高德地图 API

# ==================== MCP 框架导入 ====================
from mcp.server.fastmcp import FastMCP
# FastMCP 是 MCP 协议的 Python 实现框架
# 它封装了 JSON-RPC 通信、工具注册、请求路由等底层细节
# 开发者只需要用 @mcp.tool() 装饰器即可将函数注册为工具


# ==================== 初始化 MCP 服务器 ====================
# 创建 FastMCP 服务器实例
# 参数 "AmapWeather" 是服务器名称，用于日志和标识
mcp = FastMCP("AmapWeather")

# 从环境变量读取高德 API Key
# 这个 Key 由父进程（supervisor.py）通过 env 参数传递
# 如果没有读到，返回空字符串，后续工具会返回错误提示
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")


# ==================== 工具1：天气查询 ====================
@mcp.tool()
# @mcp.tool() 装饰器的作用：
# 1. 将此函数注册为 MCP 工具
# 2. 自动提取函数名、参数、文档字符串作为工具描述
# 3. 当客户端调用此工具时，自动执行此函数
async def get_weather(city: str) -> str:
    """
    通过城市名称查询实时天气和未来天气预报。

    Args:
        city: 需要查询天气的城市名称，例如 '北京'、'上海'。
    """
    # ----- 安全检查 -----
    # 如果没有配置 API Key，返回错误提示
    if not AMAP_API_KEY:
        return "错误: 未配置高德地图 API Key"

    # ----- 构建 API 请求 -----
    # 高德天气 API 端点
    url = "https://restapi.amap.com/v3/weather/weatherInfo"

    # 请求参数
    params = {
        "city": city,               # 城市名称
        "key": AMAP_API_KEY,        # API 密钥
        "extensions": "all"         # "all" 返回未来天气，"base" 返回实时天气
    }

    # ----- 发送异步 HTTP 请求 -----
    # async with 创建异步上下文管理器，自动管理连接
    async with httpx.AsyncClient() as client:
        try:
            # 发起 GET 请求，超时 10 秒
            response = await client.get(url, params=params, timeout=10.0)

            # 检查 HTTP 状态码，如果不是 2xx 会抛出异常
            response.raise_for_status()

            # 解析 JSON 响应
            data = response.json()

            # ----- 解析天气数据 -----
            # 检查 API 返回状态
            if data.get("status") == "1" and data.get("forecasts"):
                # 获取第一个城市的天气预报
                forecast = data["forecasts"][0]
                # 获取未来几天的天气列表
                casts = forecast.get("casts", [])

                if casts:
                    # 格式化输出
                    result = f"**{city}未来天气预报**\n"
                    # 只取前3天的天气
                    for cast in casts[:3]:
                        result += f"\n- **日期**: {cast['date']}\n  天气: {cast['dayweather']}, 温度: {cast['daytemp']}°C"
                    return result
                else:
                    return f"未找到{city}的天气预报信息。"
            else:
                # API 返回错误
                return f"查询失败: {data.get('info', '未知错误')}"

        except Exception as e:
            # 捕获所有异常（网络错误、超时、解析错误等）
            return f"查询天气时发生错误: {str(e)}"


# ==================== 工具2：景点搜索 ====================
@mcp.tool()
async def search_attractions(city: str, keywords: str = "景点") -> str:
    """
    搜索指定城市的景点。

    Args:
        city: 城市名称，如 '北京'
        keywords: 搜索关键词，如 '景点'、'博物馆'
    """
    if not AMAP_API_KEY:
        return "错误: 未配置高德地图 API Key"

    # 高德 POI 搜索 API（Place of Interest，兴趣点）
    url = "https://restapi.amap.com/v3/place/text"

    params = {
        "keywords": keywords,       # 搜索关键词
        "city": city,               # 城市范围
        "key": AMAP_API_KEY,        # API 密钥
        "output": "json"            # 返回格式
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            data = response.json()

            if data.get("status") == "1":
                # 获取前5个结果
                pois = data.get("pois", [])[:5]

                if pois:
                    result = f"**{city}{keywords}推荐**\n"
                    for poi in pois:
                        result += f"\n- **{poi.get('name')}**\n  地址: {poi.get('address')}"

                        # 提取坐标信息（格式："经度,纬度"）
                        location = poi.get("location", "").split(",")
                        if len(location) == 2:
                            result += f"\n  坐标: {location[0]}, {location[1]}"
                    return result
                return f"未找到{city}的{keywords}信息。"
            return f"搜索失败: {data.get('info')}"
        except Exception as e:
            return f"搜索异常: {str(e)}"


# ==================== 工具3：酒店搜索 ====================
@mcp.tool()
async def search_hotels(city: str, keywords: str = "经济型酒店") -> str:
    """
    搜索指定城市的酒店。

    Args:
        city: 城市名称，如 '北京'
        keywords: 搜索关键词，如 '经济型酒店'、'豪华酒店'
    """
    if not AMAP_API_KEY:
        return "错误: 未配置高德地图 API Key"

    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "keywords": keywords,
        "city": city,
        "key": AMAP_API_KEY,
        "output": "json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            data = response.json()

            if data.get("status") == "1":
                pois = data.get("pois", [])[:5]
                if pois:
                    result = f"**{city}{keywords}推荐**\n"
                    for poi in pois:
                        result += f"\n- **{poi.get('name')}**\n  地址: {poi.get('address')}"
                    return result
                return f"未找到{city}的{keywords}信息。"
            return f"搜索失败: {data.get('info')}"
        except Exception as e:
            return f"搜索异常: {str(e)}"


# ==================== 工具4：驾车路线规划 ====================
@mcp.tool()
async def get_driving_route(origin: str, destination: str, waypoints: str = "") -> str:
    """
    获取驾车路线规划。

    Args:
        origin: 起点坐标，格式 "经度,纬度"
        destination: 终点坐标，格式 "经度,纬度"
        waypoints: 途经点（可选），格式 "经度,纬度|经度,纬度"
    """
    if not AMAP_API_KEY:
        # 返回 JSON 格式的错误，便于客户端解析
        return json.dumps({"error": "未配置高德地图 API Key"})

    # 高德驾车路线规划 API
    url = "https://restapi.amap.com/v3/direction/driving"

    params = {
        "key": AMAP_API_KEY,
        "origin": origin,               # 起点
        "destination": destination,     # 终点
        "extensions": "all"             # "all" 返回详细信息（距离、时间、步骤等）
    }
    if waypoints:
        params["waypoints"] = waypoints  # 途经点，用 | 分隔

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10.0)
            data = response.json()

            if data.get("status") == "1":
                route = data.get("route", {})
                paths = route.get("paths", [])
                if paths:
                    path = paths[0]  # 取第一条推荐路线
                    # 返回 JSON 格式的路线信息
                    return json.dumps({
                        "distance": int(path.get("distance", 0)),   # 距离（米）
                        "duration": int(path.get("duration", 0)),   # 时间（秒）
                        "steps": path.get("steps", [])              # 详细导航步骤
                    }, ensure_ascii=False)

            return json.dumps({"error": data.get("info", "规划失败")}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)


# ==================== 程序入口 ====================
if __name__ == "__main__":
    """
    启动 MCP 服务器
    
    transport='stdio' 表示使用标准输入输出进行通信：
    - 从 stdin 读取 JSON-RPC 请求
    - 将响应写入 stdout
    - stderr 用于日志输出
    
    父进程（supervisor.py）通过 subprocess 启动这个脚本，
    然后通过管道与它通信。
    """
    mcp.run(transport='stdio')