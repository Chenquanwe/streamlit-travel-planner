"""
图片服务 - 为景点提供配图

功能：
1. 优先使用 Pexels API 获取高质量景点图片
2. 如果 Pexels 失败或未配置，返回默认图片
3. 支持批量处理，为整个旅行计划的景点添加图片

图片来源优先级：
1. Pexels API（免费，200次/小时）
2. 根据景点类型匹配的默认图片
3. 随机旅行风格图片
"""

# ==================== 标准库导入 ====================
import requests      # HTTP 请求，用于调用 Pexels API
import os            # 读取环境变量（API Key）
import re            # 正则表达式，用于清理搜索关键词
import random        # 随机选择默认图片
from typing import List, Dict, Optional  # 类型注解

# ==================== 项目内部导入 ====================
from models.schemas import TripPlan, Attraction  # 数据模型
import logging
logger = logging.getLogger(__name__)


class ImageService:
    """
    图片服务类

    职责：为景点名称提供配图 URL

    工作流程：
    1. 接收景点名称和城市作为查询词
    2. 清理关键词（移除特殊字符、限制长度）
    3. 调用 Pexels API 搜索图片
    4. 如果失败，根据关键词类型返回默认图片

    使用示例：
        service = ImageService()
        url = service.get_photo_url("南京博物院")
        # 返回: https://images.pexels.com/xxx.jpg
    """

    def __init__(self):
        """
        初始化图片服务

        从环境变量读取 API Key：
        - PEXELS_API_KEY: Pexels 的 API Key（推荐，免费注册）
        - UNSPLASH_ACCESS_KEY: Unsplash 的 API Key（备用，但已不推荐）
        """
        # Pexels API Key（推荐使用，200次/小时免费额度）
        self.pexels_key = os.getenv("PEXELS_API_KEY")
        # Unsplash API Key（备用，API 版本已过时，可能失效）
        self.unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")

    def get_photo_url(self, query: str) -> Optional[str]:
        """
        获取图片 URL - 主要的对外接口

        工作流程：
        1. 清理关键词（移除特殊字符）
        2. 如果有 Pexels Key，调用 Pexels API
        3. 如果成功，返回图片 URL
        4. 如果失败，返回默认图片

        Args:
            query: 搜索关键词，如 "南京博物院" 或 "中山陵 南京"

        Returns:
            Optional[str]: 图片 URL，如果获取失败返回 None（实际会返回默认图片）
        """
        # ----- 步骤1：清理关键词 -----
        # 移除括号、特殊字符，限制长度
        cleaned = self._clean_query(query)

        # ----- 步骤2：优先使用 Pexels -----
        if self.pexels_key:
            url = self._get_pexels_photo(cleaned)
            if url:
                return url  # Pexels 成功，返回图片

        # ----- 步骤3：备用方案：返回默认图片 -----
        # 当 Pexels 失败或未配置时，使用默认图片
        return self._get_default_photo(cleaned)

    def _clean_query(self, query: str) -> str:
        """
        清理搜索关键词

        为什么需要清理？
        - 景点名称可能包含括号：如"夫子庙（秦淮河）"
        - 高德 API 返回的名称可能包含特殊字符
        - Pexels API 对特殊字符敏感，可能导致搜索失败

        清理规则：
        1. 移除中文括号：（）【】
        2. 移除英文括号：()
        3. 移除百分号：%
        4. 限制长度不超过30字符（Pexels 对长关键词支持不好）

        Args:
            query: 原始关键词，如 "夫子庙（秦淮河风光带）"

        Returns:
            str: 清理后的关键词，如 "夫子庙"
        """
        # 移除中文括号和英文括号
        # [（）()【】\[] 匹配：中文括号、英文括号、方括号
        cleaned = re.sub(r'[（）()【】\[]', '', query)

        # 移除百分号（高德 API 返回的某些字段可能包含 %）
        cleaned = re.sub(r'[%]', '', cleaned)

        # 限制长度，避免搜索词过长
        if len(cleaned) > 30:
            cleaned = cleaned[:30]

        return cleaned.strip()

    def _get_pexels_photo(self, query: str) -> Optional[str]:
        """
        从 Pexels API 获取图片

        Pexels API 说明：
        - 文档：https://www.pexels.com/api/
        - 免费额度：200次/小时
        - 返回格式：JSON，包含图片 URL

        API 请求示例：
        GET https://api.pexels.com/v1/search?query=南京&per_page=1
        Headers: Authorization: your-api-key

        响应示例：
        {
            "photos": [
                {
                    "src": {
                        "medium": "https://images.pexels.com/xxx.jpg"
                    }
                }
            ]
        }

        Args:
            query: 清理后的搜索关键词

        Returns:
            Optional[str]: 图片 URL，失败返回 None
        """
        # Pexels API 端点
        url = "https://api.pexels.com/v1/search"

        # 请求头：使用 Bearer Token 认证
        headers = {"Authorization": self.pexels_key}

        # 请求参数：查询词和每页数量
        params = {"query": query, "per_page": 1}

        try:
            # 发送 GET 请求，超时10秒
            response = requests.get(url, headers=headers, params=params, timeout=10)

            # 检查 HTTP 状态码
            if response.status_code == 200:
                data = response.json()          # 解析 JSON
                photos = data.get("photos", []) # 获取图片列表

                if photos:
                    # 返回中等尺寸的图片 URL
                    # src.medium 是 1080px 宽度的图片
                    return photos[0].get("src", {}).get("medium")

        except Exception as e:
            # 记录错误但不中断程序
            print(f"Pexels 搜索失败: {e}")

        return None

    def _get_default_photo(self, query: str) -> str:
        """
        返回默认图片

        当 Pexels API 失败时，根据关键词类型返回合适的默认图片。

        匹配策略：
        1. 检查关键词中是否包含特定类型词
        2. 如果匹配，返回对应类型的默认图片
        3. 如果不匹配，随机返回旅行风格图片

        Args:
            query: 搜索关键词（用于类型匹配）

        Returns:
            str: 默认图片 URL
        """
        # 类型关键词 → 默认图片 URL 的映射
        default_images = {
            "博物馆": "https://images.pexels.com/photos/207896/pexels-photo-207896.jpeg",
            "公园": "https://images.pexels.com/photos/2387873/pexels-photo-2387873.jpeg",
            "山": "https://images.pexels.com/photos/1365425/pexels-photo-1365425.jpeg",
            "湖": "https://images.pexels.com/photos/210186/pexels-photo-210186.jpeg",
            "寺": "https://images.pexels.com/photos/2945264/pexels-photo-2945264.jpeg",
            "广场": "https://images.pexels.com/photos/466685/pexels-photo-466685.jpeg",
        }

        # 遍历映射，检查关键词是否包含类型词
        for key, url in default_images.items():
            if key in query:
                return url  # 匹配成功，返回对应图片

        # 没有匹配到特定类型，随机返回旅行风格图片
        travel_images = [
            "https://images.pexels.com/photos/338515/pexels-photo-338515.jpeg",  # 海滩
            "https://images.pexels.com/photos/417074/pexels-photo-417074.jpeg",  # 山脉
            "https://images.pexels.com/photos/361104/pexels-photo-361104.jpeg",  # 城市
        ]
        return random.choice(travel_images)


# ==================== 全局单例 ====================
# 使用单例模式，避免重复创建实例
_image_service = None


def get_image_service() -> ImageService:
    """
    获取图片服务单例

    单例模式的好处：
    - 避免重复创建实例
    - 共享 API Key 等配置
    - 减少内存占用

    Returns:
        ImageService: 图片服务实例
    """
    global _image_service
    if _image_service is None:
        _image_service = ImageService()
    return _image_service


# ==================== 批量处理函数 ====================
def enrich_attractions_with_images(trip_plan: TripPlan) -> TripPlan:
    """
    为旅行计划中的所有景点添加图片

    这是主要的对外接口，在 TravelSupervisor 中调用。

    工作流程：
    1. 遍历每一天的行程
    2. 遍历每个景点
    3. 如果景点还没有图片，获取图片 URL
    4. 将图片 URL 添加到景点对象

    Args:
        trip_plan: 旅行计划对象（包含所有景点）

    Returns:
        TripPlan: 添加了图片 URL 后的旅行计划对象（原地修改）

    使用示例：
        trip_plan = enrich_attractions_with_images(trip_plan)
        for day in trip_plan.days:
            for attr in day.attractions:
                print(attr.image_url)  # 现在有图片了
    """
    # 获取图片服务单例
    service = get_image_service()

    # 遍历每一天
    for day in trip_plan.days:
        # 遍历每个景点
        for attraction in day.attractions:
            # 如果还没有图片，获取一张
            if not attraction.image_url:
                # 搜索词 = 景点名称 + 城市，提高匹配度
                query = f"{attraction.name} {trip_plan.city}"
                attraction.image_url = service.get_photo_url(query)

    return trip_plan