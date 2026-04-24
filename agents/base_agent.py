"""
基础 Agent 类 - 所有旅行 Agent 的基类

本模块定义了旅行规划系统中所有 Agent 的通用行为和接口。
采用"模板方法"设计模式，子类只需提供系统提示词和工具列表，
基类负责处理 LLM 调用、工具调用、消息管理等通用逻辑。

核心工作流程：
1. 用户输入查询 → 2. 调用 LLM → 3. 检查是否调用工具 → 4. 执行工具 → 5. 继续循环 → 6. 返回最终答案

这个设计使得：
- 子类可以专注于业务逻辑（定义提示词和工具）
- 基类统一处理复杂的工具调用循环
- 支持多轮对话和上下文记忆
"""

# ==================== 第三方库导入 ====================
# ChatOpenAI: LangChain 的 OpenAI 兼容接口
# 用于调用大语言模型（支持 OpenAI、阿里云百炼、智谱等）
from langchain_openai import ChatOpenAI

# BaseTool: LangChain 工具基类
# 用于类型注解，表示工具列表的元素类型
from langchain.tools import BaseTool

# ==================== 标准库导入 ====================
from typing import List, Optional  # 类型注解，提高代码可读性和 IDE 支持


# ==================== 旅行 Agent 基类 ====================
class BaseTravelAgent:
    """
    旅行 Agent 基类

    所有旅行相关的 Agent 都应该继承这个类，并实现自己的提示词和工具。

    设计理念：
    - 这是一个"轻量级"Agent 实现，不依赖 LangChain 的复杂 Agent 框架
    - 采用简单的 [TOOL_CALL:tool_name:参数] 格式来触发工具调用
    - 优点：简单直观，易于调试，完全可控

    工作流程（run 方法）：
    """

    def __init__(
            self,
            name: str,
            system_prompt: str,
            llm: ChatOpenAI,
            tools: List[BaseTool],
            verbose: bool = True
    ):
        """
        初始化 Agent

        Args:
            name: Agent 名称
                用于日志输出和提示词中的身份标识
                例如："景点搜索专家"、"天气查询专家"

            system_prompt: 系统提示词
                定义 Agent 的角色、职责、行为准则
                会被注入到每次对话的 system message 中

            llm: 大语言模型实例
                支持任何兼容 OpenAI API 的模型
                例如：阿里云百炼 qwen-plus、OpenAI GPT-4 等

            tools: 工具列表
                Agent 可以使用的工具集合
                每个工具必须是 LangChain BaseTool 的实例
                工具会在 LLM 请求时被自动发现和调用

            verbose: 是否打印详细日志
                True 时会在控制台打印 LLM 的输出和工具调用过程
                便于调试和理解 Agent 的思考过程
        """
        # Agent 名称
        self.name = name

        # 大语言模型实例
        self.llm = llm

        # 工具字典（工具名 → 工具对象）
        # 将工具列表转换为字典，便于通过名称快速查找
        # 格式：{"tool_name": tool_object, ...}
        self.tools = {tool.name: tool for tool in tools}

        # 是否打印详细日志
        self.verbose = verbose

        # 系统提示词
        self.system_prompt = system_prompt

    def run(self, query: str, max_iterations: int = 3) -> str:
        """
        运行 Agent - 核心方法

        这是 Agent 的主要入口，处理用户查询并返回结果。

        工作流程详解：
        1. 构建初始消息列表（系统提示词 + 用户查询）
        2. 进入循环（最多 max_iterations 次）：
           a. 调用 LLM 获取响应
           b. 检查响应中是否包含工具调用标记 [TOOL_CALL:...]
           c. 如果有工具调用：
              - 解析工具名称和参数
              - 执行对应的工具
              - 将工具结果添加到消息历史中
              - 继续循环，让 LLM 处理工具结果
           d. 如果没有工具调用：
              - 直接返回 LLM 的响应作为最终答案
        3. 如果达到最大迭代次数仍未完成，返回错误信息

        Args:
            query: 用户查询字符串
                  例如："请搜索北京的景点"
            max_iterations: 最大迭代次数
                           防止无限循环，默认3次通常足够

        Returns:
            str: Agent 的最终回答
        """
        # ----- 步骤1：构建初始消息 -----
        # 消息格式遵循 OpenAI API 规范
        # system: 系统提示词，定义 Agent 行为
        # user: 用户输入
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query}
        ]

        # ----- 步骤2：进入迭代循环 -----
        for iteration in range(max_iterations):
            if self.verbose:
                print(f"\n🔄 第 {iteration + 1} 次迭代")

            # ----- 步骤2a：调用 LLM -----
            # invoke 方法会发送消息到 LLM 并获取响应
            response = self.llm.invoke(messages)

            # 提取响应内容（兼容不同的响应格式）
            # response.content 是标准格式
            # 如果不存在，则转为字符串
            content = response.content if hasattr(response, 'content') else str(response)

            if self.verbose:
                print(f"\n🤖 {self.name} 输出: {content[:200]}...")

            # ----- 步骤2b：检查是否需要调用工具 -----
            # 工具调用标记格式：[TOOL_CALL:工具名称:参数]
            # 例如：[TOOL_CALL:search_attractions:city=南京,preferences=历史文化]
            if "[TOOL_CALL:" in content:
                # 解析工具调用
                tool_name, tool_input = self._parse_tool_call(content)

                if self.verbose:
                    print(f"🔧 调用工具: {tool_name}({tool_input})")

                # 检查工具是否存在
                if tool_name and tool_name in self.tools:
                    # ----- 步骤2c：执行工具 -----
                    # 调用工具的 invoke 方法
                    # 工具会执行实际的操作（如调用 API、查询数据库等）
                    tool = self.tools[tool_name]
                    result = tool.invoke(tool_input)

                    if self.verbose:
                        print(f"📊 工具结果: {str(result)[:200]}...")

                    # 将 LLM 的响应和工具结果添加到消息历史中
                    # 这样 LLM 可以在下一轮看到自己的思考过程和工具执行结果
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": f"工具执行结果: {result}"})
                else:
                    # 工具未找到，将错误信息添加到消息中
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": f"错误: 未找到工具 {tool_name}"})
            else:
                # ----- 步骤2d：没有工具调用，返回最终答案 -----
                if self.verbose:
                    print(f"✅ {self.name} 完成，返回最终答案")
                return content

        # 达到最大迭代次数仍未完成
        return "达到最大迭代次数，未能完成任务"

    def _parse_tool_call(self, content: str):
        """
        解析工具调用

        从 LLM 的响应中提取工具名称和参数。

        工具调用格式：
        [TOOL_CALL:工具名称:参数]

        示例：
        - [TOOL_CALL:search_attractions:city=南京,preferences=历史文化]
        - [TOOL_CALL:query_weather:city=北京]

        Args:
            content: LLM 的响应内容

        Returns:
            tuple: (tool_name, tool_input)
                   tool_name: 工具名称字符串
                   tool_input: 工具参数字符串
                   如果没有匹配，返回 (None, None)

        正则表达式说明：
        - \[TOOL_CALL: 匹配字面量 "[TOOL_CALL:"
        - (\w+) 捕获工具名称（字母数字下划线）
        - : 匹配冒号分隔符
        - ([^\]]+) 捕获参数（除了 ] 以外的所有字符）
        - \] 匹配字面量 "]"
        """
        import re

        # 正则表达式模式
        # 解释：
        #   \[TOOL_CALL:  - 匹配 "[TOOL_CALL:"
        #   (\w+)         - 捕获组1：工具名称（字母、数字、下划线）
        #   :             - 匹配 ":"
        #   ([^\]]+)      - 捕获组2：参数（非 ] 字符，贪婪匹配）
        #   \]            - 匹配 "]"
        pattern = r'\[TOOL_CALL:(\w+):([^\]]+)\]'

        # 搜索匹配
        match = re.search(pattern, content)

        if match:
            # 返回工具名称和参数
            # group(1) 是第一个捕获组（工具名称）
            # group(2) 是第二个捕获组（参数）
            return match.group(1), match.group(2).strip()
        else:
            # 没有匹配到工具调用
            return None, None