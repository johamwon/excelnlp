"""
设备控制器

基于开源项目 uiautomator2 (https://github.com/openatx/uiautomator2) 封装，
通过 ADB 控制 Android / 小米手机：打开 App、读取界面元素、点击、滑动、输入文本等。

uiautomator2 是目前最主流的开源 Android UI 自动化库，对小米 MIUI/HyperOS 兼容良好。
"""
import re
import time
from typing import Dict, List, Optional, Any, Tuple
from xml.etree import ElementTree

from loguru import logger

try:
    import uiautomator2 as u2
except ImportError:
    u2 = None
    logger.warning("uiautomator2 库未安装，请运行: pip install uiautomator2")


# bounds 字符串形如 "[x1,y1][x2,y2]"
_BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def _parse_bounds(bounds: str) -> Optional[Tuple[int, int, int, int]]:
    """解析 bounds 字符串为 (x1, y1, x2, y2)"""
    m = _BOUNDS_RE.match(bounds or "")
    if not m:
        return None
    x1, y1, x2, y2 = (int(v) for v in m.groups())
    return x1, y1, x2, y2


class Device:
    """Android / 小米手机设备控制器"""

    def __init__(self, serial: Optional[str] = None):
        """
        初始化设备连接

        Args:
            serial: 设备序列号（adb devices 中显示的 ID）。
                    为 None 时连接默认设备（USB 或唯一的网络设备）。
        """
        if u2 is None:
            raise ImportError("uiautomator2 库未安装，请运行: pip install uiautomator2")

        self.serial = serial
        logger.info(f"正在连接设备: {serial or '默认设备'} ...")
        # u2.connect 支持 None / 序列号 / IP
        self.d = u2.connect(serial) if serial else u2.connect()
        info = self.d.info
        logger.info(
            f"设备连接成功: {info.get('productName')} "
            f"分辨率={info.get('displayWidth')}x{info.get('displayHeight')}"
        )

    # ------------------------------------------------------------------ App 操作
    def open_app(self, package_name: str, wait: float = 3.0) -> None:
        """
        启动指定包名的 App

        Args:
            package_name: 应用包名，如 com.xiaomi.shop
            wait: 启动后等待秒数
        """
        logger.info(f"启动 App: {package_name}")
        self.d.app_start(package_name, stop=False)
        time.sleep(wait)

    def stop_app(self, package_name: str) -> None:
        """停止指定 App"""
        logger.info(f"停止 App: {package_name}")
        self.d.app_stop(package_name)

    def current_app(self) -> Dict[str, Any]:
        """获取当前前台 App 信息"""
        return self.d.app_current()

    def list_installed_apps(self) -> List[str]:
        """列出已安装的应用包名"""
        return self.d.app_list()

    # ------------------------------------------------------------------ 界面感知
    def get_screen_size(self) -> Tuple[int, int]:
        """获取屏幕宽高 (width, height)"""
        info = self.d.info
        return info["displayWidth"], info["displayHeight"]

    def screenshot(self, path: Optional[str] = None):
        """
        截屏

        Args:
            path: 保存路径，为 None 时返回 PIL.Image 对象

        Returns:
            PIL.Image 或 None（已保存到文件）
        """
        if path:
            self.d.screenshot(path)
            logger.debug(f"截屏已保存: {path}")
            return None
        return self.d.screenshot()

    def get_elements(self, only_interactive: bool = False) -> List[Dict[str, Any]]:
        """
        提取当前界面的 UI 元素列表（供 LLM 决策）

        通过 dump_hierarchy 获取界面层级 XML 并解析，每个元素带有稳定的索引，
        LLM 通过索引来指定要操作的目标。

        Args:
            only_interactive: 仅返回可点击 / 可输入的元素

        Returns:
            元素列表，每项含 index/text/resource_id/class/desc/clickable/bounds/center
        """
        xml = self.d.dump_hierarchy()
        root = ElementTree.fromstring(xml)

        elements: List[Dict[str, Any]] = []
        for node in root.iter("node"):
            attrib = node.attrib
            bounds = _parse_bounds(attrib.get("bounds", ""))
            if bounds is None:
                continue

            text = (attrib.get("text") or "").strip()
            desc = (attrib.get("content-desc") or "").strip()
            clickable = attrib.get("clickable") == "true"
            editable = attrib.get("class", "").endswith("EditText")
            has_label = bool(text or desc)

            # 过滤：只保留对决策有意义的节点
            if only_interactive and not (clickable or editable):
                continue
            if not (clickable or editable or has_label):
                continue

            x1, y1, x2, y2 = bounds
            elements.append(
                {
                    "index": len(elements),
                    "text": text,
                    "desc": desc,
                    "resource_id": attrib.get("resource-id", ""),
                    "class": attrib.get("class", ""),
                    "clickable": clickable,
                    "editable": editable,
                    "bounds": bounds,
                    "center": ((x1 + x2) // 2, (y1 + y2) // 2),
                }
            )

        logger.debug(f"提取到 {len(elements)} 个界面元素")
        return elements

    # ------------------------------------------------------------------ 交互动作
    def tap(self, x: int, y: int) -> None:
        """点击坐标"""
        logger.debug(f"点击坐标: ({x}, {y})")
        self.d.click(x, y)

    def tap_element(self, element: Dict[str, Any]) -> None:
        """点击元素（使用其中心坐标）"""
        cx, cy = element["center"]
        label = element.get("text") or element.get("desc") or element.get("resource_id")
        logger.info(f"点击元素 [{element['index']}] '{label}' @ ({cx}, {cy})")
        self.tap(cx, cy)

    def input_text(self, text: str, element: Optional[Dict[str, Any]] = None,
                   clear: bool = True) -> None:
        """
        输入文本

        Args:
            text: 要输入的内容
            element: 目标输入框元素，提供时会先点击聚焦
            clear: 输入前是否清空已有内容
        """
        if element is not None:
            self.tap_element(element)
            time.sleep(0.5)
        if clear:
            self.d.clear_text()
        logger.info(f"输入文本: {text}")
        self.d.send_keys(text)

    def swipe(self, direction: str, scale: float = 0.6) -> None:
        """
        在屏幕中央按方向滑动

        Args:
            direction: up / down / left / right
            scale: 滑动距离占屏幕比例 (0-1)
        """
        w, h = self.get_screen_size()
        cx, cy = w // 2, h // 2
        dx = int(w * scale / 2)
        dy = int(h * scale / 2)
        targets = {
            "up": (cx, cy + dy, cx, cy - dy),
            "down": (cx, cy - dy, cx, cy + dy),
            "left": (cx + dx, cy, cx - dx, cy),
            "right": (cx - dx, cy, cx + dx, cy),
        }
        if direction not in targets:
            raise ValueError(f"不支持的滑动方向: {direction}")
        x1, y1, x2, y2 = targets[direction]
        logger.info(f"滑动: {direction}")
        self.d.swipe(x1, y1, x2, y2, duration=0.3)

    def press_back(self) -> None:
        """按返回键"""
        logger.info("按返回键")
        self.d.press("back")

    def press_home(self) -> None:
        """按 Home 键"""
        logger.info("按 Home 键")
        self.d.press("home")

    def wait(self, seconds: float = 1.0) -> None:
        """等待"""
        time.sleep(seconds)
