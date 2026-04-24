"""
景点搜索 Agent - 负责搜索指定城市的景点信息

功能：根据用户输入的城市和偏好（如历史文化、自然风光等），
使用高德地图API搜索相关景点，返回格式化的景点列表。

工作流程：
1. 接收城市名称和偏好类型
2. 调用高德地图POI搜索API
3. 解析返回的景点数据（名称、地址、坐标、类型）
4. 返回格式化的景点列表
"""

# ==================== 第三方库导入 ====================
# ChatOpenAI: LangChain 的 OpenAI 兼容接口，用于调用大语言模型
# 支持阿里云百炼、OpenAI 等多种 API
from langchain_openai import ChatOpenAI

# BaseTool: LangChain 工具基类，定义了工具的基本接口
# 用于类型注解，表示工具列表的类型
from langchain.tools import BaseTool

# ==================== 项目内部导入 ====================
# BaseTravelAgent: 所有旅行Agent的基类
# 提供了 run() 方法、工具调用、消息管理等通用功能
from agents.base_agent import BaseTravelAgent

# search_attractions: 高德地图景点搜索工具
# 这是一个 LangChain Tool，实际调用高德地图 API 进行 POI 搜索
# 输入参数：city(城市), preferences(偏好)
# 返回：JSON格式的景点列表
from tools.amap_tools import search_attractions


# ==================== Agent 提示词 ====================
# ATTRACTION_PROMPT 定义了景点搜索专家的系统提示词
# 这个提示词会被注入到 LLM 的 system message 中，
# 指导 LLM 如何使用工具和处理用户请求
#
# 提示词结构说明：
# 1. 角色定义：明确 Agent 的身份是"景点搜索专家"
# 2. 职责描述：说明 Agent 需要完成的任务
# 3. 工具说明：指明要使用的工具和调用方式
# 4. 约束条件：强调必须使用工具，不能编造信息
# 5. 输出要求：规定返回结果的格式
ATTRACTION_PROMPT = """你是一个景点搜索专家。

你的职责：
1. 根据用户偏好的城市和兴趣，搜索合适的景点
2. 使用 search_attractions 工具获取景点信息
3. 返回格式化的景点列表

注意事项：
- 必须使用工具搜索，不要编造景点信息
- 根据偏好调整搜索关键词
- 返回结果应包含景点名称、地址、类型等信息
"""


# ==================== 景点搜索 Agent 类 ====================
class AttractionSearchAgent(BaseTravelAgent):
    """
    景点搜索 Agent

    职责：根据用户输入的城市和偏好，搜索并返回相关景点信息

    继承自 BaseTravelAgent，获得以下能力：
    - run() 方法：执行 Agent 任务
    - 工具调用机制：自动解析 [TOOL_CALL:...] 格式并调用工具
    - 多轮对话管理：维护消息历史

    使用示例：
        agent = AttractionSearchAgent(llm, verbose=True)
        result = agent.search("南京", "历史文化")
        print(result)  # 输出格式化的景点列表
    """

    def __init__(self, llm: ChatOpenAI, verbose: bool = True):
        """
        初始化景点搜索 Agent

        Args:
            llm: 大语言模型实例
                可以是 OpenAI、阿里云百炼、智谱等兼容 OpenAI API 的模型
            verbose: 是否打印详细日志
                设为 True 时会打印 Agent 的思考和工具调用过程，
                便于调试和理解 Agent 的工作流程
        """
        # 准备工具列表 - 景点搜索只需要一个工具
        # search_attractions 是一个 @tool 装饰的函数，已被包装成 LangChain Tool
        tools = [search_attractions]

        # 调用父类初始化方法
        # 父类会完成以下工作：
        # 1. 保存 llm、tools、verbose 等属性
        # 2. 创建 AgentExecutor（LangChain 的 Agent 执行器）
        # 3. 设置系统提示词
        super().__init__(
            name="景点搜索专家",           # Agent 名称，用于日志和提示词
            system_prompt=ATTRACTION_PROMPT,  # 系统提示词，定义 Agent 行为
            llm=llm,                     # 大语言模型实例
            tools=tools,                 # 可用工具列表
            verbose=verbose              # 是否打印详细日志
        )

    def search(self, city: str, preferences: str) -> str:
        """
        搜索景点 - 主要的对外接口

        Args:
            city: 城市名称，如 "北京"、"上海"、"南京"
            preferences: 偏好类型，如 "历史文化"、"自然风光"、"美食购物"

        Returns:
            str: 格式化的景点列表字符串
                格式示例：
                "找到以下5个景点：
                 1. 故宫博物院 - 北京市东城区景山前街4号
                 2. 天坛公园 - 北京市东城区天坛路
                 ..."

        工作流程：
            1. 根据参数构建查询字符串
            2. 调用父类的 run() 方法执行 Agent
            3. run() 内部会：
               - 将查询发送给 LLM
               - LLM 决定是否需要调用 search_attractions 工具
               - 执行工具并将结果返回给 LLM
               - LLM 格式化结果后返回

        注意：
            - 实际搜索是由 search_attractions 工具完成的
            - LLM 的作用是理解用户意图并格式化输出
        """
        # 构建查询字符串
        # 查询格式：要求 Agent 搜索指定城市和偏好的景点
        # LLM 会理解这个请求，并决定何时调用 search_attractions 工具
        query = f"请搜索{city}的{preferences}相关景点，返回景点名称、地址和类型。"

        # 调用父类的 run() 方法执行 Agent
        # run() 方法会：
        # 1. 构建消息（system_prompt + user_query）
        # 2. 调用 LLM 获取响应
        # 3. 如果响应中包含 [TOOL_CALL:...] 标记，解析并执行工具
        # 4. 将工具结果返回给 LLM，继续对话
        # 5. 重复直到 LLM 不再调用工具，返回最终答案
        return self.run(query)