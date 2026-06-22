"""
Agent 大脑（LLM 决策器）

负责：给定「任务 + 当前界面」，输出下一步动作（action 字典）。
做成可插拔，方便后续定制 / 更换模型：

- ClaudeBrain      : 调用 Claude（多模态），直接「看」带编号的截图来决策，能力最强（推荐）。
- OllamaBrain      : 调用本地 Ollama 文本模型，基于界面元素文本列表决策，无需联网。
- LocalVisionBrain : 调用「端侧」Ollama 多模态模型（手机里用 Termux 跑），既看截图又看元素，
                     全程在手机上推理、彻底不联网、不依赖电脑。

三者都返回符合 actions.ACTION_JSON_SCHEMA 的字典。
"""
import base64
import json
import io
from typing import Dict, List, Any, Optional

from loguru import logger

from .actions import ACTION_TYPES, ACTION_JSON_SCHEMA


SYSTEM_PROMPT = """你是一个操作 Android / 小米手机的智能体（agent）。
你会收到一个用户任务，以及手机当前界面的信息。请一步一步地操作手机来完成任务。

可用的动作类型：
{actions}

规则：
1. 每次只输出一个动作。
2. 需要点击或输入时，用界面元素的 index（编号）来指定目标。
3. 如果当前界面信息不足以判断，可以先 swipe 滚动或 wait 等待加载。
4. 当任务已经完成时，输出 action 为 "done"。
5. thought 字段简要说明你的判断依据。
""".format(actions="\n".join(f"- {k}: {v}" for k, v in ACTION_TYPES.items()))


def _format_elements(elements: List[Dict[str, Any]]) -> str:
    """把元素列表格式化为给 LLM 阅读的文本"""
    lines = []
    for el in elements:
        label = el["text"] or el["desc"] or el["resource_id"] or el["class"]
        kind = []
        if el["clickable"]:
            kind.append("可点击")
        if el["editable"]:
            kind.append("输入框")
        kind_str = f"({','.join(kind)})" if kind else ""
        lines.append(f"[{el['index']}] {label} {kind_str}".strip())
    return "\n".join(lines) if lines else "（当前界面没有可识别的元素）"


def _extract_json(text: str) -> Dict[str, Any]:
    """从模型输出里尽量稳健地解析出 JSON 对象（小模型常带多余文字 / 代码块）"""
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s[:4].lower() == "json":
            s = s[4:]
    # 截取首个 { 到最后一个 }，丢掉前后的废话
    start, end = s.find("{"), s.rfind("}")
    if start != -1 and end != -1 and end > start:
        s = s[start:end + 1]
    return json.loads(s)


def _msg_content(resp: Any) -> str:
    """兼容 ollama 新旧版本返回（dict / 带属性的对象）"""
    msg = resp["message"] if isinstance(resp, dict) else resp.message
    return msg["content"] if isinstance(msg, dict) else msg.content


class Brain:
    """决策器基类"""

    def decide(self, task: str, elements: List[Dict[str, Any]],
               history: List[str], screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """返回下一步动作字典"""
        raise NotImplementedError


class ClaudeBrain(Brain):
    """基于 Claude 的多模态决策器（推荐）"""

    def __init__(self, model: str = "claude-opus-4-8",
                 api_key: Optional[str] = None,
                 use_thinking: bool = True):
        """
        Args:
            model: Claude 模型 ID（默认使用最新最强的 Opus 4.8）
            api_key: API Key，为 None 时从环境变量 ANTHROPIC_API_KEY 读取
            use_thinking: 是否开启自适应思考（决策更稳，略慢）
        """
        import anthropic

        # 不硬编码 key：默认从环境变量解析
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = model
        self.use_thinking = use_thinking
        logger.info(f"Claude 决策器初始化完成，模型: {model}")

    def decide(self, task: str, elements: List[Dict[str, Any]],
               history: List[str], screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        prompt = (
            f"用户任务：{task}\n\n"
            f"已执行的操作历史：\n{chr(10).join(history) or '（无）'}\n\n"
            f"当前界面元素（截图中红框内的编号与此一致）：\n{_format_elements(elements)}\n\n"
            f"请决定下一步动作。"
        )

        content: List[Dict[str, Any]] = []
        if screenshot_path:
            with open(screenshot_path, "rb") as f:
                img_b64 = base64.standard_b64encode(f.read()).decode("utf-8")
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
            })
        content.append({"type": "text", "text": prompt})

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 2048,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": content}],
            # 结构化输出：保证模型只产出合法的 action JSON
            "output_config": {"format": {"type": "json_schema", "schema": ACTION_JSON_SCHEMA}},
        }
        if self.use_thinking:
            # Opus 4.8 仅支持自适应思考
            kwargs["thinking"] = {"type": "adaptive"}

        response = self.client.messages.create(**kwargs)

        # 结构化输出下，正文 text 块即为合法 JSON（思考块在前，需筛出 text 块）
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)


class OllamaBrain(Brain):
    """基于本地 Ollama 文本模型的决策器（无需联网）"""

    def __init__(self, model: str = "qwen2.5:7b",
                 host: str = "http://localhost:11434"):
        from src.models.ollama_client import OllamaClient

        self.client = OllamaClient(host=host, model=model)
        logger.info(f"Ollama 决策器初始化完成，模型: {model}")

    def decide(self, task: str, elements: List[Dict[str, Any]],
               history: List[str], screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        prompt = (
            f"用户任务：{task}\n\n"
            f"已执行的操作历史：\n{chr(10).join(history) or '（无）'}\n\n"
            f"当前界面元素：\n{_format_elements(elements)}\n\n"
            f"请只返回一个 JSON 对象表示下一步动作，"
            f"字段：thought, action, index, text, direction, app。"
        )
        return self.client.chat_with_json(prompt=prompt, system_prompt=SYSTEM_PROMPT)


class LocalVisionBrain(Brain):
    """端侧多模态决策器：在「手机本机」用 Ollama 跑的视觉模型来决策。

    与 OllamaBrain 的区别：
    - 既看标注截图、又看元素文本（真·多模态），定位更准；
    - 默认连本机 127.0.0.1，意味着模型就跑在手机里（Termux），
      推理全程在端侧完成，不联网、也不需要电脑。

    需要手机端 Ollama 已拉取一个视觉模型，例如：
      minicpm-v（质量好）/ llava-phi3、moondream（更小更快）。
    """

    def __init__(self, model: str = "minicpm-v",
                 host: str = "http://127.0.0.1:11434",
                 use_vision: bool = True):
        """
        Args:
            model: 手机端 Ollama 里的视觉模型名（需先 ollama pull）
            host: Ollama 服务地址；端侧部署时指向本机 127.0.0.1
            use_vision: 是否把截图喂给模型（端侧视觉建议 True）
        """
        import ollama

        self.client = ollama.Client(host=host)
        self.model = model
        self.use_vision = use_vision
        logger.info(f"端侧视觉决策器初始化完成，模型: {model}, 地址: {host}")

    def decide(self, task: str, elements: List[Dict[str, Any]],
               history: List[str], screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        prompt = (
            f"用户任务：{task}\n\n"
            f"已执行的操作历史：\n{chr(10).join(history) or '（无）'}\n\n"
            f"当前界面元素（截图中红框内的编号与此一致）：\n{_format_elements(elements)}\n\n"
            f"请只返回一个 JSON 对象表示下一步动作，"
            f"字段：thought, action, index, text, direction, app。"
        )

        user_msg: Dict[str, Any] = {"role": "user", "content": prompt}
        if self.use_vision and screenshot_path:
            with open(screenshot_path, "rb") as f:
                user_msg["images"] = [f.read()]  # ollama 接受图片字节

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            user_msg,
        ]
        options = {"temperature": 0}

        # 优先用结构化输出（Ollama >=0.5 支持传 JSON Schema）；老版本退回 format="json"
        try:
            resp = self.client.chat(model=self.model, messages=messages,
                                    format=ACTION_JSON_SCHEMA, options=options)
        except Exception as e:
            logger.warning(f"端侧结构化输出不可用（{e}），退回 format=json")
            resp = self.client.chat(model=self.model, messages=messages,
                                    format="json", options=options)

        return _extract_json(_msg_content(resp))


def create_brain(provider: str, **kwargs) -> Brain:
    """
    根据配置创建决策器

    Args:
        provider: "claude" / "ollama" / "local"
        **kwargs: 传给对应决策器的参数
    """
    provider = provider.lower()
    if provider == "claude":
        return ClaudeBrain(**kwargs)
    if provider == "ollama":
        return OllamaBrain(**kwargs)
    if provider == "local":
        return LocalVisionBrain(**kwargs)
    raise ValueError(f"不支持的决策器类型: {provider}（可选: claude / ollama / local）")
