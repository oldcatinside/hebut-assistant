"""生成手机查看的接待清单，与固定短信模板相互独立。"""
from dataclasses import dataclass
from datetime import datetime
import re
import unicodedata
from app.models import Record


def short_room(address: str) -> tuple[str, bool]:
    text = unicodedata.normalize('NFKC', address).strip()
    # 只缩写没有楼号或校区前缀的教室，完整地点保留原文。
    match = re.fullmatch(r'([A-Za-z]\d{3,4})(?:教室)?', text, re.I)
    if match:
        return match.group(1).lower(), True
    return re.sub(r'\s+', ' ', address).strip() or '[地点缺失]', False


@dataclass(frozen=True)
class Schedule:
    text: str
    count: int
    attention: int


def build_schedule(records: list[Record], chronological=False) -> Schedule:
    ordered = list(records)
    if chronological:
        ordered.sort(key=lambda r: r.start_time or datetime.max)
    dates = {(r.start_time.year, r.start_time.month) for r in records if r.start_time}
    years = {y for y, _ in dates}
    lines, attention = [], 0
    for record in ordered:
        start = record.start_time
        if start:
            day = f'{start.day}号'
            if len(dates) > 1:
                day = f'{start.month}月{start.day}号'
            if len(years) > 1:
                day = f'{start.year}年{start.month}月{start.day}号'
            when = f'{day} {start:%H.%M}'
        else:
            when = '[时间缺失或无法识别]'
        room, simple = short_room(record.address)
        phone = record.phone if record.phone_valid else (f'[号码异常:{record.phone}]' if record.phone else '[手机号缺失]')
        notes = []
        if not simple and record.address:
            notes.append('地点需核对')
        if any('地点' in issue for issue in record.issues) and '地点需核对' not in notes:
            notes.append('地点需核对')
        needs_check = not start or not simple or not record.phone_valid or bool(notes)
        attention += int(needs_check)
        company = re.sub(r'\s+', ' ', record.company).strip() or '[企业名称缺失]'
        line = f'{when} {room} {phone} {company}'
        if not record.phone_valid and record.row_notes:
            line += ' [表格提示：' + '；'.join(record.row_notes) + ']'
        if notes:
            line += ' [' + '；'.join(notes) + ']'
        lines.append(line)
    return Schedule('\n'.join(lines), len(lines), attention)
