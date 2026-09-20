"""通用通知模板；可按实际活动要求修改。"""

TEMPLATE = (
    "您好，您企业的宣讲时间是{time}，地点是{address}。\n"
    "如时间、地点或参会人员有变更，请提前联系接待人员确认。谢谢！"
)


def render_message(time_text: str, address: str) -> str:
    return TEMPLATE.format(time=time_text, address=address)
