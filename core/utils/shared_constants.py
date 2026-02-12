"""mais_art_journal 共享常量"""

# Base64 图片格式前缀，用于区分 base64 数据与 URL
# JPEG: /9j/  PNG: iVBORw  WEBP: UklGR  GIF: R0lGOD
BASE64_IMAGE_PREFIXES = ("iVBORw", "/9j/", "UklGR", "R0lGOD")

# 防止生成双手拿手机等不自然姿态的负面提示词
ANTI_DUAL_HANDS_PROMPT = (
    "two phones, camera in both hands, "
    "holding phone with both hands, "
    "extra hands, extra arms, 3 hands, 4 hands, "
    "multiple hands, both hands holding phone, "
    "phone in frame, visible phone in hand, "
    "both hands visible"
)
