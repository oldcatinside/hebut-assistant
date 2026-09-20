import re
from app.phone_utils import text_value


def normalize_location(value) -> tuple[str, str]:
    raw = text_value(value)
    markers = r"(?:调整至|调整到|调换至|调换到|调到|改为|改至|更改为)"
    if re.search(markers, raw):
        parts = re.split(markers, raw)
        final = parts[-1].strip()
        # 仅接受完整明确的教室或完整地点，任何附注均保留原文。
        if len(parts) == 2 and re.fullmatch(r"(?:[\u4e00-\u9fff]+)?[0-9]+-[A-Za-z]?[0-9]+", final):
            return final, ""
        return raw, "地点含调换说明，请人工检查"
    if any(word in raw for word in ("调换", "调整", "待定", "改到", "另行通知")):
        return raw, "地点需要人工检查"
    return raw, ""
