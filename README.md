# ✈️ 智能旅行助手

基于 LangChain 多智能体架构的智能旅行规划应用。
本项目是在学习黑马程序员langchain教程的基础上，开发的基于 LangChain 多智能体架构的智能旅行规划应用主要拓展了多智能体应用和使用mcp协议封装工具的功能。系统以 Streamlit 构建现代化 Web 界面，后端基于多智能体协作框架，整合高德地图 API 与 MCP 协议，实现从景点搜索、天气查询、酒店推荐到行程规划的全流程智能化服务。

## ✨ 功能特性

- 🤖 **多智能体协作**: 景点搜索、天气查询、酒店推荐、行程规划
- 🗺️ **地图路线**: 基于高德地图的景点标记和路线规划
- 🌤️ **实时天气**: 集成高德天气 API
- 📸 **智能配图**: 自动为景点获取图片
- 💰 **预算管理**: 自动计算旅行预算

## 🛠️ 技术栈

- **前端**: Streamlit
- **AI 框架**: LangChain
- **大模型**: 阿里云百炼 (Qwen)
- **地图服务**: 高德地图 API
- **图片服务**: Pexels API

## 🚀 快速开始

### 环境要求
- Python 3.10+
### 获取 API 密钥
你需要准备以下 API 密钥：
| 服务 | 说明 | 获取地址 |
|------|------|----------|
| LLM API | 阿里云百炼 API Key | https://bailian.console.aliyun.com/ |
| 高德地图 Web服务 Key | 用于景点搜索、天气查询 | https://console.amap.com/ |
| 高德地图 Web端 Key | 用于前端地图显示 | https://console.amap.com/ |
| Pexels API Key | 用于景点图片（可选） | https://www.pexels.com/api/ |
### 安装步骤
#### 1. 克隆项目或直接下载 ZIP
克隆项目：git clone https://github.com/Chenquanwe/streamlit-travel-planner.git

直接下载：访问 https://github.com/Chenquanwe/streamlit-travel-planner ，点击绿色的 "Code" 按钮
#### 2.进入目录
cd streamlit-travel-planner
#### 3. 安装依赖
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
#### 4. 配置环境变量
##### 复制 .env.example 并重命名为 .env，然后填入你的 API 密钥
```text
# 阿里云百炼配置
LLM_API_KEY=sk-你的API密钥
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus

# 高德地图配置
AMAP_API_KEY=你的高德Web服务Key
AMAP_WEB_KEY=你的高德Web端JS API Key

# Pexels 图片API（可选）
PEXELS_API_KEY=你的Pexels API Key
```
#### 5. 运行应用
streamlit run app.py
## 📁 项目结构
```text
streamlit-travel-planner/
├── app.py                      # Streamlit 主入口
├── amap_mcp_server.py          # MCP 服务器（可选）
├── requirements.txt            # Python 依赖清单
├── .env.example                # 环境变量模板
├── .gitignore                  # Git 忽略文件
├── README.md                   # 项目说明文档
│
├── agents/                     # 多智能体模块
│   ├── __init__.py
│   ├── base_agent.py           # Agent 基类
│   ├── attraction_agent.py     # 景点搜索
│   ├── weather_agent.py        # 天气查询
│   ├── hotel_agent.py          # 酒店推荐
│   ├── planner_agent.py        # 行程规划
│   └── supervisor.py           # 监督者
│
├── models/                     # 数据模型模块
│   ├── __init__.py
│   └── schemas.py              # Pydantic 模型
│
├── services/                   # 服务模块
│   ├── __init__.py
│   └── image_service.py        # 图片服务
│
├── tools/                      # 工具模块
│   ├── __init__.py
│   └── amap_tools.py           # 高德地图工具
│
└── ui/                         # 前端界面模块
    ├── __init__.py
    ├── home.py                 # 首页表单
    ├── result.py               # 结果展示
    ├── components.py           # UI 组件
    └── styles.py               # CSS 样式
```
## ❓ 常见问题
地图无法显示
检查 .env 中的 AMAP_WEB_KEY 是否配置正确

确保 Key 类型是 Web端(JS API)

API 调用失败
检查 LLM_API_KEY（阿里云百炼）是否有效

检查 AMAP_API_KEY（高德 Web服务）是否有效

## 📄 许可证
MIT License
