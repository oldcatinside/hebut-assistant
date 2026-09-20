import math
import re


def text_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        if value.is_integer():
            return str(int(value))
    return str(value).strip()


def clean_phone(value) -> tuple[str, bool]:
    phone = re.sub(r"[\s\-－]", "", text_value(value))
    if phone.startswith("+86"):
        phone = phone[3:]
    elif len(phone) == 13 and phone.startswith("86"):
        phone = phone[2:]
    return phone, bool(re.fullmatch(r"1[0-9]{10}", phone))
