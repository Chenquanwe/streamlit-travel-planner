"""
多智能体模块 - 智能旅行助手的核心模块

本模块定义了旅行规划系统中所有智能体（Agent）的导出接口。
智能体采用分层架构：基类 + 具体专家 + 监督者模式。

架构说明：
┌─────────────────────────────────────────────────────────────┐
│                    TravelSupervisor                         │
│                      (监督者/协调者)                         │
│           负责协调各个专家Agent，编排执行流程                  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│Attraction     │    │Weather        │    │Hotel          │
│SearchAgent    │    │QueryAgent     │    │Agent          │
│  景点搜索专家  │    │  天气查询专家  │    │  酒店推荐专家  │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌───────────────┐
                    │ PlannerAgent  │
                    │  行程规划专家  │
                    │ 整合所有信息   │
                    │ 生成最终计划   │
                    └───────────────┘

所有Agent都继承自 BaseTravelAgent 基类
"""

# ==================== 导入声明 ====================
# 导入基础Agent类 - 所有Agent的父类，提供通用的run()方法和工具调用机制
from agents.base_agent import BaseTravelAgent

# 导入景点搜索Agent - 负责搜索指定城市的景点信息
from agents.attraction_agent import AttractionSearchAgent

# 导入天气查询Agent - 负责查询指定城市的天气预报
from agents.weather_agent import WeatherQueryAgent

# 导入酒店推荐Agent - 负责推荐指定城市的酒店
from agents.hotel_agent import HotelAgent

# 导入行程规划Agent - 负责整合景点、天气、酒店信息，生成完整旅行计划
from agents.planner_agent import PlannerAgent

# 导入监督者 - 多智能体系统的总协调器，负责编排和执行整个规划流程
from agents.supervisor import TravelSupervisor


# ==================== 公开接口定义 ====================
# __all__ 定义了当使用 "from agents import *" 时会导出的模块
# 这既是API文档，也是模块的公开接口边界
__all__ = [
    # 基础类 - 用于扩展自定义Agent时继承
    "BaseTravelAgent",

    # 具体专家Agent - 可直接使用或继承扩展
    "AttractionSearchAgent",   # 景点搜索专家
    "WeatherQueryAgent",       # 天气查询专家
    "HotelAgent",              # 酒店推荐专家
    "PlannerAgent",            # 行程规划专家

    # 监督者 - 多智能体系统的入口和协调器
    "TravelSupervisor",        # 旅行规划监督者（主控制器）
]