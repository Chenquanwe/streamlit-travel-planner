"""
行程规划 Agent - 负责整合所有信息生成完整的旅行计划

功能：接收景点、天气、酒店等所有信息，生成一个完整的、结构化的旅行计划。
这是多智能体系统中的"总指挥"，负责将各个专家 Agent 的输出整合成最终结果。

工作流程：
1. 接收所有输入信息（城市、日期、偏好、景点、天气、酒店）
2. 将信息组织成详细的提示词
3. 调用 LLM 生成结构化的 JSON 旅行计划
4. 返回 JSON 字符串供后续解析

与 BaseTravelAgent 的区别：
- 其他 Agent（景点、天气、酒店）需要调用工具获取数据
- 规划 Agent 不需要工具，只负责整合信息
"""

# ==================== 第三方库导入 ====================
# ChatOpenAI: LangChain 的 OpenAI 兼容接口，用于调用大语言模型
from langchain_openai import ChatOpenAI

# ==================== 项目内部导入 ====================
# BaseTravelAgent: 所有旅行Agent的基类
# 提供了 run() 方法等通用功能
from agents.base_agent import BaseTravelAgent


# ==================== Agent 提示词 ====================
# PLANNER_PROMPT 定义了行程规划专家的系统提示词
#
# 这个提示词非常关键，因为它：
# 1. 定义了输出格式（严格的 JSON）
# 2. 要求每个景点必须包含经纬度坐标（用于地图显示）
# 3. 提供了常用景点的坐标参考
# 4. 规定了每天安排2-3个景点
#
# 提示词结构：
# - 角色定义：行程规划专家
# - 职责描述：整合信息、生成行程、提供建议、估算预算
# - 输出格式：完整的 JSON 示例
# - 坐标参考：常用景点的经纬度
# - 注意事项：每天景点数量、必须包含坐标等
PLANNER_PROMPT = """你是行程规划专家，负责整合所有信息生成完整的旅行计划。

你的职责：
1. 整合景点、天气、酒店信息
2. 生成每日详细行程安排
3. 提供总体建议和预算估算

⚠️ 重要：每个景点必须包含经纬度坐标！

输出格式必须为严格的 JSON：

{
    "city": "城市名称",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "days": [
        {
            "date": "YYYY-MM-DD",
            "day_index": 0,
            "description": "当日行程描述",
            "transportation": "交通方式",
            "accommodation": "住宿类型",
            "attractions": [
                {
                    "name": "景点名称",
                    "address": "地址",
                    "location": {
                        "longitude": 116.397128,
                        "latitude": 39.916527
                    },
                    "visit_duration": 120,
                    "ticket_price": 60,
                    "description": "景点描述"
                }
            ],
            "hotel": {
                "name": "酒店名称",
                "address": "酒店地址",
                "estimated_cost": 300
            }
        }
    ],
    "weather_info": [
        {
            "date": "YYYY-MM-DD",
            "day_weather": "晴",
            "night_weather": "多云",
            "day_temp": 25,
            "night_temp": 15
        }
    ],
    "overall_suggestions": "总体建议和注意事项",
    "budget": {
        "total_attractions": 180,
        "total_hotels": 600,
        "total_meals": 300,
        "total_transportation": 100,
        "total": 1180
    }
}

坐标参考（常用景点）：
- 南京中山陵: 118.850, 32.060
- 南京明孝陵: 118.845, 32.058
- 南京夫子庙: 118.785, 32.018
- 南京博物院: 118.815, 32.042
- 南京总统府: 118.795, 32.045
- 郑州商城遗址: 113.685, 34.755
- 郑州博物馆: 113.635, 34.755
- 大河村遗址: 113.755, 34.825

注意事项：
- 每天安排2-3个景点
- 每个景点必须有 location 字段
- 坐标使用百度或高德坐标系即可
- 根据预算提供合理的费用估算
"""


# ==================== 行程规划 Agent 类 ====================
class PlannerAgent(BaseTravelAgent):
    """
    行程规划 Agent

    职责：整合所有信息，生成完整的 JSON 格式旅行计划

    特点：
    - 不需要工具（tools=[]）
    - 只依赖 LLM 的推理能力
    - 输出严格的 JSON 格式
    - 需要确保每个景点都有坐标

    与其他 Agent 的区别：
    - AttractionSearchAgent：搜索景点（需要工具）
    - WeatherQueryAgent：查询天气（需要工具）
    - HotelAgent：推荐酒店（需要工具）
    - PlannerAgent：整合信息（不需要工具）

    使用示例：
        agent = PlannerAgent(llm, verbose=True)
        result = agent.plan(
            city="南京",
            start_date="2026-04-27",
            end_date="2026-04-29",
            days=3,
            preferences="历史文化",
            budget_level="中等",
            transportation="公共交通",
            accommodation="经济型酒店",
            attractions_info="景点列表...",
            weather_info="天气信息...",
            hotels_info="酒店列表..."
        )
        # result 是 JSON 字符串，需要进一步解析
    """

    def __init__(self, llm: ChatOpenAI, verbose: bool = True):
        """
        初始化行程规划 Agent

        Args:
            llm: 大语言模型实例
                推荐使用能力较强的模型（如 qwen-max、gpt-4）
                因为生成 JSON 格式需要较强的推理能力
            verbose: 是否打印详细日志
                设为 True 时会打印 LLM 的输出，便于调试 JSON 格式问题
        """
        # 行程规划 Agent 不需要工具
        # 因为它的任务不是获取数据，而是整合已有的数据
        tools = []

        # 调用父类初始化方法
        super().__init__(
            name="行程规划专家",           # Agent 名称
            system_prompt=PLANNER_PROMPT,  # 系统提示词（包含 JSON 格式要求）
            llm=llm,                      # 大语言模型实例
            tools=tools,                  # 工具列表（空）
            verbose=verbose               # 是否打印详细日志
        )

    def plan(
        self,
        city: str,
        start_date: str,
        end_date: str,
        days: int,
        preferences: str,
        budget_level: str,
        transportation: str,
        accommodation: str,
        attractions_info: str,
        weather_info: str,
        hotels_info: str
    ) -> str:
        """
        生成行程计划 - 主要的对外接口

        这是整个多智能体系统的核心方法，负责将分散的信息整合成完整的旅行计划。

        Args:
            city: 目的地城市名称
            start_date: 开始日期（格式：YYYY-MM-DD）
            end_date: 结束日期（格式：YYYY-MM-DD）
            days: 旅行天数
            preferences: 旅行偏好（历史文化、自然风光、美食购物等）
            budget_level: 预算级别（经济型、中等、舒适型、豪华型）
            transportation: 交通方式（公共交通、自驾、打车等）
            accommodation: 住宿类型（经济型酒店、舒适型酒店等）
            attractions_info: 景点信息（来自 AttractionSearchAgent）
            weather_info: 天气信息（来自 WeatherQueryAgent）
            hotels_info: 酒店信息（来自 HotelAgent）

        Returns:
            str: JSON 格式的旅行计划字符串
                格式见 PLANNER_PROMPT 中的示例
                需要由调用方（supervisor）进一步解析为 TripPlan 对象

        提示词构建策略：
            1. 将用户的基本信息（城市、日期、偏好等）组织成结构化格式
            2. 附加景点、天气、酒店信息
            3. 强调 JSON 格式要求和坐标要求
            4. 返回 JSON 字符串
        """
        # 构建详细的查询字符串
        # 使用多行字符串和三引号保持可读性
        # 结构：
        #   - 基本信息（城市、日期、天数等）
        #   - 景点信息（从 AttractionSearchAgent 获取）
        #   - 天气信息（从 WeatherQueryAgent 获取）
        #   - 酒店信息（从 HotelAgent 获取）
        #   - 特殊要求（必须包含坐标）
        query = f"""
请根据以下信息生成{city}的{days}日旅行计划：

**基本信息：**
- 目的地: {city}
- 日期: {start_date} 至 {end_date}
- 天数: {days}天
- 偏好: {preferences}
- 预算级别: {budget_level}
- 交通方式: {transportation}
- 住宿类型: {accommodation}

**景点信息：**
{attractions_info}

**天气信息：**
{weather_info}

**酒店信息：**
{hotels_info}

⚠️ 请确保每个景点都包含 location 经纬度坐标！
"""

        # 调用父类的 run() 方法执行 Agent
        # run() 方法会：
        # 1. 构建消息（system_prompt + user_query）
        # 2. 调用 LLM 获取响应
        # 3. 由于没有工具，LLM 会直接返回 JSON 格式的答案
        # 4. 返回 JSON 字符串
        return self.run(query)