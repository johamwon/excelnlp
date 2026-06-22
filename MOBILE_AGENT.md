# 手机自动化 Agent（小米 / Android）

用一句自然语言指挥手机自动打开 App 并完成操作。基于开源的 **uiautomator2**（ADB 控制）
+ LLM 决策，采用 **AppAgent / Mobile-Agent** 这类开源手机 Agent 的「感知-决策-执行」范式，
结构清晰、方便后续自己定制。

## 它能做什么

给它一句话，比如：

- 「打开设置，进入 WLAN 页面」
- 「打开计算器，算一下 23 乘以 17」
- 「打开微信，给文件传输助手发一条消息：你好」

Agent 会自动循环：**截屏 + 读取界面元素 → 交给大模型决定下一步 → 在手机上执行**，
直到任务完成。

## 工作原理

```
        ┌─────────────────────────────────────────────┐
        │              MobileAgent 循环                 │
        │                                               │
   ┌────▼─────┐    ┌──────────────┐    ┌─────────────┐ │
   │ 感知      │ →  │ 决策（LLM）   │ →  │ 执行        │ │
   │ 截屏+元素 │    │ 输出 action  │    │ 点击/输入… │ │
   └──────────┘    └──────────────┘    └──────┬──────┘ │
        ▲                                       │        │
        └───────────────────────────────────────┘        │
                                                          │
   设备层: uiautomator2 ── ADB ── 小米/Android 手机        │
        └─────────────────────────────────────────────┘
```

涉及的开源项目 / 库：

| 组件 | 项目 | 作用 |
|------|------|------|
| 设备控制 | [uiautomator2](https://github.com/openatx/uiautomator2) | 通过 ADB 控制手机，截屏、点击、输入、读取界面层级 |
| Agent 范式 | [AppAgent](https://github.com/mnotgod96/AppAgent) / [Mobile-Agent](https://github.com/X-PLUG/MobileAgent) | 截图编号标注 + LLM 决策的手机 Agent 思路 |
| 决策大脑 | Claude（多模态，推荐）/ [Ollama](https://github.com/ollama/ollama)（本地/端侧） | 看界面、做决策、输出动作 |

三种决策大脑（`provider`）：

| provider | 模型跑在哪 | 看截图 | 是否联网 | 是否要电脑 | 适合 |
|----------|-----------|:------:|:--------:|:----------:|------|
| `claude` | 云端 | ✅ | 需要 | 需要 | 能力最强，复杂任务 |
| `ollama` | 电脑本地 | ❌（纯文本） | 不需要 | 需要 | 隐私敏感、有电脑 |
| `local`  | **手机里（Termux）** | ✅ | **不需要** | **不需要** | 彻底端侧、随身离线 |

## 目录结构

```
src/mobile/
├── device.py    # 设备控制器（封装 uiautomator2）
├── apps.py      # 常见小米/第三方 App 包名表（可自行扩展）
├── actions.py   # 动作定义、执行器、截图编号标注
├── llm.py       # 决策大脑：ClaudeBrain / OllamaBrain（可插拔）
└── agent.py     # 感知-决策-执行主循环
mobile_agent.py        # 命令行入口
configs/mobile_config.yaml   # 配置文件
```

## 准备工作

### 1. 安装依赖

```bash
pip install -r requirements.txt
# 或仅安装手机自动化所需：
pip install uiautomator2 Pillow anthropic
```

还需要本机装好 **adb**（Android Platform Tools）：

```bash
adb version   # 能输出版本号即可
```

### 2. 小米手机开启调试（关键）

小米 MIUI / HyperOS 需要额外开启「USB 调试（安全设置）」，否则无法模拟点击：

1. 设置 → 我的设备 → 全部参数 → 连续点击「MIUI 版本」7 次，开启开发者选项
2. 设置 → 更多设置 → 开发者选项，打开：
   - **USB 调试**
   - **USB 调试（安全设置）** ← 小米必开，否则不能模拟输入/点击
   - **USB 安装**（如需自动安装）
3. 用数据线连接电脑，手机弹出授权框时勾选「一律允许」并确定

确认连接成功：

```bash
adb devices
# 应能看到设备序列号，状态为 device
```

### 3. 初始化 uiautomator2（首次）

```bash
python -m uiautomator2 init
```

这会在手机上安装 ATX-Agent 等辅助 App（开源），用于接收自动化指令。

### 4. 配置大脑

编辑 `configs/mobile_config.yaml`：

- **用 Claude（推荐，能力最强）**：设置环境变量 `ANTHROPIC_API_KEY`，`provider: claude`
  ```bash
  export ANTHROPIC_API_KEY=sk-ant-...
  ```
- **用本地 Ollama（无需联网、隐私安全）**：`provider: ollama`，并确保 Ollama 在运行
  （本仓库已用到 Ollama，参见主 README）。本地纯文本模型建议关闭视觉（`--no-vision`）。
- **端侧视觉（`provider: local`，模型也跑在手机里、彻底离线）**：见下方专节。

## 端侧视觉：把模型也搬进手机（彻底离线，连电脑都不要）

`provider: local` 让「看截图 + 做决策」的多模态模型直接在手机里运行，
推理全程在端侧、不联网、也不依赖电脑。做法是在手机的
[Termux](https://github.com/termux/termux-app)（安卓上的 Linux 终端）里把整套跑起来。

1. **装 Termux**：从 F-Droid / GitHub Releases 安装（应用商店版本较旧，不推荐）。

2. **在 Termux 里装运行环境**：
   ```bash
   pkg update && pkg install python git
   pip install uiautomator2 Pillow ollama loguru pyyaml
   ```

3. **在手机上装并启动 Ollama**，拉一个小型视觉模型：
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh   # 或参考 Ollama 安卓/Termux 说明
   ollama serve &                                   # 监听 127.0.0.1:11434
   ollama pull minicpm-v       # 质量好；机型吃力可换 moondream / llava-phi3（更小更快）
   ```

4. **本机自连**：手机自己控制自己，uiautomator2 连本机即可（同机的 ADB / ATX-Agent）。
   把代码拷进手机（`git clone` 本仓库或解压功能包），确保
   `configs/mobile_config.yaml` 里 `provider: local`、`brain.local.host: http://127.0.0.1:11434`。

5. **跑起来**（在 Termux 内）：
   ```bash
   python mobile_agent.py "打开设置，进入WLAN页面" --provider local
   ```

> 提示：端侧小模型的决策能力弱于 Claude，建议任务描述写具体、`max_steps` 调大一点；
> 机型内存有限时优先选更小的视觉模型，或退回 `--no-vision` 用纯文本（更快但更弱）。
> 手机端 Ollama 升到 0.5+ 可启用 JSON Schema 结构化输出（决策更稳），老版本会自动退回。

## 使用

```bash
# 一句话指挥（读取 configs/mobile_config.yaml）
python mobile_agent.py "打开设置，进入WLAN页面"

# 端侧视觉：模型也跑在手机里，全程离线（见上方 Termux 专节）
python mobile_agent.py "打开计算器" --provider local

# 电脑本地纯文本模型、关闭截图
python mobile_agent.py "打开计算器" --provider ollama --no-vision

# 交互模式：连续下达多个任务
python mobile_agent.py
```

也可在代码里调用：

```python
from src.mobile import Device, MobileAgent, create_brain

device = Device()                      # 连接默认手机
brain = create_brain("claude")         # 或 "ollama"（电脑本地）/ "local"（手机端侧视觉）
agent = MobileAgent(device, brain, max_steps=15)
agent.run("打开小米商城，搜索 手机壳")
```

## 如何定制（未来扩展点）

这套框架刻意做成模块化，常见定制只需改一处：

| 想做的事 | 改哪里 |
|----------|--------|
| 新增/修正 App 包名 | `src/mobile/apps.py` 的 `APP_PACKAGES` |
| 增加新动作（如长按、双击、截图保存） | `src/mobile/actions.py` 的 `ACTION_TYPES` + `ActionExecutor.execute` |
| 换模型 / 换厂商（GPT、Gemini、其他本地模型） | 在 `src/mobile/llm.py` 新增一个 `Brain` 子类，并在 `create_brain` 注册 |
| 调整 Agent 的提示词/策略 | `src/mobile/llm.py` 的 `SYSTEM_PROMPT` |
| 改感知方式（如只看可点击元素、加 OCR） | `src/mobile/device.py` 的 `get_elements` / `actions.py` 的 `annotate_screenshot` |
| 固定流程（不走 LLM，写死脚本） | 直接用 `Device` 的方法编排，跳过 `MobileAgent` |

## 常见问题

- **adb devices 看不到设备**：换数据线/USB 口；确认手机已授权调试；`adb kill-server && adb start-server`。
- **点击没反应**：小米需开启「USB 调试（安全设置）」。
- **找不到 App**：用 `adb shell pm list packages | grep 关键词` 查到真实包名，补到 `apps.py`。
- **决策不准**：用 Claude + 开启视觉效果最好；适当增大 `max_steps`；把任务描述写得更具体。

## 注意

- 自动化会真实操作你的手机，请在测试机或非敏感场景下使用，避免误触支付等操作。
- 截图可能包含隐私信息，中间截图默认存于系统临时目录，按需清理。
