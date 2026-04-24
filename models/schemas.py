"""数据模型定义 - Pydantic Schemas"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
# from models.schemas import Location  # 在 _parse_plan_result 中使用

class Location(BaseModel):
    """位置信息"""
    longitude: float = Field(..., description="经度", ge=-180, le=180)
    latitude: float = Field(..., description="纬度", ge=-90, le=90)


class Attraction(BaseModel):
    """景点信息"""
    name: str = Field(..., description="景点名称")
    address: str = Field(..., description="地址")
    location: Optional[Location] = Field(default=None, description="经纬度坐标")
    visit_duration: int = Field(default=120, description="建议游览时间(分钟)", gt=0)
    description: str = Field(default="", description="景点描述")
    ticket_price: int = Field(default=0, description="门票价格(元)")
    image_url: Optional[str] = Field(default=None, description="图片URL")
    rating: Optional[float] = Field(default=None, description="评分", ge=0, le=5)


class WeatherInfo(BaseModel):
    """天气信息"""
    date: str = Field(..., description="日期")
    day_weather: str = Field(..., description="白天天气")
    night_weather: str = Field(..., description="夜间天气")
    day_temp: int = Field(..., description="白天温度")
    night_temp: int = Field(..., description="夜间温度")
    wind_direction: str = Field(default="", description="风向")
    wind_power: str = Field(default="", description="风力")


class Hotel(BaseModel):
    """酒店信息"""
    name: str = Field(..., description="酒店名称")
    address: str = Field(default="", description="酒店地址")
    location: Optional[Location] = Field(default=None, description="酒店位置")
    estimated_cost: int = Field(default=0, description="预估费用(元/晚)")
    rating: Optional[float] = Field(default=None, description="评分")
    phone: Optional[str] = Field(default=None, description="联系电话")


class Meal(BaseModel):
    """餐饮信息"""
    type: str = Field(..., description="餐饮类型: breakfast/lunch/dinner/snack")
    name: str = Field(..., description="餐饮名称")
    description: str = Field(default="", description="描述")
    estimated_cost: int = Field(default=0, description="预估费用(元)")


class RoutePoint(BaseModel):
    """路线点"""
    longitude: float = Field(..., description="经度")
    latitude: float = Field(..., description="纬度")
    name: Optional[str] = Field(default=None, description="名称")


class RouteInfo(BaseModel):
    """路线信息"""
    start: Optional[RoutePoint] = Field(default=None, description="起点")
    end: Optional[RoutePoint] = Field(default=None, description="终点")
    waypoints: List[RoutePoint] = Field(default_factory=list, description="途经点")
    distance: int = Field(default=0, description="距离（米）")
    duration: int = Field(default=0, description="时间（秒）")
    polyline: List[RoutePoint] = Field(default_factory=list, description="路线折线点")


class DayPlan(BaseModel):
    """单日行程"""
    date: str = Field(..., description="日期")
    day_index: int = Field(..., description="第几天(从0开始)")
    description: str = Field(..., description="当日行程描述")
    transportation: str = Field(..., description="交通方式")
    accommodation: str = Field(..., description="住宿安排")
    hotel: Optional[Hotel] = Field(default=None, description="酒店信息")
    attractions: List[Attraction] = Field(default_factory=list, description="景点列表")
    meals: List[Meal] = Field(default_factory=list, description="餐饮安排")
    route: Optional[RouteInfo] = Field(default=None, description="路线规划信息")


class Budget(BaseModel):
    """预算信息"""
    total_attractions: int = Field(default=0, description="景点门票总费用")
    total_hotels: int = Field(default=0, description="酒店总费用")
    total_meals: int = Field(default=0, description="餐饮总费用")
    total_transportation: int = Field(default=0, description="交通总费用")
    total: int = Field(default=0, description="总费用")


class TripPlan(BaseModel):
    """旅行计划"""
    city: str = Field(..., description="目的地城市")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    days: List[DayPlan] = Field(default_factory=list, description="每日行程")
    weather_info: List[WeatherInfo] = Field(default_factory=list, description="天气信息")
    overall_suggestions: str = Field(default="", description="总体建议")
    budget: Optional[Budget] = Field(default=None, description="预算信息")


class TripRequest(BaseModel):
    """旅行规划请求"""
    city: str = Field(..., description="目的地城市")
    start_date: str = Field(..., description="开始日期")
    end_date: str = Field(..., description="结束日期")
    days: int = Field(..., description="旅行天数", ge=1, le=7)
    preferences: str = Field(default="历史文化", description="旅行偏好")
    budget: str = Field(default="中等", description="预算级别")
    transportation: str = Field(default="公共交通", description="交通方式")
    accommodation: str = Field(default="经济型酒店", description="住宿类型")