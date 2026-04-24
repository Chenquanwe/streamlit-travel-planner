"""结果展示页组件 - 独立的结果展示模块"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from models.schemas import TripPlan
import logging

logger = logging.getLogger(__name__)


class ResultDisplay:
    """结果展示器"""

    def __init__(self):
        self.export_format = "json"
        # 从环境变量读取高德 Web Key
        self.amap_key = os.getenv("AMAP_WEB_KEY", "")
        if not self.amap_key:
            logger.warning("AMAP_WEB_KEY 未配置，地图将无法显示")

    def display(self, trip_plan: TripPlan):
        """显示旅行计划"""
        if not trip_plan:
            st.warning("暂无旅行计划数据")
            return

        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 行程概览", "🗺️ 每日详情", "🌤️ 天气信息", "💰 预算明细"
        ])

        with tab1:
            self._show_overview(trip_plan)

        with tab2:
            self._show_daily_details(trip_plan)

        with tab3:
            self._show_weather(trip_plan)

        with tab4:
            self._show_budget(trip_plan)

        self._show_export_options(trip_plan)

    def _show_overview(self, trip_plan: TripPlan):
        """显示概览"""
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 16px; padding: 1.5rem; color: white; margin-bottom: 1rem;">
            <h2 style="color: white; margin: 0;">✈️ {trip_plan.city} 旅行计划</h2>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">
                📅 {trip_plan.start_date} - {trip_plan.end_date} | 
                🏨 {len(trip_plan.days)} 天行程
            </p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🏨 住宿天数", f"{len(trip_plan.days)} 晚")
        with col2:
            total_attractions = sum(len(day.attractions) for day in trip_plan.days)
            st.metric("📍 景点数量", f"{total_attractions} 个")
        with col3:
            if trip_plan.budget:
                st.metric("💰 预估总费用", f"¥{trip_plan.budget.total}")
        with col4:
            st.metric("🌤️ 天气天数", f"{len(trip_plan.weather_info)} 天")

        if trip_plan.overall_suggestions:
            st.info(f"💡 **总体建议**：{trip_plan.overall_suggestions}")

        st.subheader("📅 行程摘要")
        for day in trip_plan.days:
            with st.expander(f"第 {day.day_index + 1} 天 - {day.date}", expanded=False):
                st.markdown(f"**{day.description}**")
                st.markdown(f"🚗 {day.transportation} | 🏨 {day.accommodation}")
                if day.attractions:
                    st.markdown("**景点：** " + " → ".join([a.name for a in day.attractions]))

    def _show_daily_details(self, trip_plan: TripPlan):
        """显示每日详情"""
        for day_index, day in enumerate(trip_plan.days):
            with st.container():
                st.markdown(f"""
                <div style="background: #f8f9fa; border-radius: 12px; padding: 1rem; margin-bottom: 1rem;">
                    <h3>📅 第 {day.day_index + 1} 天 - {day.date}</h3>
                    <p><strong>{day.description}</strong></p>
                </div>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**🚗 交通方式**")
                    st.info(day.transportation)
                    st.markdown("**🏨 住宿安排**")
                    st.info(day.accommodation)
                    if day.hotel:
                        st.markdown("**🏨 推荐酒店**")
                        st.write(f"**{day.hotel.name}**")
                        st.caption(f"📍 {day.hotel.address}")
                        if day.hotel.estimated_cost:
                            st.caption(f"💰 参考价格：¥{day.hotel.estimated_cost}/晚")

                with col2:
                    if day.meals:
                        st.markdown("**🍽️ 餐饮推荐**")
                        for meal in day.meals:
                            meal_icon = {"breakfast": "🍳", "lunch": "🍜", "dinner": "🍽️", "snack": "🍎"}.get(meal.type, "🍴")
                            st.write(f"{meal_icon} **{meal.name}** - ¥{meal.estimated_cost}")
                            st.caption(meal.description)

                # 显示后端计算的路线信息（如果有）
                if day.route and day.route.distance > 0:
                    distance_km = day.route.distance / 1000
                    duration_min = day.route.duration / 60
                    st.markdown(f"""
                    <div style="background: #f0f7ff; border-radius: 8px; padding: 0.8rem; margin: 0.5rem 0;">
                        <span>🚗 驾车距离: <strong>{distance_km:.1f}公里</strong></span>
                        <span style="margin-left: 1rem;">⏱️ 预计时间: <strong>{duration_min:.0f}分钟</strong></span>
                    </div>
                    """, unsafe_allow_html=True)

                # 景点详情
                if day.attractions:
                    st.markdown("---")
                    st.markdown("### 📍 景点安排")

                    for i, attr in enumerate(day.attractions, 1):
                        col_img, col_info = st.columns([1, 2])
                        with col_img:
                            if attr.image_url:
                                st.image(attr.image_url, width=150)
                            else:
                                st.image("https://via.placeholder.com/150x100?text=景点", width=150)

                        with col_info:
                            st.markdown(f"**{i}. {attr.name}**")
                            st.caption(f"📍 {attr.address}")
                            if attr.description:
                                st.caption(f"📖 {attr.description[:150]}...")
                            col_info1, col_info2 = st.columns(2)
                            with col_info1:
                                st.markdown(f"⏱️ 建议游览：{attr.visit_duration}分钟")
                            with col_info2:
                                if attr.ticket_price:
                                    st.markdown(f"🎫 门票：¥{attr.ticket_price}")

                        st.markdown("---")

                    # ========== 地图显示 ==========
                    st.markdown("### 🗺️ 行程地图")

                    # 调试信息
                    with st.expander("🔍 调试信息（点击展开）"):
                        st.write(f"AMAP_WEB_KEY 状态: {'✅ 已配置' if self.amap_key else '❌ 未配置'}")
                        if self.amap_key:
                            st.write(f"Key 前缀: {self.amap_key[:10]}...")

                        valid_attrs = [a for a in day.attractions if a.location and a.location.longitude]
                        st.write(f"有效坐标景点数: {len(valid_attrs)} / {len(day.attractions)}")

                        for a in day.attractions:
                            if a.location and a.location.longitude:
                                st.write(f"  ✅ {a.name}: {a.location.longitude}, {a.location.latitude}")
                            else:
                                st.write(f"  ❌ {a.name}: 无坐标")

                    # 生成并显示地图（使用 folium）
                    if self.amap_key:
                        try:
                            valid_attrs = [a for a in day.attractions if a.location and a.location.longitude]

                            if len(valid_attrs) >= 2:
                                # 计算中心点
                                lats = [a.location.latitude for a in valid_attrs]
                                lngs = [a.location.longitude for a in valid_attrs]
                                center_lat = sum(lats) / len(lats)
                                center_lng = sum(lngs) / len(lngs)

                                # 动态计算缩放级别
                                lat_span = max(lats) - min(lats)
                                lng_span = max(lngs) - min(lngs)
                                max_span = max(lat_span, lng_span)

                                if max_span < 0.01:
                                    zoom = 15
                                elif max_span < 0.05:
                                    zoom = 14
                                elif max_span < 0.1:
                                    zoom = 13
                                elif max_span < 0.2:
                                    zoom = 12
                                elif max_span < 0.5:
                                    zoom = 11
                                elif max_span < 1.0:
                                    zoom = 10
                                elif max_span < 2.0:
                                    zoom = 9
                                else:
                                    zoom = 8

                                st.write(f"📍 地图缩放级别: {zoom} (范围: {max_span:.2f}°)")

                                # 创建 folium 地图，使用高德地图图源
                                tiles_url = f"http://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={{x}}&y={{y}}&z={{z}}"
                                m = folium.Map(
                                    location=[center_lat, center_lng],
                                    zoom_start=zoom,
                                    tiles=tiles_url,
                                    attr="© 高德地图"
                                )

                                # 添加景点标记
                                for idx, attr in enumerate(valid_attrs):
                                    icon_html = f'''
                                        <div style="font-family: sans-serif; font-size: 12px; font-weight: bold; 
                                                    background-color: #667eea; color: white; border-radius: 50%; 
                                                    width: 24px; height: 24px; display: flex; align-items: center; 
                                                    justify-content: center; border: 2px solid white; 
                                                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
                                            {idx + 1}
                                        </div>
                                    '''
                                    folium.Marker(
                                        location=[attr.location.latitude, attr.location.longitude],
                                        popup=folium.Popup(html=f"<b>{attr.name}</b><br>{attr.address}", max_width=300),
                                        tooltip=attr.name,
                                        icon=folium.DivIcon(html=icon_html)
                                    ).add_to(m)

                                # 添加路线连线（直线）
                                if len(valid_attrs) >= 2:
                                    points = [[a.location.latitude, a.location.longitude] for a in valid_attrs]
                                    folium.PolyLine(
                                        locations=points,
                                        color='#667eea',
                                        weight=4,
                                        opacity=0.8
                                    ).add_to(m)

                                # 渲染地图
                                st_folium(m, width=700, height=500, key=f"map_{day_index}")
                                st.success("✅ 地图已加载")
                            else:
                                st.warning(f"⚠️ 第 {day_index + 1} 天少于2个景点，无法显示路线")
                        except Exception as e:
                            st.error(f"❌ 地图生成失败: {e}")
                    else:
                        st.warning("⚠️ 未配置 AMAP_WEB_KEY，无法显示地图")

                st.markdown("---")

    def _show_weather(self, trip_plan: TripPlan):
        """显示天气信息"""
        if not trip_plan.weather_info:
            st.info("暂无天气信息")
            return

        weather_data = []
        for w in trip_plan.weather_info:
            weather_data.append({
                "日期": w.date,
                "白天天气": w.day_weather,
                "夜间天气": w.night_weather,
                "白天温度": f"{w.day_temp}°C",
                "夜间温度": f"{w.night_temp}°C",
            })
        st.dataframe(weather_data, width='stretch')

        temps_day = [w.day_temp for w in trip_plan.weather_info]
        temps_night = [w.night_temp for w in trip_plan.weather_info]
        dates = [w.date for w in trip_plan.weather_info]

        if temps_day:
            chart_data = {"日期": dates, "白天温度": temps_day, "夜间温度": temps_night}
            st.line_chart(chart_data, x="日期", y=["白天温度", "夜间温度"])

    def _show_budget(self, trip_plan: TripPlan):
        """显示预算信息"""
        if not trip_plan.budget:
            st.info("暂无预算信息")
            return

        budget = trip_plan.budget
        budget_data = {
            "类别": ["景点门票", "酒店住宿", "餐饮费用", "交通费用"],
            "金额": [budget.total_attractions, budget.total_hotels, budget.total_meals, budget.total_transportation]
        }
        st.bar_chart(budget_data, x="类别", y="金额")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 费用明细")
            st.write(f"- 🎫 景点门票：¥{budget.total_attractions}")
            st.write(f"- 🏨 酒店住宿：¥{budget.total_hotels}")
            st.write(f"- 🍽️ 餐饮费用：¥{budget.total_meals}")
            st.write(f"- 🚗 交通费用：¥{budget.total_transportation}")

        with col2:
            st.markdown("### 费用占比")
            total = budget.total if budget.total > 0 else 1
            st.write(f"- 景点：{budget.total_attractions / total * 100:.1f}%")
            st.write(f"- 酒店：{budget.total_hotels / total * 100:.1f}%")
            st.write(f"- 餐饮：{budget.total_meals / total * 100:.1f}%")
            st.write(f"- 交通：{budget.total_transportation / total * 100:.1f}%")

        st.markdown("---")
        st.metric("💰 预估总费用", f"¥{budget.total}")

    def _show_export_options(self, trip_plan: TripPlan):
        """显示导出选项"""
        st.markdown("---")
        st.subheader("📎 导出选项")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 导出为 JSON", width='stretch'):
                json_str = trip_plan.model_dump_json(indent=2, ensure_ascii=False)
                st.download_button(
                    label="下载 JSON",
                    data=json_str,
                    file_name=f"travel_plan_{trip_plan.city}_{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    width='stretch'
                )
        with col2:
            if st.button("📋 复制为 Markdown", width='stretch'):
                md_content = self._to_markdown(trip_plan)
                st.code(md_content, language="markdown")
                st.success("已生成 Markdown 内容")

    def _to_markdown(self, trip_plan: TripPlan) -> str:
        """转换为 Markdown 格式"""
        md = f"""# {trip_plan.city} 旅行计划

**日期**：{trip_plan.start_date} - {trip_plan.end_date}
**天数**：{len(trip_plan.days)} 天

## 总体建议

{trip_plan.overall_suggestions}

## 每日行程

"""
        for day in trip_plan.days:
            md += f"""
### 第 {day.day_index + 1} 天 - {day.date}

**{day.description}**

- 交通方式：{day.transportation}
- 住宿安排：{day.accommodation}

#### 景点安排

"""
            for attr in day.attractions:
                md += f"""
- **{attr.name}**
  - 地址：{attr.address}
  - 游览时间：{attr.visit_duration}分钟
  - 门票：¥{attr.ticket_price}
"""

        if trip_plan.weather_info:
            md += """
## 天气信息

| 日期 | 天气 | 温度 |
|------|------|------|
"""
            for w in trip_plan.weather_info:
                md += f"| {w.date} | {w.day_weather} | {w.day_temp}°C |\n"

        return md


def display_result(trip_plan: TripPlan):
    """便捷函数：显示旅行计划结果"""
    displayer = ResultDisplay()
    displayer.display(trip_plan)