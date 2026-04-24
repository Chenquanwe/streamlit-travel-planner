"""
酒店推荐 Agent - 负责根据用户需求推荐合适的酒店

功能：根据用户输入的城市和酒店类型（经济型、舒适型、豪华型等），
使用高德地图API搜索相关酒店，返回格式化的酒店推荐列表。

工作流程：
1. 接收城市名称和酒店类型
2. 调用高德地图POI搜索API（关键词：酒店类型+酒店）
3. 解析返回的酒店数据（名称、地址、类型、价格）
4. 返回格式化的酒店推荐列表
"""

# ==================== 第三方库导入 ====================
# ChatOpenAI: LangChain 的 OpenAI 兼容接口，用于调用大语言模型
from langchain_openai import ChatOpenAI

# ==================== 项目内部导入 ====================
# BaseTravelAgent: 所有旅行Agent的基类
# 提供了 run() 方法、工具调用、消息管理等通用功能
from agents.base_agent import BaseTravelAgent

# search_hotels: 高德地图酒店搜索工具
# 这是一个 LangChain Tool，实际调用高德地图 API 进行 POI 搜索
# 输入参数：city(城市), hotel_type(酒店类型)
# 返回：格式化的酒店列表字符串
from tools.amap_tools import search_hotels


# ==================== Agent 提示词 ====================
# HOTEL_PROMPT 定义了酒店推荐专家的系统提示词
# 这个提示词会被注入到 LLM 的 system message 中，
# 指导 LLM 如何使用工具和处理用户请求
#
# 提示词结构说明：
# 1. 角色定义：明确 Agent 的身份是"酒店推荐专家"
# 2. 职责描述：说明 Agent 需要完成的任务（根据需求和预算推荐酒店）
# 3. 工具说明：指明要使用的 search_hotels 工具
# 4. 约束条件：强调必须使用工具搜索，不能编造信息
# 5. 输出要求：规定返回结果应包含酒店名称、地址、类型等信息
HOTEL_PROMPT = """你是一个酒店推荐专家。

你的职责：
1. 根据用户需求和预算，推荐合适的酒店
2. 使用 search_hotels 工具获取酒店信息
3. 返回格式化的酒店推荐列表

注意事项：
- 必须使用工具搜索，不要编造酒店信息
- 根据用户预算推荐相应档次的酒店
- 返回结果应包含酒店名称、地址、类型等信息
"""


# ==================== 酒店推荐 Agent 类 ====================
class HotelAgent(BaseTravelAgent):
    """
    酒店推荐 Agent

    职责：根据用户输入的城市和酒店类型，搜索并返回相关酒店信息

    继承自 BaseTravelAgent，获得以下能力：
    - run() 方法：执行 Agent 任务
    - 工具调用机制：自动解析 [TOOL_CALL:...] 格式并调用工具
    - 多轮对话管理：维护消息历史

    使用示例：
        agent = HotelAgent(llm, verbose=True)
        result = agent.recommend("南京", "经济型")
        print(result)  # 输出格式化的酒店推荐列表
    """

    def __init__(self, llm: ChatOpenAI, verbose: bool = True):
        """
        初始化酒店推荐 Agent

        Args:
            llm: 大语言模型实例
                可以是 OpenAI、阿里云百炼、智谱等兼容 OpenAI API 的模型
            verbose: 是否打印详细日志
                设为 True 时会打印 Agent 的思考和工具调用过程，
                便于调试和理解 Agent 的工作流程
        """
        # 准备工具列表 - 酒店推荐只需要一个工具
        # search_hotels 是一个 @tool 装饰的函数，已被包装成 LangChain Tool
        # 该工具接受 city 和 hotel_type 两个参数
        tools = [search_hotels]

        # 调用父类初始化方法
        # 父类会完成以下工作：
        # 1. 保存 llm、tools、verbose 等属性
        # 2. 将工具列表转换为字典（工具名 → 工具对象）
        # 3. 保存系统提示词
        super().__init__(
            name="酒店推荐专家",           # Agent 名称，用于日志和提示词
            system_prompt=HOTEL_PROMPT,   # 系统提示词，定义 Agent 行为
            llm=llm,                      # 大语言模型实例
            tools=tools,                  # 可用工具列表
            verbose=verbose               # 是否打印详细日志
        )

    def recommend(self, city: str, hotel_type: str) -> str:
        """
        推荐酒店 - 主要的对外接口

        Args:
            city: 城市名称
                例如："北京"、"上海"、"南京"
            hotel_type: 酒店类型
                常见类型：
                - "经济型"：如汉庭、如家、7天等连锁酒店
                - "舒适型"：如全季、亚朵等中档酒店
                - "豪华型"：如希尔顿、万豪等五星级酒店
                - "民宿"：特色民宿、客栈

        Returns:
            str: 格式化的酒店推荐列表字符串
                格式示例：
                "找到以下5家经济型酒店：
                 1. 如家精选酒店（南京新街口店） - 南京市秦淮区汉中路185号
                 2. 汉庭酒店（南京夫子庙店） - 南京市秦淮区贡院街XX号
                 ..."

        工作流程：
            1. 根据参数构建查询字符串
            2. 调用父类的 run() 方法执行 Agent
            3. run() 内部会：
               - 将查询发送给 LLM
               - LLM 决定是否需要调用 search_hotels 工具
               - 执行工具并将结果返回给 LLM
               - LLM 格式化结果后返回

        注意：
            - 实际搜索是由 search_hotels 工具完成的
            - LLM 的作用是理解用户意图并格式化输出
            - 工具会根据 hotel_type 自动选择合适的关键词进行搜索
        """
        # 构建查询字符串
        # 查询格式：要求 Agent 推荐指定城市和类型的酒店
        # LLM 会理解这个请求，并决定何时调用 search_hotels 工具
        #
        # 示例：
        #   city="南京", hotel_type="经济型"
        #   → "请推荐南京的经济型酒店，返回酒店名称和地址。"
        query = f"请推荐{city}的{hotel_type}酒店，返回酒店名称和地址。"

        # 调用父类的 run() 方法执行 Agent
        # run() 方法会：
        # 1. 构建消息（system_prompt + user_query）
        # 2. 调用 LLM 获取响应
        # 3. 如果响应中包含 [TOOL_CALL:...] 标记，解析并执行工具
        # 4. 将工具结果返回给 LLM，继续对话
        # 5. 重复直到 LLM 不再调用工具，返回最终答案
        return self.run(query)