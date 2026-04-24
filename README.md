# ✈️ 智能旅行助手

基于 LangChain 多智能体架构的智能旅行规划应用。

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
- Streamlit

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/你的用户名/streamlit-travel-planner.git
   cd streamlit-travel-planner
2、创建并激活虚拟环境
  # Windows
  python -m venv venv
  venv\Scripts\activate
  
  # macOS/Linux
  python3 -m venv venv
  source venv/bin/activate
3、安装依赖
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
4、配置环境变量
  复制 .env.example 并重命名为 .env
  填入你的 API 密钥
5、运行应用
  streamlit run app.py
📁 项目结构
  streamlit-travel-planner/
  ├── app.py                 # Streamlit 主入口
  ├── amap_mcp_server.py     # MCP 服务器（可选）
  ├── agents/                # 多智能体模块
  │   ├── base_agent.py      # Agent 基类
  │   ├── attraction_agent.py # 景点搜索
  │   ├── weather_agent.py    # 天气查询
  │   ├── hotel_agent.py      # 酒店推荐
  │   ├── planner_agent.py    # 行程规划
  │   └── supervisor.py       # 监督者
  ├── tools/                  # 工具模块
  │   └── amap_tools.py       # 高德地图工具
  ├── services/               # 服务模块
  │   └── image_service.py    # 图片服务
  ├── models/                 # 数据模型
  │   └── schemas.py          # Pydantic 模型
  ├── ui/                     # 前端界面
  │   ├── home.py             # 表单页面
  │   ├── result.py           # 结果展示
  │   ├── components.py       # UI 组件
  │   └── styles.py           # CSS 样式
  └── requirements.txt        # 依赖清单
❓ 常见问题
地图无法显示
检查 .env 中的 AMAP_WEB_KEY 是否配置正确

确保 Key 类型是 Web端(JS API)

API 调用失败
检查 LLM_API_KEY（阿里云百炼）是否有效

检查 AMAP_API_KEY（高德 Web服务）是否有效

📄 许可证
MIT License
