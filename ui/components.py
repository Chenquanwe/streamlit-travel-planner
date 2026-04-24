"""可复用的 UI 组件"""

import streamlit as st
from typing import Dict, Any, List, Optional
from models.schemas import TripPlan, WeatherInfo, Attraction, DayPlan


def show_header():
    """显示页面头部"""
    st.markdown("""
    <div class="main-header">
        <h1>✈️ 智能旅行助手</h1>
        <p>基于 AI 多智能体的个性化旅行规划</p>
    </div>
    """, unsafe_allow_html=True)


def show_sidebar_info():
    """显示侧边栏信息"""
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-logo">
            <h2>✈️ 旅行助手</h2>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        st.info(
            "💡 **使用提示**\n\n"
            "- 填写目的地和日期\n"
            "- 选择你的偏好和预算\n"
            "- AI 会自动规划行程\n"
            "- 支持导出为 JSON和markdown格式"
        )

        st.markdown("---")

        with st.expander("📌 关于本应用"):
            st.markdown(
                "本应用使用 **LangChain** 多智能体框架构建，\n\n"
                "包含以下 AI 助手：\n"
                "- 🤖 景点搜索专家\n"
                "- 🌤️ 天气查询专家\n"
                "- 🏨 酒店推荐专家\n"
                "- 📋 行程规划专家\n\n"
                "数据来源：高德地图 API和Pexels API"
            )










def show_loading_progress():
    """显示加载进度"""
    progress_placeholder = st.empty()
    status_placeholder = st.empty()

    steps = [
        ("🔍 正在搜索景点...", 10),
        ("🌤️ 正在查询天气...", 20),
        ("🏨 正在推荐酒店...", 35),
        ("📋 正在生成行程计划...", 50)
    ]

    return progress_placeholder, status_placeholder, steps


def update_progress(progress_placeholder, status_placeholder, step_index: int, steps: list):
    """更新进度"""
    if step_index < len(steps):
        status, percent = steps[step_index]
        status_placeholder.info(status)
        progress_placeholder.progress(percent)
