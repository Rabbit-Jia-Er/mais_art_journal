"""
场景动作生成器（精简版）

根据 ActivityInfo 生成符合情境的动作和 Stable Diffusion 提示词。
从 selfie_painter 的 SceneActionGenerator 精简而来，
不依赖 ScheduleEntry，使用简化的 ActivityInfo。
"""

import random
import re
from typing import Dict, List, Optional

from src.common.logger import get_logger

from .schedule_provider import ActivityInfo, ActivityType
from ..utils import ANTI_DUAL_HANDS_PROMPT

logger = get_logger("auto_selfie.scene")


# 活动类型到动作的映射（12 种类型）
ACTIVITY_ACTIONS: Dict[str, List[str]] = {
    "sleeping": [
        "lying down, relaxed",
        "hugging pillow, cozy",
        "stretching arms, sleepy",
        "curled up in bed",
        "peaceful sleeping pose",
    ],
    "waking_up": [
        "stretching, yawning",
        "rubbing eyes, sleepy",
        "sitting on bed edge",
        "messy hair, just woke up",
        "holding alarm clock",
    ],
    "eating": [
        "holding chopsticks, eating",
        "holding cup, drinking",
        "picking up food",
        "holding fork and knife",
        "holding spoon, tasting",
        "holding bowl, eating",
    ],
    "working": [
        "typing on laptop",
        "writing notes",
        "looking at screen, focused",
        "holding pen, thinking",
        "reading documents",
    ],
    "studying": [
        "holding book, reading",
        "writing in notebook",
        "looking at textbook",
        "holding pen, studying",
        "taking notes",
    ],
    "exercising": [
        "stretching, athletic",
        "holding water bottle",
        "wiping sweat, tired",
        "doing yoga pose",
        "running pose",
    ],
    "relaxing": [
        "lying on couch, relaxed",
        "resting head on hand, zoning out",
        "reading magazine",
        "listening to music, headphones",
        "watching TV, relaxed",
    ],
    "socializing": [
        "waving hand, greeting",
        "making peace sign, happy",
        "laughing, joyful",
        "talking with friends",
        "cheering, celebration",
    ],
    "commuting": [
        "holding bag, walking",
        "standing, waiting",
        "looking out window, daydreaming",
        "wearing earbuds, commuting",
        "holding coffee, on the go",
    ],
    "hobby": [
        "holding camera, taking photos",
        "playing instrument",
        "crafting, creative",
        "painting, artistic",
        "playing video games",
    ],
    "self_care": [
        "applying makeup, mirror",
        "brushing hair",
        "holding mirror, checking",
        "skincare routine",
        "face mask, relaxing",
    ],
    "other": [
        "standing, casual pose",
        "sitting, relaxed",
        "casual pose, natural",
        "looking at camera",
        "peace sign, friendly",
    ],
}

# 活动类型到场景环境的映射
ACTIVITY_ENVIRONMENTS: Dict[str, List[str]] = {
    "sleeping": ["bedroom, dim lighting, cozy atmosphere, bed"],
    "waking_up": ["bedroom, morning light, curtains, warm sunlight"],
    "eating": ["dining room, table setting", "cafe, cozy interior", "kitchen, home cooking"],
    "working": ["office desk, computer screen", "study room, books", "coworking space"],
    "studying": ["library, bookshelves", "study room, desk lamp", "classroom"],
    "exercising": ["gym, fitness equipment", "outdoor park, morning", "yoga studio"],
    "relaxing": ["living room, sofa", "balcony, afternoon sun", "garden, natural"],
    "socializing": ["outdoor cafe", "park bench", "restaurant interior"],
    "commuting": ["city street, urban", "bus stop", "train station platform"],
    "hobby": ["art studio", "music room", "craft table"],
    "self_care": ["bathroom, mirror, vanity", "bedroom vanity table"],
    "other": ["indoor, natural lighting", "outdoor, casual setting"],
}

# 活动类型到表情的映射
ACTIVITY_EXPRESSIONS: Dict[str, List[str]] = {
    "sleeping": ["peaceful expression, closed eyes", "sleepy smile"],
    "waking_up": ["drowsy expression, half-open eyes", "yawning, cute"],
    "eating": ["happy expression, enjoying food", "satisfied smile"],
    "working": ["focused expression, serious", "determined look, concentrated"],
    "studying": ["focused, reading", "thoughtful expression"],
    "exercising": ["energetic expression", "sweating, determined", "refreshed smile"],
    "relaxing": ["relaxed smile, content", "lazy expression, comfortable"],
    "socializing": ["bright smile, happy", "laughing, cheerful"],
    "commuting": ["calm expression", "looking forward, determined"],
    "hobby": ["excited, passionate", "focused, creative"],
    "self_care": ["gentle smile, self-care", "focused, beauty routine"],
    "other": ["natural smile", "casual expression"],
}

# 活动类型到光线的映射
ACTIVITY_LIGHTING: Dict[str, List[str]] = {
    "sleeping": ["dim warm light, night lamp"],
    "waking_up": ["soft morning light, golden hour"],
    "eating": ["warm indoor lighting", "natural window light"],
    "working": ["office lighting, even illumination"],
    "studying": ["desk lamp, focused light"],
    "exercising": ["bright natural light", "gym lighting"],
    "relaxing": ["soft afternoon light", "warm ambient light"],
    "socializing": ["bright cheerful lighting", "outdoor natural light"],
    "commuting": ["urban city lights", "morning sunlight"],
    "hobby": ["creative studio lighting", "natural side lighting"],
    "self_care": ["bathroom lighting, mirror reflection"],
    "other": ["natural lighting"],
}


def get_action_for_activity(activity_info: ActivityInfo) -> Dict[str, str]:
    """
    根据活动信息获取适合的动作

    Args:
        activity_info: 活动信息

    Returns:
        包含 hand_action, environment, expression, lighting 的字典
    """
    activity_key = activity_info.activity_type.value

    hand_action = random.choice(
        ACTIVITY_ACTIONS.get(activity_key, ACTIVITY_ACTIONS["other"])
    )
    environment = random.choice(
        ACTIVITY_ENVIRONMENTS.get(activity_key, ACTIVITY_ENVIRONMENTS["other"])
    )
    expression = random.choice(
        ACTIVITY_EXPRESSIONS.get(activity_key, ACTIVITY_EXPRESSIONS["other"])
    )
    lighting = random.choice(
        ACTIVITY_LIGHTING.get(activity_key, ACTIVITY_LIGHTING["other"])
    )

    return {
        "hand_action": hand_action,
        "environment": environment,
        "expression": expression,
        "lighting": lighting,
    }


def convert_to_selfie_prompt(
    activity_info: ActivityInfo,
    selfie_style: str = "standard",
    bot_appearance: str = "",
) -> str:
    """
    将活动信息转换为完整的自拍 SD 提示词

    Args:
        activity_info: 活动信息
        selfie_style: 自拍风格 ("standard" 或 "mirror")
        bot_appearance: Bot 外观描述（从配置读取的 selfie.prompt_prefix）

    Returns:
        完整的 SD 提示词
    """
    prompt_parts: List[str] = []

    # 1. 强制主体
    prompt_parts.append("(1girl:1.4), (solo:1.3)")

    # 2. Bot 外观
    if bot_appearance:
        prompt_parts.append(bot_appearance)

    # 3. 获取场景动作
    scene = get_action_for_activity(activity_info)

    # 4. 表情
    prompt_parts.append(f"({scene['expression']}:1.2)")

    # 5. 手部/身体动作
    hand_action = scene["hand_action"]

    # standard 自拍禁止手机类词汇
    if selfie_style == "standard" and hand_action:
        if re.search(r"\b(phone|smartphone|mobile|device)\b", hand_action, flags=re.IGNORECASE):
            hand_action = "resting head on hand"

    if hand_action:
        if selfie_style == "standard":
            hand_prompt = (
                f"(visible free hand {hand_action}:1.4), "
                "(only one hand visible in frame:1.5), "
                "(single hand gesture:1.3)"
            )
        else:
            hand_prompt = f"({hand_action}:1.3)"
        prompt_parts.append(hand_prompt)

    # 6. 环境
    prompt_parts.append(scene["environment"])

    # 7. 光线
    prompt_parts.append(scene["lighting"])

    # 8. 自拍风格
    if selfie_style == "mirror":
        selfie_scene = (
            "mirror selfie, reflection in mirror, "
            "holding phone in hand, phone visible, "
            "looking at mirror, indoor scene"
        )
    else:
        selfie_scene = (
            "selfie, front camera view, POV selfie, "
            "(front facing selfie camera angle:1.3), "
            "looking at camera, slight high angle selfie, "
            "upper body shot, cowboy shot, "
            "(centered composition:1.2)"
        )
    prompt_parts.append(selfie_scene)

    # 9. 过滤空值、去重、拼接
    prompt_parts = [p for p in prompt_parts if p and p.strip()]
    keywords = [kw.strip() for kw in ", ".join(prompt_parts).split(",")]
    seen = set()
    unique = []
    for kw in keywords:
        kw_lower = kw.strip().lower()
        if kw_lower and kw_lower not in seen:
            seen.add(kw_lower)
            unique.append(kw.strip())

    final_prompt = ", ".join(unique)
    logger.info(f"生成自拍提示词: {final_prompt[:150]}...")
    return final_prompt


def get_negative_prompt_for_style(selfie_style: str, base_negative: str = "") -> str:
    """
    获取指定自拍风格的负面提示词

    Args:
        selfie_style: 自拍风格
        base_negative: 基础负面提示词（从配置读取）

    Returns:
        完整的负面提示词
    """
    if selfie_style == "standard":
        anti_dual_hands = ANTI_DUAL_HANDS_PROMPT
        if base_negative:
            return f"{base_negative}, {anti_dual_hands}"
        return anti_dual_hands

    return base_negative
