"""
手机自动化 Agent 模块

基于开源 uiautomator2 + LLM，实现「用自然语言操控 Android / 小米手机」。

快速使用::

    from src.mobile import Device, MobileAgent, create_brain

    device = Device()                                   # 连接手机
    brain = create_brain("claude")                      # 选择决策大脑
    agent = MobileAgent(device, brain)
    agent.run("打开设置，进入WLAN页面")
"""
from .device import Device
from .actions import ActionExecutor
from .llm import Brain, ClaudeBrain, OllamaBrain, LocalVisionBrain, create_brain
from .agent import MobileAgent

__all__ = [
    "Device",
    "ActionExecutor",
    "Brain",
    "ClaudeBrain",
    "OllamaBrain",
    "LocalVisionBrain",
    "create_brain",
    "MobileAgent",
]
