"""
手机自动化 Agent —— 命令行入口

用法示例::

    # 用一句话指挥手机（从配置文件读取设置）
    python mobile_agent.py "打开设置，进入WLAN页面"

    # 指定使用本地 Ollama 模型、关闭视觉
    python mobile_agent.py "打开计算器" --provider ollama --no-vision

    # 进入交互模式，连续下达多个任务
    python mobile_agent.py

准备工作见 MOBILE_AGENT.md（小米手机需先开启 USB 调试）。
"""
import argparse
import sys

import yaml
from loguru import logger

from src.mobile import Device, MobileAgent, create_brain


def load_config(path: str = "configs/mobile_config.yaml") -> dict:
    """加载配置文件，文件不存在时返回空配置"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning(f"配置文件不存在: {path}，使用默认配置")
        return {}


def build_agent(config: dict, provider_override: str = None,
                use_vision_override: bool = None) -> MobileAgent:
    """根据配置构建 Agent"""
    device_cfg = config.get("device", {})
    brain_cfg = config.get("brain", {})
    agent_cfg = config.get("agent", {})

    # 连接设备
    serial = device_cfg.get("serial") or None
    device = Device(serial=serial)

    # 构建决策大脑
    provider = provider_override or brain_cfg.get("provider", "claude")
    if provider == "claude":
        c = brain_cfg.get("claude", {})
        brain = create_brain(
            "claude",
            model=c.get("model", "claude-opus-4-8"),
            api_key=c.get("api_key") or None,
            use_thinking=c.get("use_thinking", True),
        )
    else:
        o = brain_cfg.get("ollama", {})
        brain = create_brain(
            "ollama",
            model=o.get("model", "qwen2.5:7b"),
            host=o.get("host", "http://localhost:11434"),
        )

    use_vision = use_vision_override if use_vision_override is not None \
        else agent_cfg.get("use_vision", True)
    # 本地文本模型默认不发截图
    if provider == "ollama" and use_vision_override is None:
        use_vision = False

    return MobileAgent(
        device=device,
        brain=brain,
        max_steps=agent_cfg.get("max_steps", 15),
        use_vision=use_vision,
    )


def main():
    parser = argparse.ArgumentParser(description="用自然语言操控 Android / 小米手机")
    parser.add_argument("task", nargs="?", help="要执行的任务，如「打开微信」；不填则进入交互模式")
    parser.add_argument("--config", default="configs/mobile_config.yaml", help="配置文件路径")
    parser.add_argument("--provider", choices=["claude", "ollama"], help="覆盖决策器类型")
    parser.add_argument("--no-vision", action="store_true", help="不向决策器发送截图")
    args = parser.parse_args()

    config = load_config(args.config)
    use_vision = False if args.no_vision else None

    try:
        agent = build_agent(config, provider_override=args.provider,
                            use_vision_override=use_vision)
    except Exception as e:
        logger.error(f"初始化失败: {e}")
        logger.error("请确认：手机已连 ADB（adb devices 可见）、已开启 USB 调试。详见 MOBILE_AGENT.md")
        sys.exit(1)

    if args.task:
        agent.run(args.task)
    else:
        # 交互模式
        logger.info("进入交互模式，输入任务后回车执行，输入 q 退出。")
        while True:
            try:
                task = input("\n任务> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if task.lower() in ("q", "quit", "exit"):
                break
            if task:
                agent.run(task)


if __name__ == "__main__":
    main()
