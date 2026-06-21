"""
手机自动化 Agent

把「设备控制 + 界面感知 + LLM 决策 + 动作执行」组装成一个感知-决策-执行循环：

    while 未完成 and 未超过最大步数:
        1. 截屏 + 提取界面元素（感知）
        2. 交给 LLM 决定下一步动作（决策）
        3. 执行动作（执行）

这是 AppAgent / Mobile-Agent 等开源手机 Agent 的通用范式，结构清晰，便于定制。
"""
import os
import tempfile
from typing import Optional

from loguru import logger

from .device import Device
from .actions import ActionExecutor, annotate_screenshot
from .llm import Brain


class MobileAgent:
    """手机自动化 Agent"""

    def __init__(self, device: Device, brain: Brain,
                 max_steps: int = 15, use_vision: bool = True,
                 work_dir: Optional[str] = None):
        """
        Args:
            device: 设备控制器
            brain: LLM 决策器
            max_steps: 单个任务最大步数（防止死循环）
            use_vision: 是否给决策器发送标注截图（Claude 推荐 True）
            work_dir: 截图等中间文件目录
        """
        self.device = device
        self.brain = brain
        self.executor = ActionExecutor(device)
        self.max_steps = max_steps
        self.use_vision = use_vision
        self.work_dir = work_dir or os.path.join(tempfile.gettempdir(), "mobile_agent")
        os.makedirs(self.work_dir, exist_ok=True)

    def run(self, task: str) -> bool:
        """
        执行一个自然语言任务

        Args:
            task: 任务描述，如「打开微信，给文件传输助手发一条消息：你好」

        Returns:
            是否正常完成
        """
        logger.info(f"========== 开始任务: {task} ==========")
        history = []

        for step in range(1, self.max_steps + 1):
            logger.info(f"--- 第 {step}/{self.max_steps} 步 ---")

            # 1. 感知：提取元素 + （可选）标注截图
            elements = self.device.get_elements()
            screenshot_path = None
            if self.use_vision:
                image = self.device.screenshot()
                screenshot_path = os.path.join(self.work_dir, f"step_{step}.png")
                annotate_screenshot(image, elements, screenshot_path)

            # 2. 决策
            try:
                action = self.brain.decide(task, elements, history, screenshot_path)
            except Exception as e:
                logger.error(f"决策失败: {e}")
                return False

            history.append(
                f"第{step}步: {action.get('action')} "
                f"(index={action.get('index')}, text={action.get('text')})"
            )

            # 3. 执行
            should_continue = self.executor.execute(action, elements)
            if not should_continue:
                logger.success(f"========== 任务结束 (共 {step} 步) ==========")
                return True

        logger.warning(f"已达最大步数 {self.max_steps}，任务未明确完成")
        return False
