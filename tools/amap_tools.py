"""高德地图 API 工具封装"""

import requests
import json
import os
from typing import List, Dict
from langchain.tools import tool


class AMapService:
    """高德地图服务类"""

    def __init__(self):
        self.api_key = os.getenv("AMAP_API_KEY")
        self.base_url = "https://restapi.amap.com/v3"

    def search_poi(self, keywords: str, city: str) -> List[Dict]:
        """搜索 POI"""
        url = f"{self.base_url}/place/text"
        params = {
            "keywords": keywords,
            "city": city,
            "key": self.api_key,
            "output": "json",
            "offset": 10
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get("status") == "1":
                pois = data.get("pois", [])
                results = []
                for poi in pois:
                    location = poi.get("location", "").split(",")
                    results.append({
                        "name": poi.get("name"),
                        "address": poi.get("address"),
                        "longitude": float(location[0]) if len(location) > 0 else 0,
                        "latitude": float(location[1]) if len(location) > 1 else 0,
                        "type": poi.get("type")
                    })
                return results
            return []
        except Exception as e:
            print(f"POI搜索失败: {e}")
            return []

    def get_weather(self, city: str) -> List[Dict]:
        """获取天气信息"""
        url = f"{self.base_url}/weather/weatherInfo"
        params = {
            "city": city,
            "key": self.api_key,
            "extensions": "all"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get("status") == "1" and data.get("forecasts"):
                forecast = data["forecasts"][0]
                casts = forecast.get("casts", [])
                results = []
                for cast in casts[:5]:
                    results.append({
                        "date": cast.get("date"),
                        "day_weather": cast.get("dayweather"),
                        "night_weather": cast.get("nightweather"),
                        "day_temp": int(cast.get("daytemp", 0)),
                        "night_temp": int(cast.get("nighttemp", 0)),
                        "wind_direction": cast.get("daywind", ""),
                        "wind_power": cast.get("daypower", "")
                    })
                return results
            return []
        except Exception as e:
            print(f"天气查询失败: {e}")
            return []

    def get_driving_route(self, origin: str, destination: str, waypoints: str = "") -> Dict:
        """获取驾车路线规划"""
        url = f"{self.base_url}/direction/driving"
        params = {
            "key": self.api_key,
            "origin": origin,
            "destination": destination,
            "extensions": "all"
        }
        if waypoints:
            params["waypoints"] = waypoints

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get("status") == "1":
                route = data.get("route", {})
                paths = route.get("paths", [])
                if paths:
                    path = paths[0]
                    return {
                        "distance": int(path.get("distance", 0)),
                        "duration": int(path.get("duration", 0)),
                        "steps": path.get("steps", [])
                    }
            return {"error": data.get("info", "规划失败")}
        except Exception as e:
            return {"error": str(e)}


_amap_service = None


def get_amap_service() -> AMapService:
    global _amap_service
    if _amap_service is None:
        _amap_service = AMapService()
    return _amap_service


@tool
def search_attractions(city: str, preferences: str = "景点") -> str:
    """
    搜索指定城市的景点。

    参数:
    - city: 城市名称，如"北京"、"上海"
    - preferences: 偏好类型，如"景点"、"博物馆"、"公园"

    返回: JSON格式的景点列表
    """
    service = get_amap_service()

    keywords_map = {
        "历史文化": "博物馆|古迹",
        "自然风光": "公园|风景区",
        "美食购物": "美食街|商场",
        "休闲度假": "度假村|乐园",
        "景点": "景点"
    }

    keywords = keywords_map.get(preferences, "景点")
    results = service.search_poi(keywords, city)

    if results:
        output = f"找到以下{len(results)}个景点：\n"
        for i, r in enumerate(results[:5], 1):
            output += f"{i}. {r.get('name')} - {r.get('address')}\n"
        return output
    return f"未找到{city}的{preferences}相关景点"


@tool
def search_hotels(city: str, hotel_type: str = "经济型") -> str:
    """
    搜索指定城市的酒店。

    参数:
    - city: 城市名称
    - hotel_type: 酒店类型，如"经济型"、"舒适型"

    返回: 格式化的酒店列表
    """
    service = get_amap_service()

    type_map = {
        "经济型": "经济型酒店",
        "舒适型": "舒适型酒店",
        "豪华型": "豪华酒店",
        "民宿": "民宿"
    }

    keywords = type_map.get(hotel_type, "酒店")
    results = service.search_poi(keywords, city)

    if results:
        output = f"找到以下{len(results)}家{hotel_type}酒店：\n"
        for i, r in enumerate(results[:5], 1):
            output += f"{i}. {r.get('name')} - {r.get('address')}\n"
        return output
    return f"未找到{city}的{hotel_type}酒店"


@tool
def query_weather(city: str) -> str:
    """
    查询指定城市未来几天的天气预报。

    参数:
    - city: 城市名称，如"北京"

    返回: 格式化的天气预报
    """
    service = get_amap_service()
    results = service.get_weather(city)

    if results:
        output = f"{city}未来天气：\n"
        for w in results:
            output += f"📅 {w['date']}: {w['day_weather']} {w['day_temp']}°C\n"
        return output
    return f"未找到{city}的天气信息"


@tool
def get_driving_route(origin: str, destination: str, waypoints: str = "") -> str:
    """
    获取驾车路线规划。

    参数:
    - origin: 起点坐标，格式 "经度,纬度"
    - destination: 终点坐标，格式 "经度,纬度"
    - waypoints: 途经点（可选），格式 "经度,纬度|经度,纬度"

    返回: JSON格式的路线信息
    """
    service = get_amap_service()
    result = service.get_driving_route(origin, destination, waypoints)
    return json.dumps(result, ensure_ascii=False)