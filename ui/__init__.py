"""UI 组件模块 - Streamlit 界面组件"""

from ui.styles import MAIN_STYLES, SIDEBAR_STYLES
from ui.components import (
    show_header,
    show_sidebar_info,

    show_loading_progress,
    update_progress,

)
from ui.home import show_home_form
from ui.result import ResultDisplay, display_result

__all__ = [
    # 样式
    "MAIN_STYLES",
    "SIDEBAR_STYLES",
    # 通用组件
    "show_header",
    "show_sidebar_info",

    "show_loading_progress",
    "update_progress",

    # 页面
    "show_home_form",
    "ResultDisplay",
    "display_result",
]