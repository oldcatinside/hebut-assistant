"""显式格式解析：不推测缺少年份的日期，不使用宽松日期猜测。"""
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from numbers import Real
import re

from openpyxl.utils.datetime import from_excel, WINDOWS_EPOCH

from app.phone_utils import text_value


class TimeParseError(ValueError):
    pass


@dataclass(frozen=True)
class TalkTime:
    start: datetime
    end: datetime

    @property
    def text(self) -> str:
        start = self.start
        prefix = f"{start.month}月{start.day}日周{'一二三四五六日'[start.weekday()]} {start:%H:%M}"
        if self.end.date() == start.date():
            return f"{prefix}-{self.end:%H:%M}"
        return f"{prefix}-{self.end.month}月{self.end.day}日 {self.end:%H:%M}"


DATE_TIME = re.compile(
    r"(?P<y>[0-9]{4})[-/.年](?P<m>[0-9]{1,2})[-/.月](?P<d>[0-9]{1,2})日?"
    r"[ T]+(?P<h>[0-9]{1,2})[:：点时](?P<minute>[0-9]{1,2})分?"
    r"(?::(?P<s>[0-9]{2})(?:\.0+)?)?"
)
CLOCK = re.compile(r"(?P<h>[0-9]{1,2})[:：点时](?P<m>[0-9]{1,2})分?(?::(?P<s>[0-9]{2}))?")


def _normalize(value: str) -> str:
    value = re.sub(r"[（(]?\s*(?:星期|周)[一二三四五六日天]\s*[）)]?", " ", value)
    value = re.sub(r"日(?=[0-9])", "日 ", value)
    return re.sub(r"\s+", " ", value).strip()


def _date_string(value: str) -> datetime:
    match = DATE_TIME.fullmatch(_normalize(value))
    if not match:
        raise TimeParseError("宣讲时间无法识别")
    v = match.groupdict()
    if int(v['s'] or 0) != 0:
        raise TimeParseError("宣讲时间包含非零秒，请人工确认到分钟")
    return datetime(*(int(v[k]) for k in ('y', 'm', 'd', 'h', 'minute')))


def _start(value, epoch: datetime) -> datetime:
    if isinstance(value, datetime):
        result = value
    elif isinstance(value, Real) and not isinstance(value, bool):
        result = from_excel(float(value), epoch=epoch)
    else:
        result = _date_string(text_value(value))
    if not isinstance(result, datetime) or result.tzinfo is not None:
        raise TimeParseError("宣讲时间无法识别")
    if result.second or result.microsecond:
        raise TimeParseError("宣讲时间包含非零秒，请人工确认到分钟")
    return result


def _end(value, start: datetime, epoch: datetime) -> datetime:
    explicit_next_day = False
    if isinstance(value, str):
        value = _normalize(value)
        if value.startswith(("次日", "翌日")):
            explicit_next_day = True
            value = value[2:].strip()
        match = CLOCK.fullmatch(value)
        if match:
            v = match.groupdict()
            value = time(int(v['h']), int(v['m']), int(v['s'] or 0))
    if isinstance(value, Real) and 0 <= value < 1:
        value = from_excel(float(value), epoch=epoch)
    if isinstance(value, time):
        if value.second or value.microsecond or value.tzinfo:
            raise TimeParseError("结束时间无法识别")
        result = datetime.combine(start.date(), value)
        if explicit_next_day:
            result += timedelta(days=1)
    else:
        result = _start(value, epoch)
    if result <= start:
        raise TimeParseError("结束时间不晚于开始时间，请明确是否跨日")
    return result


def parse_time(value, duration: int = 95, end_value=None, epoch=WINDOWS_EPOCH) -> TalkTime:
    try:
        if not 1 <= duration <= 1440:
            raise TimeParseError("默认时长须为1至1440分钟")
        start_value = value
        embedded_end = None
        if isinstance(value, str):
            normalized = _normalize(value)
            match = DATE_TIME.match(normalized)
            if match:
                start_value = match.group()
                tail = normalized[match.end():].strip()
                if tail:
                    separator = re.match(r"^(?:至|到|~|～|—|–|-)+\s*(.+)$", tail)
                    if not separator:
                        raise TimeParseError("宣讲时间无法识别")
                    embedded_end = separator.group(1)
        start = _start(start_value, epoch)
        end = _end(embedded_end, start, epoch) if embedded_end else None
        if text_value(end_value):
            separate_end = _end(end_value, start, epoch)
            if end is not None and end != separate_end:
                raise TimeParseError("两处结束时间不一致，请人工检查")
            end = separate_end
        return TalkTime(start, end or start + timedelta(minutes=duration))
    except (ValueError, OverflowError, TypeError) as exc:
        if isinstance(exc, TimeParseError):
            raise
        raise TimeParseError("宣讲时间无法识别") from exc
