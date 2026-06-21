"""
应用包名注册表

记录常见小米 / 第三方 App 的包名，方便用自然语言指定 App。
可自行扩展，或用 Device.list_installed_apps() 查询真实包名后补充。

提示：不同地区 / 版本的包名可能不同，请以手机实际安装的为准：
  adb shell pm list packages | grep <关键词>
"""
from typing import Dict, Optional

# 应用别名 -> 包名
APP_PACKAGES: Dict[str, str] = {
    # 小米系统应用
    "设置": "com.android.settings",
    "settings": "com.android.settings",
    "相机": "com.android.camera",
    "相册": "com.miui.gallery",
    "文件管理": "com.android.fileexplorer",
    "时钟": "com.android.deskclock",
    "计算器": "com.miui.calculator",
    "便签": "com.miui.notes",
    "浏览器": "com.android.browser",
    "应用商店": "com.xiaomi.market",
    "音乐": "com.miui.player",
    "小米商城": "com.xiaomi.shop",
    "小米社区": "com.xiaomi.vipaccount",
    "小爱同学": "com.miui.voiceassist",
    # 常见第三方应用
    "微信": "com.tencent.mm",
    "wechat": "com.tencent.mm",
    "qq": "com.tencent.mobileqq",
    "支付宝": "com.eg.android.AlipayGphone",
    "alipay": "com.eg.android.AlipayGphone",
    "淘宝": "com.taobao.taobao",
    "京东": "com.jingdong.app.mall",
    "抖音": "com.ss.android.ugc.aweme",
    "douyin": "com.ss.android.ugc.aweme",
    "微博": "com.sina.weibo",
    "美团": "com.sankuai.meituan",
    "高德地图": "com.autonavi.minimap",
    "知乎": "com.zhihu.android",
    "bilibili": "tv.danmaku.bili",
    "哔哩哔哩": "tv.danmaku.bili",
}


def resolve_package(name_or_package: str) -> Optional[str]:
    """
    将 App 名称或别名解析为包名

    Args:
        name_or_package: App 中文名 / 英文别名 / 直接传包名

    Returns:
        包名；无法解析时返回 None
    """
    key = name_or_package.strip()
    # 已经是包名（含点号）则直接返回
    if "." in key:
        return key
    return APP_PACKAGES.get(key) or APP_PACKAGES.get(key.lower())
