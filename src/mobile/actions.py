"""
动作定义与执行

Agent 的每一步决策都被表示为一个标准化的 action 字典，由本模块统一执行。
这样新增 / 修改动作时，只需改这里，便于后续定制。

action 字典格式::

    {
        "thought": "为什么这么做",     # LLM 的推理（可选）
        "action": "tap",              # 动作类型，见 ACTION_TYPES
        "index": 5,                   # tap / input 的目标元素索引
        "text": "你好",               # input 要输入的文本
        "direction": "up",           # swipe 的方向
        "app": "微信"                # open_app 的目标
    }
"""
from typing import Dict, List, Any, Optional

from loguru import logger

from .device import Device
from .apps import resolve_package

# 支持的动作类型及说明（同时作为给 LLM 的提示）
ACTION_TYPES: Dict[str, str] = {
    "tap": "点击一个元素，需提供 index（元素索引）",
    "input": "向输入框输入文本，需提供 index 和 text",
    "swipe": "滑动屏幕，需提供 direction (up/down/left/right)",
    "open_app": "打开一个 App，需提供 app（名称或包名）",
    "back": "按返回键",
    "home": "回到桌面",
    "wait": "等待一会儿（界面加载中）",
    "done": "任务已完成，结束",
}

# JSON Schema —— 用于 Claude 结构化输出，约束模型只产出合法动作
ACTION_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "thought": {"type": "string", "description": "对当前界面的分析与下一步理由"},
        "action": {"type": "string", "enum": list(ACTION_TYPES.keys())},
        "index": {"type": ["integer", "null"], "description": "目标元素索引"},
        "text": {"type": ["string", "null"], "description": "要输入的文本"},
        "direction": {
            "type": ["string", "null"],
            "enum": ["up", "down", "left", "right", None],
        },
        "app": {"type": ["string", "null"], "description": "要打开的 App"},
    },
    "required": ["thought", "action"],
    "additionalProperties": False,
}


class ActionExecutor:
    """根据 action 字典在设备上执行对应操作"""

    def __init__(self, device: Device):
        self.device = device

    def execute(self, action: Dict[str, Any], elements: List[Dict[str, Any]]) -> bool:
        """
        执行一个动作

        Args:
            action: 动作字典
            elements: 当前界面元素列表（用于按 index 定位）

        Returns:
            是否应继续（False 表示任务结束）
        """
        act = action.get("action")
        thought = action.get("thought", "")
        if thought:
            logger.info(f"💭 {thought}")

        if act == "done":
            logger.success("任务完成 ✅")
            return False

        if act == "tap":
            element = self._get_element(action, elements)
            if element is not None:
                self.device.tap_element(element)

        elif act == "input":
            element = self._get_element(action, elements)
            text = action.get("text") or ""
            self.device.input_text(text, element=element)

        elif act == "swipe":
            self.device.swipe(action.get("direction", "up"))

        elif act == "open_app":
            self._open_app(action.get("app", ""))

        elif act == "back":
            self.device.press_back()

        elif act == "home":
            self.device.press_home()

        elif act == "wait":
            self.device.wait(2.0)

        else:
            logger.warning(f"未知动作: {act}，跳过")

        self.device.wait(1.5)  # 等界面响应
        return True

    def _get_element(self, action: Dict[str, Any],
                     elements: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """按 index 取元素，越界时返回 None"""
        index = action.get("index")
        if index is None or not (0 <= index < len(elements)):
            logger.warning(f"元素索引无效: {index}")
            return None
        return elements[index]

    def _open_app(self, app: str) -> None:
        """打开 App（名称会先解析成包名）"""
        package = resolve_package(app)
        if not package:
            logger.warning(f"无法识别 App: {app}，请在 apps.py 中补充包名")
            return
        self.device.open_app(package)


def annotate_screenshot(image, elements: List[Dict[str, Any]], output_path: str):
    """
    在截图上为可交互元素绘制带编号的方框（Set-of-Mark 标注）

    给视觉模型（如 Claude）看带编号的截图，模型直接返回要点击的编号，
    定位更准。这是 AppAgent / Mobile-Agent 等开源项目的常用做法。

    Args:
        image: PIL.Image 截图
        elements: 元素列表
        output_path: 标注后图片保存路径
    """
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 28)
    except Exception:
        font = ImageFont.load_default()

    for el in elements:
        if not (el["clickable"] or el["editable"]):
            continue
        x1, y1, x2, y2 = el["bounds"]
        draw.rectangle([x1, y1, x2, y2], outline=(255, 0, 0), width=3)
        label = str(el["index"])
        # 编号底色块，避免与界面文字混淆
        draw.rectangle([x1, y1, x1 + 14 * len(label) + 8, y1 + 32], fill=(255, 0, 0))
        draw.text((x1 + 4, y1), label, fill=(255, 255, 255), font=font)

    image.save(output_path)
    logger.debug(f"标注截图已保存: {output_path}")
    return output_path
