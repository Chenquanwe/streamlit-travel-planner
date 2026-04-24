"""首页表单组件 - 用户输入旅行需求"""

import streamlit as st
from datetime import date, timedelta
from models.schemas import TripRequest


def show_home_form() -> TripRequest | None:
    """显示首页表单，返回用户提交的请求"""

    # 初始化 session_state 中的默认值
    if "trip_form_data" not in st.session_state:
        st.session_state.trip_form_data = {
            "city": "",
            "start_date": date.today() + timedelta(days=7),
            "end_date": date.today() + timedelta(days=9),
            "preferences": "历史文化",
            "budget": "中等",
            "transportation": "公共交通",
            "accommodation": "经济型酒店"
        }

    st.markdown("### ✈️ 填写旅行信息")

    col1, col2 = st.columns(2)

    with col1:
        # 目的地城市
        city = st.text_input(
            "📍 目的地城市",
            placeholder="如：北京、上海、南京",
            value=st.session_state.trip_form_data["city"],
            key="city_input",
            help="输入你想去的城市名称"
        )
        # 实时保存
        st.session_state.trip_form_data["city"] = city

        # 开始日期
        start_date = st.date_input(
            "📅 开始日期",
            min_value=date.today(),
            value=st.session_state.trip_form_data["start_date"],
            key="start_date_input",
            help="选择出发日期"
        )
        st.session_state.trip_form_data["start_date"] = start_date

        # 结束日期（最小值随开始日期动态变化）
        min_end_date = start_date
        current_end_date = st.session_state.trip_form_data["end_date"]
        if current_end_date < min_end_date:
            current_end_date = min_end_date

        end_date = st.date_input(
            "📅 结束日期",
            min_value=min_end_date,
            value=current_end_date,
            key="end_date_input",
            help="选择返回日期"
        )
        st.session_state.trip_form_data["end_date"] = end_date

        # 自动计算并显示天数
        days = (end_date - start_date).days + 1
        st.info(f"💡 旅行天数：**{days}天**（由开始和结束日期自动计算）")

    with col2:
        # 旅行偏好
        preferences = st.selectbox(
            "🎯 旅行偏好",
            options=["历史文化", "自然风光", "美食购物", "休闲度假", "冒险探索"],
            index=["历史文化", "自然风光", "美食购物", "休闲度假", "冒险探索"].index(
                st.session_state.trip_form_data["preferences"]
            ),
            key="preferences_input",
            help="选择你感兴趣的旅行类型"
        )
        st.session_state.trip_form_data["preferences"] = preferences

        # 预算范围
        budget = st.select_slider(
            "💰 预算范围",
            options=["经济型", "中等", "舒适型", "豪华型"],
            value=st.session_state.trip_form_data["budget"],
            key="budget_input",
            help="选择整体预算级别"
        )
        st.session_state.trip_form_data["budget"] = budget

        # 交通方式
        transportation = st.selectbox(
            "🚗 交通方式",
            options=["公共交通", "自驾", "打车", "骑行", "步行"],
            index=["公共交通", "自驾", "打车", "骑行", "步行"].index(
                st.session_state.trip_form_data["transportation"]
            ),
            key="transportation_input",
            help="选择主要交通方式"
        )
        st.session_state.trip_form_data["transportation"] = transportation

        # 住宿类型
        accommodation = st.selectbox(
            "🏨 住宿类型",
            options=["经济型酒店", "舒适型酒店", "豪华酒店", "民宿", "青年旅社"],
            index=["经济型酒店", "舒适型酒店", "豪华酒店", "民宿", "青年旅社"].index(
                st.session_state.trip_form_data["accommodation"]
            ),
            key="accommodation_input",
            help="选择住宿偏好"
        )
        st.session_state.trip_form_data["accommodation"] = accommodation

    st.markdown("---")

    # 提交按钮（不在 form 内）
    submitted = st.button("🚀 开始规划", width='stretch', type="primary")

    if submitted and city:
        return TripRequest(
            city=city,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            days=days,
            preferences=preferences,
            budget=budget,
            transportation=transportation,
            accommodation=accommodation
        )
    elif submitted and not city:
        st.error("❌ 请输入目的地城市")

    return None