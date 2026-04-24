"""
监督者 - 多智能体系统的总协调器

这是整个旅行规划系统的核心控制器，负责：
1. 协调各个专家 Agent 的执行顺序
2. 管理 MCP 模式（Model Context Protocol）和普通模式的切换
3. 整合各个 Agent 的输出结果
4. 计算景点间的路线距离
5. 解析 JSON 结果并构建 TripPlan 对象

设计模式：监督者模式（Supervisor Pattern）
- 监督者（本类）负责协调多个子 Agent
- 子 Agent 各司其职，互不依赖
- 监督者控制执行流程和错误处理
"""

import json
import logging
import os
import asyncio
import concurrent.futures
from typing import Optional, List

from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from models.schemas import (
    TripRequest, TripPlan, Attraction, WeatherInfo,
    Hotel, DayPlan, Budget, RouteInfo, RoutePoint, Location
)
from agents.planner_agent import PlannerAgent
from services.image_service import enrich_attractions_with_images
from tools.amap_tools import get_amap_service

logger = logging.getLogger(__name__)


class TravelSupervisor:
    """
    旅行规划监督者

    这是多智能体系统的总控制器，负责：
    - 初始化各个子 Agent（景点搜索、天气查询、酒店推荐）
    - 按顺序执行规划流程（搜索景点 → 查询天气 → 推荐酒店 → 生成计划）
    - 计算景点间的驾车路线
    - 为缺少坐标的景点补充坐标
    - 为景点添加图片
    - 解析 LLM 返回的 JSON 并构建结构化的 TripPlan 对象

    执行流程：
    ┌─────────────────────────────────────────────────────────────┐
    │                    plan_trip(request)                       │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │ 步骤1: 搜索景点                 │
              │ AttractionSearchAgent.search() │
              └───────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │ 步骤2: 查询天气                 │
              │ WeatherQueryAgent.query()      │
              └───────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │ 步骤3: 推荐酒店                 │
              │ HotelAgent.recommend()         │
              └───────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │ 步骤4: 生成行程计划             │
              │ PlannerAgent.plan()            │
              └───────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │ 步骤5: 解析 JSON               │
              │ _parse_plan_result()           │
              └───────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │ 步骤6: 补充坐标（如需要）       │
              │ _get_location_from_api()       │
              └───────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │ 步骤7: 计算路线                 │
              │ _calculate_daily_routes()      │
              └───────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │ 步骤8: 添加图片                 │
              │ enrich_attractions_with_images│
              └───────────────────────────────┘
                              │
                              ▼
                         TripPlan 对象
    """

    def __init__(self, llm: ChatOpenAI, verbose: bool = True, use_mcp: bool = False):
        """
        初始化监督者

        Args:
            llm: 大语言模型实例
                用于所有子 Agent 的 LLM 调用
            verbose: 是否打印详细日志
                设为 True 时会打印每个 Agent 的执行过程
            use_mcp: 是否使用 MCP 模式
                True: 使用 MCP 协议调用工具（更标准化）
                False: 使用普通 Agent 模式（直接调用工具函数）
        """
        # 基础属性
        self.llm = llm
        self.verbose = verbose
        self.use_mcp = use_mcp

        # MCP 相关属性（仅 MCP 模式使用）
        self.mcp_client = None      # MCP 客户端实例
        self.mcp_tools = []          # 从 MCP 服务器获取的工具列表

        # 普通模式 Agent（仅普通模式使用）
        self.attraction_agent = None  # 景点搜索 Agent
        self.weather_agent = None     # 天气查询 Agent
        self.hotel_agent = None       # 酒店推荐 Agent

        # 根据模式初始化
        if use_mcp:
            self._init_mcp_mode()
        else:
            self._init_agent_mode()

        # 行程规划 Agent（两种模式都需要）
        # 这个 Agent 不需要工具，只负责整合信息
        self.planner_agent = PlannerAgent(llm, verbose)

        logger.info(f"多智能体系统初始化完成，模式: {'MCP' if use_mcp else '普通Agent'}")

    def _run_async(self, coro):
        """
        安全地运行异步协程

        这是一个辅助方法，用于在同步函数中调用异步代码。
        因为 MCP 客户端的方法是异步的，但 __init__ 是同步的，
        所以需要这个方法作为桥梁。

        为什么要这么复杂？
        - 情况1：当前没有运行中的事件循环 → 直接运行
        - 情况2：当前有运行中的事件循环 → 不能嵌套运行，需要用线程池

        Args:
            coro: 协程对象（async 函数的返回值）

        Returns:
            协程执行结果

        示例：
            # 在同步函数中调用异步方法
            result = self._run_async(self.mcp_client.get_tools())
        """
        try:
            # 尝试获取当前正在运行的事件循环
            # 如果当前已经在异步环境中（比如另一个 async 函数内部），
            # 这个调用会成功返回当前的事件循环
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 如果抛出 RuntimeError，说明当前不在异步环境中
            # 也就是说，我们是在普通的同步函数中
            # 此时可以直接用 asyncio.run() 来运行协程
            # asyncio.run() 会创建新的事件循环、运行协程、然后关闭循环
            return asyncio.run(coro)

        # 如果执行到这里，说明已经在异步环境中了
        # 但是 asyncio.run() 不能在已有事件循环的环境中再次调用
        # 否则会报错：RuntimeError: asyncio.run() cannot be called from a running event loop

        # 解决方案：使用线程池
        # 创建一个新的线程，在新线程中运行新的事件循环
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # executor.submit() 会在线程池中执行一个函数
            # 这里我们执行 asyncio.run(coro)，它会在新线程中创建新的事件循环
            future = executor.submit(asyncio.run, coro)
            # future.result() 等待线程执行完成并获取结果
            return future.result()

    def _init_mcp_mode(self):
        """
        初始化 MCP 模式

        MCP（Model Context Protocol）是一种标准化协议，
        让 AI 应用能够发现和调用外部工具。

        工作流程：
        1. 读取高德 API Key
        2. 定位 MCP 服务器文件
        3. 创建 MCP 客户端（启动子进程）
        4. 获取工具列表
        5. 如果失败，回退到普通模式
        """

        # ----- 步骤1：读取并设置 API Key -----
        # 从环境变量读取高德 API Key
        api_key = os.getenv("AMAP_API_KEY")
        if not api_key:
            logger.warning("AMAP_API_KEY 未配置")
        else:
            # 设置环境变量，确保子进程能继承
            # 子进程启动时会继承父进程的环境变量
            os.environ["AMAP_API_KEY"] = api_key

        # ----- 步骤2：定位 MCP 服务器文件 -----
        # __file__ 是当前文件的完整路径
        # 例如：D:\project\agents\supervisor.py

        # os.path.dirname() 获取父目录
        # 第一次调用：D:\project\agents
        # 第二次调用：D:\project（项目根目录）
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # 拼接路径：项目根目录 + "amap_mcp_server.py"
        # 结果：D:\project\amap_mcp_server.py
        server_path = os.path.join(current_dir, "amap_mcp_server.py")

        # 检查 MCP 服务器文件是否存在
        if not os.path.exists(server_path):
            logger.error(f"MCP 服务器文件不存在: {server_path}")
            # 文件不存在，回退到普通模式
            self._init_agent_mode()
            self.use_mcp = False
            return

        # ----- 步骤3：创建 MCP 客户端 -----
        # MultiServerMCPClient 是 LangChain 官方提供的 MCP 客户端
        # 它会：
        # 1. 启动子进程：python -u amap_mcp_server.py
        # 2. 建立 stdio 管道（标准输入输出）
        # 3. 自动处理 JSON-RPC 消息的发送和接收
        self.mcp_client = MultiServerMCPClient({
            "amap": {  # 服务器名称
                "transport": "stdio",  # 传输方式：标准输入输出
                "command": "python",  # 启动命令
                "args": ["-u", server_path],  # 参数：-u 禁用输出缓冲
                "env": {  # 子进程的环境变量
                    "AMAP_API_KEY": api_key  # 直接传递 API Key
                }
            }
        })

        # ----- 步骤4：获取工具列表 -----
        try:
            # 创建新的事件循环（因为 __init__ 是同步方法）
            # 不能直接 await，所以需要创建临时的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 运行异步方法获取工具
            # _get_tools_async() 会向 MCP 服务器发送 "tools/list" 请求
            # 服务器返回所有 @mcp.tool() 装饰的函数
            self.mcp_tools = loop.run_until_complete(self._get_tools_async())
            loop.close()
        except Exception as e:
            logger.error(f"获取 MCP 工具失败: {e}")
            self.mcp_tools = []

        # ----- 步骤5：打印工具信息 -----
        tool_names = [tool.name for tool in self.mcp_tools]
        logger.info(f"MCP 模式初始化完成，获取到 {len(self.mcp_tools)} 个工具: {tool_names}")

        # ----- 步骤6：如果失败，回退到普通模式 -----
        if not self.mcp_tools:
            logger.warning("未获取到 MCP 工具，回退到普通模式")
            self._init_agent_mode()
            self.use_mcp = False

    async def _get_tools_async(self):
        """
        异步获取 MCP 工具列表

        这个方法会向 MCP 服务器发送 "tools/list" 请求，
        服务器返回所有注册的工具。

        通信过程：
        客户端发送 → {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
        服务器返回 → {"jsonrpc": "2.0", "result": {"tools": [...]}, "id": 1}

        Returns:
            List: 从 MCP 服务器获取的工具列表
                  每个工具是一个 LangChain Tool 对象
        """
        if self.mcp_client:
            # get_tools() 是异步方法，需要 await
            # 它会自动处理 JSON-RPC 通信
            return await self.mcp_client.get_tools()
        return []

    def _init_agent_mode(self):
        """
        初始化普通 Agent 模式

        创建三个专家 Agent：
        1. AttractionSearchAgent - 景点搜索
        2. WeatherQueryAgent - 天气查询
        3. HotelAgent - 酒店推荐
        """
        from agents.attraction_agent import AttractionSearchAgent
        from agents.weather_agent import WeatherQueryAgent
        from agents.hotel_agent import HotelAgent

        # 创建景点搜索 Agent
        self.attraction_agent = AttractionSearchAgent(self.llm, self.verbose)

        # 创建天气查询 Agent
        self.weather_agent = WeatherQueryAgent(self.llm, self.verbose)

        # 创建酒店推荐 Agent
        self.hotel_agent = HotelAgent(self.llm, self.verbose)

        logger.info("普通 Agent 模式初始化完成")

    def plan_trip(self, request: TripRequest, progress_callback=None) -> Optional[TripPlan]:
        """
        执行旅行规划 - 主要对外接口

        Args:
            request: 用户请求对象
            progress_callback: 进度回调函数，接收 (step_index, step_name) 参数

        Returns:
            TripPlan: 完整的旅行计划对象
        """
        try:
            # 打印开始信息
            print("\n" + "=" * 60)
            print(f"🚀 开始多智能体协作规划旅行...")
            print(f"目的地: {request.city}")
            print(f"日期: {request.start_date} 至 {request.end_date}")
            print(f"天数: {request.days}天")
            print(f"偏好: {request.preferences}")
            print(f"模式: {'MCP' if self.use_mcp else '普通Agent'}")
            print("=" * 60)

            # 根据模式执行规划，传入回调
            if self.use_mcp:
                result = self._plan_with_mcp(request, progress_callback)
            else:
                result = self._plan_with_agents(request, progress_callback)

            if result:
                result = self._calculate_daily_routes(result)
                print("\n" + "=" * 60)
                print("✅ 旅行计划生成完成!")
                print("=" * 60)

            return result

        except Exception as e:
            logger.error(f"旅行规划失败: {e}")
            print(f"❌ 生成旅行计划失败: {e}")
            return None

    def _plan_with_mcp(self, request: TripRequest, progress_callback=None) -> Optional[TripPlan]:
        """使用 MCP 模式规划"""

        if not self.mcp_tools:
            logger.error("MCP 工具未初始化，回退到普通模式")
            return self._plan_with_agents(request, progress_callback)

        tools_dict = {tool.name: tool for tool in self.mcp_tools}

        # 步骤1: 搜索景点
        if progress_callback:
            progress_callback(0, "🔍 正在搜索景点...")
        print("\n📍 步骤1: 搜索景点...")
        if "search_attractions" in tools_dict:
            try:
                result = self._run_async(
                    tools_dict["search_attractions"].ainvoke({
                        "city": request.city,
                        "keywords": request.preferences
                    })
                )
                attractions_result = str(result)
            except Exception as e:
                print(f"景点搜索失败: {e}")
                attractions_result = f"搜索{request.city}的{request.preferences}景点失败"
        else:
            attractions_result = "未找到搜索景点的工具"
        print(f"景点搜索结果: {attractions_result[:200]}...")

        # 步骤2: 查询天气
        if progress_callback:
            progress_callback(1, "🌤️ 正在查询天气...")
        print("\n🌤️ 步骤2: 查询天气...")
        if "get_weather" in tools_dict:
            try:
                result = self._run_async(
                    tools_dict["get_weather"].ainvoke({"city": request.city})
                )
                weather_result = str(result)
            except Exception as e:
                print(f"天气查询失败: {e}")
                weather_result = f"查询{request.city}天气失败"
        else:
            weather_result = "未找到查询天气的工具"
        print(f"天气查询结果: {weather_result[:200]}...")

        # 步骤3: 搜索酒店
        if progress_callback:
            progress_callback(2, "🏨 正在推荐酒店...")
        print("\n🏨 步骤3: 搜索酒店...")
        if "search_hotels" in tools_dict:
            try:
                result = self._run_async(
                    tools_dict["search_hotels"].ainvoke({
                        "city": request.city,
                        "keywords": request.accommodation
                    })
                )
                hotel_result = str(result)
            except Exception as e:
                print(f"酒店搜索失败: {e}")
                hotel_result = f"搜索{request.city}的{request.accommodation}酒店失败"
        else:
            hotel_result = "未找到搜索酒店的工具"
        print(f"酒店搜索结果: {hotel_result[:200]}...")

        # 步骤4: 生成行程计划
        if progress_callback:
            progress_callback(3, "📋 正在生成行程计划...")
        print("\n📋 步骤4: 生成行程计划...")
        plan_result = self.planner_agent.plan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=request.days,
            preferences=request.preferences,
            budget_level=request.budget,
            transportation=request.transportation,
            accommodation=request.accommodation,
            attractions_info=attractions_result,
            weather_info=weather_result,
            hotels_info=hotel_result
        )

        return self._parse_plan_result(plan_result, request)

    def _plan_with_agents(self, request: TripRequest, progress_callback=None) -> Optional[TripPlan]:
        """
        使用普通 Agent 模式规划
        """
        # ----- 步骤1: 搜索景点 -----
        if progress_callback:
            progress_callback(0, "🔍 正在搜索景点...")
        print("\n📍 步骤1: 搜索景点...")
        attractions_result = self.attraction_agent.search(request.city, request.preferences)
        print(f"景点搜索结果: {attractions_result[:200]}...")

        # ----- 步骤2: 查询天气 -----
        if progress_callback:
            progress_callback(1, "🌤️ 正在查询天气...")
        print("\n🌤️ 步骤2: 查询天气...")
        weather_result = self.weather_agent.query(request.city)
        print(f"天气查询结果: {weather_result[:200]}...")

        # ----- 步骤3: 搜索酒店 -----
        if progress_callback:
            progress_callback(2, "🏨 正在推荐酒店...")
        print("\n🏨 步骤3: 搜索酒店...")
        hotel_result = self.hotel_agent.recommend(request.city, request.accommodation)
        print(f"酒店搜索结果: {hotel_result[:200]}...")

        # ----- 步骤4: 生成行程计划 -----
        if progress_callback:
            progress_callback(3, "📋 正在生成行程计划...")
        print("\n📋 步骤4: 生成行程计划...")
        plan_result = self.planner_agent.plan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=request.days,
            preferences=request.preferences,
            budget_level=request.budget,
            transportation=request.transportation,
            accommodation=request.accommodation,
            attractions_info=attractions_result,
            weather_info=weather_result,
            hotels_info=hotel_result
        )

        return self._parse_plan_result(plan_result, request)



    def _calculate_daily_routes(self, trip_plan: TripPlan) -> TripPlan:
        """
        计算每日景点间的驾车路线

        为每天的行程计算景点之间的驾车距离和时间，
        并将路线信息保存到 DayPlan.route 中。

        Args:
            trip_plan: 旅行计划对象

        Returns:
            TripPlan: 添加了路线信息后的旅行计划对象
        """
        amap_service = get_amap_service()

        for day in trip_plan.days:
            attractions = day.attractions
            if len(attractions) < 2:
                continue

            # 筛选有坐标的景点
            valid_attractions = []
            for attr in attractions:
                if attr.location and attr.location.longitude and attr.location.latitude:
                    valid_attractions.append(attr)

            if len(valid_attractions) < 2:
                continue

            # 计算从第一个景点到最后一个景点的路线
            start = valid_attractions[0]
            end = valid_attractions[-1]

            start_coord = f"{start.location.longitude},{start.location.latitude}"
            end_coord = f"{end.location.longitude},{end.location.latitude}"

            # 构建途经点（中间景点）
            waypoints_list = []
            for attr in valid_attractions[1:-1]:
                waypoints_list.append(f"{attr.location.longitude},{attr.location.latitude}")
            waypoints = "|".join(waypoints_list) if waypoints_list else ""

            # 调用高德 API 获取路线
            result = amap_service.get_driving_route(start_coord, end_coord, waypoints)

            if "error" not in result:
                route = RouteInfo(
                    start=RoutePoint(
                        longitude=start.location.longitude,
                        latitude=start.location.latitude,
                        name=start.name
                    ),
                    end=RoutePoint(
                        longitude=end.location.longitude,
                        latitude=end.location.latitude,
                        name=end.name
                    ),
                    waypoints=[
                        RoutePoint(
                            longitude=attr.location.longitude,
                            latitude=attr.location.latitude,
                            name=attr.name
                        ) for attr in valid_attractions[1:-1]
                    ],
                    distance=result.get("distance", 0),
                    duration=result.get("duration", 0)
                )
                day.route = route

                print(f"  📍 第{day.day_index + 1}天路线: {result.get('distance', 0)/1000:.1f}km, {result.get('duration', 0)/60:.0f}分钟")

        return trip_plan

    def _parse_plan_result(self, result: str, request: TripRequest) -> Optional[TripPlan]:
        """
        解析 Agent 返回的 JSON 结果

        将 LLM 返回的 JSON 字符串解析为结构化的 TripPlan 对象。

        Args:
            result: LLM 返回的 JSON 字符串
            request: 原始请求对象

        Returns:
            TripPlan: 解析后的旅行计划对象
        """
        try:
            # 提取 JSON 内容（去除 markdown 代码块标记）
            if "```json" in result:
                start = result.find("```json") + 7
                end = result.find("```", start)
                json_str = result[start:end]
            elif "```" in result:
                start = result.find("```") + 3
                end = result.find("```", start)
                json_str = result[start:end]
            else:
                json_str = result

            json_str = json_str.strip()
            data = json.loads(json_str)

            # 解析每日行程
            days = []
            for day_data in data.get("days", []):
                attractions = []
                for attr_data in day_data.get("attractions", []):
                    loc_data = attr_data.get("location", {})
                    location = None

                    # 优先使用 LLM 提供的坐标
                    if loc_data.get("longitude") and loc_data.get("latitude"):
                        location = Location(
                            longitude=loc_data.get("longitude"),
                            latitude=loc_data.get("latitude")
                        )
                    else:
                        # 没有坐标时，通过 API 补全
                        location = self._get_location_from_api(
                            attr_data.get("name", ""),
                            request.city
                        )
                        if location:
                            print(f"  🔍 补全坐标: {attr_data.get('name')} -> {location.longitude}, {location.latitude}")

                    attractions.append(Attraction(
                        name=attr_data.get("name", ""),
                        address=attr_data.get("address", ""),
                        location=location,
                        visit_duration=attr_data.get("visit_duration", 120),
                        description=attr_data.get("description", ""),
                        ticket_price=attr_data.get("ticket_price", 0)
                    ))

                # 解析酒店信息
                hotel_data = day_data.get("hotel")
                hotel = Hotel(
                    name=hotel_data.get("name", ""),
                    address=hotel_data.get("address", ""),
                    estimated_cost=hotel_data.get("estimated_cost", 0)
                ) if hotel_data else None

                days.append(DayPlan(
                    date=day_data.get("date", ""),
                    day_index=day_data.get("day_index", 0),
                    description=day_data.get("description", ""),
                    transportation=day_data.get("transportation", request.transportation),
                    accommodation=day_data.get("accommodation", request.accommodation),
                    hotel=hotel,
                    attractions=attractions
                ))

            # 解析天气信息
            weather_info = []
            for w_data in data.get("weather_info", []):
                weather_info.append(WeatherInfo(
                    date=w_data.get("date", ""),
                    day_weather=w_data.get("day_weather", ""),
                    night_weather=w_data.get("night_weather", ""),
                    day_temp=w_data.get("day_temp", 0),
                    night_temp=w_data.get("night_temp", 0),
                    wind_direction=w_data.get("wind_direction", ""),
                    wind_power=w_data.get("wind_power", "")
                ))

            # 解析预算信息
            budget_data = data.get("budget", {})
            budget = Budget(
                total_attractions=budget_data.get("total_attractions", 0),
                total_hotels=budget_data.get("total_hotels", 0),
                total_meals=budget_data.get("total_meals", 0),
                total_transportation=budget_data.get("total_transportation", 0),
                total=budget_data.get("total", 0)
            ) if budget_data else None

            # 构建最终对象
            trip_plan = TripPlan(
                city=data.get("city", request.city),
                start_date=data.get("start_date", request.start_date),
                end_date=data.get("end_date", request.end_date),
                days=days,
                weather_info=weather_info,
                overall_suggestions=data.get("overall_suggestions", ""),
                budget=budget
            )

            # 添加景点图片
            trip_plan = enrich_attractions_with_images(trip_plan)
            return trip_plan

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return self._create_fallback_plan(request)

    def _create_fallback_plan(self, request: TripRequest) -> TripPlan:
        """
        创建备用计划

        当 JSON 解析失败时，返回一个基本的旅行计划。

        Args:
            request: 原始请求对象

        Returns:
            TripPlan: 备用计划对象
        """
        return TripPlan(
            city=request.city,
            start_date=request.start_date,
            end_date=request.end_date,
            days=[],
            weather_info=[],
            overall_suggestions=f"为您规划的{request.city}{request.days}日游行程。建议提前查看景点开放时间和天气情况。",
            budget=None
        )

    def __del__(self):
        """析构函数，关闭 MCP 客户端（如果已初始化）"""
        if hasattr(self, 'mcp_client') and self.mcp_client:
            try:
                if hasattr(self.mcp_client, '__aexit__'):
                    try:
                        loop = asyncio.new_event_loop()
                        loop.run_until_complete(self.mcp_client.__aexit__(None, None, None))
                        loop.close()
                    except:
                        pass
            except:
                pass

    """
    第1次运行 → 启动子进程 PID=100
    第2次运行 → 启动子进程 PID=101（旧进程 PID=100 还在！）
    第3次运行 → 启动子进程 PID=102（旧进程 PID=100、101 还在！）
    ...
    最终：大量僵尸进程，消耗系统资源
    普通对象	不用管	Python 自动回收
    文件操作	用 with open()	自动关闭
    MCP 子进程	写 __del__ 或使用上下文管理器	确保子进程终止
    """
