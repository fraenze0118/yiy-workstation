"""
VC-Keyboard App Definition

每个应用模块提供一个 AppDefinition 实例 (APP) 和一个 main() 函数。
"""

from dataclasses import dataclass, field


@dataclass
class AppDefinition:
    """应用定义 — Launcher 通过此元数据显示应用卡片并启动子进程"""

    id: str                 # 唯一标识, 如 "tomato"
    name: str               # 显示名称, 如 "Tomato"
    name_zh: str            # 中文名, 如 "番茄钟"
    description: str        # 简短描述 (英文)
    icon: str               # emoji 图标, 如 "🍅"
    category: str           # "tool" | "test" | "game" | "demo"

    # 操作提示 — 在 Launcher 运行中视图展示
    controls: dict = field(default_factory=dict)
    # {"KEY1": "开始/暂停", "KEY5": "重置", "编码器": "调时长"}

    # 入口: 子进程调用的 Python 模块路径
    module: str = ""

    # 依赖: 需要额外安装的 Python 包
    requires: list = field(default_factory=list)
