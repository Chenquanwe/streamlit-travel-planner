"""CSS 样式定义 - 极简黑白色"""

MAIN_STYLES = """
<style>
    /* 主标题 - 无背景 */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        color: #111;
        font-size: 2rem;
        margin: 0;
        font-weight: 600;
    }
    .main-header p {
        color: #555;
        font-size: 0.9rem;
    }

    /* 结果卡片 */
    .result-card {
        background: white;
        border-radius: 0;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        border-bottom: 1px solid #eee;
    }

    /* 每日行程卡片 */
    .day-card {
        padding: 1.2rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid #eee;
    }

    /* 景点项目 */
    .attraction-item {
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-bottom: 1px solid #f0f0f0;
    }

    /* 按钮样式 */
    .stButton > button {
        background: #5bb5c9;
        color: white;
        border: none;
        border-radius: 0;
        padding: 0.5rem 2rem;
    }
    .stButton > button:hover {
        background: #3a9bb0;
    }

    /* 侧边栏 */
    [data-testid="stSidebar"] {
        background: #fafafa;
    }

    /* 进度条 */
    .stProgress > div > div {
        background: #111;
        border-radius: 0;
    }
</style>
"""

SIDEBAR_STYLES = """
<style>
    .sidebar-logo {
        text-align: center;
        padding: 1rem;
    }
    .sidebar-logo h2 {
        color: #111;
        margin: 0;
    }
</style>
"""