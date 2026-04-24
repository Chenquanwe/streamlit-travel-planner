"""
智能旅行助手 - Streamlit 主入口

这是整个应用的入口文件，负责：
1. 配置 Streamlit 页面
2. 初始化 LLM 和多智能体系统
3. 渲染用户界面（表单、结果）
4. 协调用户交互和后台处理

技术栈：
- Streamlit: 快速构建 Web 界面
- LangChain: 大语言模型调用
- 多智能体系统: 旅行规划核心
"""

# ==================== 标准库导入 ====================
import streamlit as st      # Streamlit Web 框架，用于构建 UI
import os                    # 操作系统接口，用于读取环境变量
import logging               # 日志记录，用于记录系统运行状态
from dotenv import load_dotenv  # 加载 .env 文件中的环境变量
from langchain_openai import ChatOpenAI  # OpenAI 兼容的聊天模型

# 加载 .env 文件中的环境变量
# .env 文件包含敏感信息（API Keys），不应提交到 Git
# 例如：LLM_API_KEY, AMAP_API_KEY, AMAP_WEB_KEY 等
load_dotenv()

# 配置日志系统
# level=logging.INFO: 只显示 INFO、WARNING、ERROR 级别的日志
# 调试时可将级别改为 DEBUG 查看更多信息
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  # 获取当前模块的日志记录器

# ==================== 项目内部模块导入 ====================
from models.schemas import TripRequest  # 用户请求数据模型
from agents.supervisor import TravelSupervisor  # 多智能体监督者（核心控制器）
from ui.styles import MAIN_STYLES, SIDEBAR_STYLES  # CSS 样式
from ui.components import show_header, show_sidebar_info, show_loading_progress, update_progress  # UI 组件
from ui.result import display_result  # 结果展示函数
from ui.home import show_home_form  # 首页表单函数


# ==================== Streamlit 页面配置 ====================
# st.set_page_config 必须在任何其他 Streamlit 命令之前调用
# 这是 Streamlit 的硬性要求
st.set_page_config(
    page_title="智能旅行助手 - AI 多智能体旅行规划",  # 浏览器标签页标题
    page_icon="✈️",                                 # 浏览器标签页图标（飞机表情）
    layout="wide",                                  # 页面布局：wide 表示宽屏模式
    initial_sidebar_state="expanded"                # 侧边栏初始状态：expanded 表示展开
)

# 应用自定义 CSS 样式
# MAIN_STYLES: 主内容区域的样式（标题、卡片、按钮、进度条等）
# unsafe_allow_html=True 允许在 markdown 中嵌入 HTML 代码
st.markdown(MAIN_STYLES, unsafe_allow_html=True)
st.markdown(SIDEBAR_STYLES, unsafe_allow_html=True)


# ==================== LLM 初始化函数 ====================
def init_llm() -> ChatOpenAI:
    """
    初始化大语言模型实例

    使用 OpenAI 兼容接口，支持：
    - 阿里云百炼（DashScope）
    - OpenAI
    - 其他兼容 OpenAI API 的服务

    Returns:
        ChatOpenAI: 配置好的 LLM 实例
    """
    return ChatOpenAI(
        # 模型名称，从环境变量读取，默认 qwen-plus
        # qwen-plus 是阿里云百炼的模型，速度快，能力均衡
        model=os.getenv("LLM_MODEL", "qwen-plus"),

        # API 地址，从环境变量读取
        # 阿里云百炼: https://dashscope.aliyuncs.com/compatible-mode/v1
        base_url=os.getenv("LLM_BASE_URL"),

        # API 密钥，从环境变量读取
        # 格式：sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        api_key=os.getenv("LLM_API_KEY"),

        # 温度参数：控制输出的随机性
        # 范围 0.0-1.0，值越小输出越确定，值越大输出越有创造性
        # 0.3 是一个平衡值，既有一定的创造性，又不会太发散
        temperature=0.3,

        # 是否使用流式输出
        # False: 一次性返回完整结果（适合批量处理）
        # True: 逐字返回（适合聊天场景，实时显示）
        streaming=False
    )


# ==================== 会话状态初始化函数 ====================
def init_session_state():
    """
    初始化 Streamlit 会话状态

    Streamlit 在每次交互时都会重新运行脚本，
    st.session_state 用于在多次运行之间保持数据。

    会话状态说明：
    - trip_plan: 存储生成的旅行计划（TripPlan 对象）
    - loading: 是否正在处理请求（显示加载动画）
    - llm: 大语言模型实例（只需初始化一次）
    - supervisor: 多智能体监督者（只需初始化一次）
    """
    # ----- 存储生成的旅行计划 -----
    # 用户提交请求后，结果会存储在这里
    if "trip_plan" not in st.session_state:
        st.session_state.trip_plan = None

    # ----- 加载状态标志 -----
    # True 表示正在后台处理，显示加载动画，防止重复提交
    if "loading" not in st.session_state:
        st.session_state.loading = False

    # ----- 初始化 LLM（只执行一次）-----
    if "llm" not in st.session_state:
        # st.spinner 显示一个加载提示
        with st.spinner("正在初始化 AI 模型..."):
            st.session_state.llm = init_llm()

    # ----- 初始化多智能体系统（只执行一次）-----
    if "supervisor" not in st.session_state:
        with st.spinner("正在初始化多智能体系统..."):
            st.session_state.supervisor = TravelSupervisor(
                st.session_state.llm,   # 传入 LLM 实例
                verbose=True,           # True 表示打印详细日志到控制台
                use_mcp=True            # True 表示使用 MCP 模式（通过协议调用工具）
                # use_mcp=False 表示使用普通模式（直接调用函数）
            )


# ==================== 主函数 ====================
def main():
    """主函数"""
    show_sidebar_info()
    show_header()
    init_session_state()
    request = show_home_form()

    if request and not st.session_state.loading:
        st.session_state.loading = True
        st.session_state.trip_plan = None

        progress_placeholder, status_placeholder, steps = show_loading_progress()

        try:
            # 定义进度回调
            def update_progress(step_index, step_name):
                """进度回调：更新 UI"""
                if step_index < len(steps):
                    name, percent = steps[step_index]
                    status_placeholder.info(name)
                    progress_placeholder.progress(percent)
                print(f"📊 进度更新: {step_name} (步骤{step_index + 1}/4)")

            # 调用后端，传入回调
            result = st.session_state.supervisor.plan_trip(
                request,
                progress_callback=update_progress
            )

            if result:
                st.session_state.trip_plan = result
                # 完成后显示100%
                status_placeholder.success("✅ 规划完成！")
                progress_placeholder.progress(100)
            else:
                status_placeholder.error("❌ 规划失败，请重试")

            # 延迟清除进度显示，让用户看到完成状态
            import time
            time.sleep(1)
            progress_placeholder.empty()
            status_placeholder.empty()

        except Exception as e:
            logger.error(f"规划失败: {e}")
            status_placeholder.error(f"❌ 生成失败: {str(e)}")
            progress_placeholder.empty()
            status_placeholder.empty()
        finally:
            st.session_state.loading = False
            st.rerun()

    if st.session_state.trip_plan:
        display_result(st.session_state.trip_plan)

        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔄 重新规划", width='stretch'):
                st.session_state.trip_plan = None
                st.rerun()

# ==================== 程序入口 ====================


if __name__ == "__main__":
    main()
