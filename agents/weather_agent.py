"""
天气查询 Agent - 负责查询指定城市的天气预报

功能：根据用户输入的城市名称，使用高德地图天气 API 查询实时天气和未来天气预报。
返回格式化的天气信息，包括日期、天气状况、温度等。

工作流程：
1. 接收城市名称
2. 调用高德地图天气 API
3. 解析返回的天气数据
4. 返回格式化的天气预报

API 说明：
- 高德天气 API 支持实时天气和未来天气预报
- 实时天气：返回当前温度、湿度、风向等
- 未来天气：返回未来几天的天气预报
"""

# ==================== 第三方库导入 ====================
# ChatOpenAI: LangChain 的 OpenAI 兼容接口，用于调用大语言模型
# 支持阿里云百炼、OpenAI、智谱等兼容 OpenAI API 的模型
from langchain_openai import ChatOpenAI

# ==================== 项目内部导入 ====================
# BaseTravelAgent: 所有旅行Agent的基类
# 提供了 run() 方法、工具调用、消息管理等通用功能
from agents.base_agent import BaseTravelAgent

# query_weather: 高德地图天气查询工具
# 这是一个 LangChain Tool，实际调用高德地图 API 获取天气信息
# 输入参数：city（城市名称）
# 返回：格式化的天气预报字符串
from tools.amap_tools import query_weather


# ==================== Agent 提示词 ====================
# WEATHER_PROMPT 定义了天气查询专家的系统提示词
# 这个提示词会被注入到 LLM 的 system message 中，
# 指导 LLM 如何使用工具和处理用户请求
#
# 提示词结构说明：
# 1. 角色定义：明确 Agent 的身份是"天气查询专家"
# 2. 职责描述：说明 Agent 需要完成的任务（查询指定城市的天气预报）
# 3. 工具说明：指明要使用的 query_weather 工具
# 4. 约束条件：强调必须使用工具查询，不能编造信息
# 5. 输出要求：规定返回结果应包含日期、天气状况、温度等信息
WEATHER_PROMPT = """你是一个天气查询专家。

你的职责：
1. 查询指定城市的天气预报
2. 使用 query_weather 工具获取天气信息
3. 返回未来几天的天气情况

注意事项：
- 必须使用工具查询，不要编造天气信息
- 返回结果应包含日期、天气状况、温度等信息
"""


# ==================== 天气查询 Agent 类 ====================
class WeatherQueryAgent(BaseTravelAgent):
    """
    天气查询 Agent

    职责：根据用户输入的城市名称，查询并返回该城市的天气预报

    继承自 BaseTravelAgent，获得以下能力：
    - run() 方法：执行 Agent 任务
    - 工具调用机制：自动解析 [TOOL_CALL:...] 格式并调用工具
    - 多轮对话管理：维护消息历史

    使用示例：
        agent = WeatherQueryAgent(llm, verbose=True)
        result = agent.query("南京")
        print(result)  # 输出格式化的天气预报

    返回格式示例：
        "南京未来天气：
         📅 2026-04-27: 晴 25°C
         📅 2026-04-28: 多云 22°C
         📅 2026-04-29: 小雨 18°C"
    """

    def __init__(self, llm: ChatOpenAI, verbose: bool = True):
        """
        初始化天气查询 Agent

        Args:
            llm: 大语言模型实例
                可以是 OpenAI、阿里云百炼、智谱等兼容 OpenAI API 的模型
            verbose: 是否打印详细日志
                设为 True 时会打印 Agent 的思考和工具调用过程，
                便于调试和理解 Agent 的工作流程
        """
        # 准备工具列表 - 天气查询只需要一个工具
        # query_weather 是一个 @tool 装饰的函数，已被包装成 LangChain Tool
        # 该工具接受 city 参数，返回格式化的天气预报字符串
        tools = [query_weather]

        # 调用父类初始化方法
        # 父类会完成以下工作：
        # 1. 保存 llm、tools、verbose 等属性
        # 2. 将工具列表转换为字典（工具名 → 工具对象）
        # 3. 保存系统提示词
        super().__init__(
            name="天气查询专家",           # Agent 名称，用于日志和提示词
            system_prompt=WEATHER_PROMPT,  # 系统提示词，定义 Agent 行为
            llm=llm,                      # 大语言模型实例
            tools=tools,                  # 可用工具列表
            verbose=verbose               # 是否打印详细日志
        )

    def query(self, city: str) -> str:
        """
        查询天气 - 主要的对外接口

        Args:
            city: 城市名称
                例如："北京"、"上海"、"南京"
                支持中国主要城市的中文名称

        Returns:
            str: 格式化的天气预报字符串
                格式示例：
                "南京未来天气：
                 📅 2026-04-27: 晴 25°C
                 📅 2026-04-28: 多云 22°C
                 📅 2026-04-29: 小雨 18°C"

        工作流程：
            1. 根据参数构建查询字符串
            2. 调用父类的 run() 方法执行 Agent
            3. run() 内部会：
               - 将查询发送给 LLM
               - LLM 决定是否需要调用 query_weather 工具
               - 执行工具并将结果返回给 LLM
               - LLM 格式化结果后返回

        注意：
            - 实际查询是由 query_weather 工具完成的
            - LLM 的作用是理解用户意图并格式化输出
            - 工具会调用高德天气 API 获取真实数据
        """
        # 构建查询字符串
        # 查询格式：要求 Agent 查询指定城市未来几天的天气预报
        # LLM 会理解这个请求，并决定何时调用 query_weather 工具
        #
        # 示例：
        #   city="南京"
        #   → "请查询南京未来几天的天气预报，包括日期、天气状况和温度。"
        query = f"请查询{city}未来几天的天气预报，包括日期、天气状况和温度。"

        # 调用父类的 run() 方法执行 Agent
        # run() 方法会：
        # 1. 构建消息（system_prompt + user_query）
        # 2. 调用 LLM 获取响应
        # 3. 如果响应中包含 [TOOL_CALL:...] 标记，解析并执行工具
        # 4. 将工具结果返回给 LLM，继续对话
        # 5. 重复直到 LLM 不再调用工具，返回最终答案
        return self.run(query)