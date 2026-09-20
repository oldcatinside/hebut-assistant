from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Record:
    company: str
    contact: str
    phone: str
    phone_valid: bool
    time_text: str
    address: str
    message: str
    message_error: str
    sheet: str
    row: int
    raw_time: str = ""
    raw_address: str = ""
    raw_phone: str = ""
    issues: list[str] = field(default_factory=list)
    start_time: datetime | None = None
    row_notes: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "；".join(self.issues) if self.issues else "正常"

    def all_info(self) -> str:
        return (
            f"企业：{self.company or '未填写'}\n联系人：{self.contact or '未填写'}\n"
            f"手机号：{self.phone or '未填写'}\n时间：{self.time_text or '未填写 / 无法识别'}\n"
            f"地点：{self.address or '未填写'}\n状态：{self.status}\n"
            f"来源：{self.sheet}，第{self.row}行\n\n短信：\n{self.message or self.message_error}"
        )


@dataclass
class ReadResult:
    records: list[Record] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sheet_count: int = 0
    raw_book: object = None
    layouts: dict = field(default_factory=dict)
