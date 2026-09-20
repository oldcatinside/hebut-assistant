"""只读读取，按工作表和行顺序处理；不跨企业猜测补值。"""
import logging
import re
from datetime import datetime, date, time
from pathlib import Path
from openpyxl.utils.datetime import from_excel
from app.workbook_loader import load_raw_book
from app.import_layout import FIELDS, SheetLayout, detect_sections
from app.location_utils import normalize_location
from app.message_builder import render_message
from app.models import ReadResult, Record
from app.phone_utils import text_value, clean_phone
from app.time_parser import parse_time, TimeParseError
from app.row_notes import collect_row_notes

log = logging.getLogger(__name__)


def combine_time(value, date_value, year, epoch):
    if text_value(date_value):
        if isinstance(date_value, (int, float)):
            date_value = from_excel(date_value, epoch)
        if isinstance(date_value, (datetime, date)):
            date_text = date_value.strftime('%Y-%m-%d')
        else:
            date_text = text_value(date_value)
        if isinstance(value, (int, float)) and 0 <= value < 1:
            value = from_excel(value, epoch)
        if isinstance(value, time):
            value = value.strftime('%H:%M:%S')
        elif isinstance(value, datetime) and value.year in (1899, 1900, 1904):
            value = value.strftime('%H:%M:%S')
        value = f'{date_text} {text_value(value)}' if text_value(value) else ''
    if year and isinstance(value, str) and re.match(r'^\s*\d{1,2}(?:月|[-/.])\d{1,2}', value):
        value = f'{year}年' + value if '月' in value else f'{year}-' + value
    return value


def make_record(get, sheet, row, duration, epoch, year=0):
    company, contact = text_value(get('公司名称')), text_value(get('联系人'))
    raw_time, raw_address, raw_phone = (text_value(get(f)) for f in ('宣讲会时间', '宣讲会地点', '联系人电话'))
    if text_value(get('宣讲日期')):
        raw_time = text_value(get('宣讲日期')) + ' ' + raw_time
    phone, valid = clean_phone(get('联系人电话'))
    address, location_warning = normalize_location(get('宣讲会地点'))
    issues, blockers = [], []
    if not company:
        issues.append('公司名称缺失')
    formatted_time = ''
    start_time = None
    if not text_value(get('宣讲会时间')):
        issues.append('宣讲时间缺失')
        blockers.append('缺少宣讲时间')
    else:
        try:
            value = combine_time(get('宣讲会时间'), get('宣讲日期'), year, epoch)
            parsed = parse_time(value, duration, get('结束时间'), epoch)
            formatted_time, start_time = parsed.text, parsed.start
        except (TimeParseError, ValueError, TypeError, OverflowError) as exc:
            issues.append('宣讲时间无法识别：' + str(exc))
            blockers.append('宣讲时间无法识别')
            log.warning('时间解析异常，行号=%d', row)
    if not address:
        issues.append('宣讲地点缺失')
        blockers.append('缺少宣讲地点')
    if location_warning:
        issues.append(location_warning)
    if not contact:
        issues.append('联系人缺失')
    if not raw_phone:
        issues.append('联系电话缺失（手机号异常）')
    elif not valid:
        issues.append('手机号格式异常')
    return Record(company, contact, phone, valid, formatted_time, address,
        render_message(formatted_time, address) if not blockers else '',
        '无法生成短信：' + '、'.join(blockers) if blockers else '',
        sheet, row, raw_time, raw_address, raw_phone, issues, start_time)


def process_book(book, name='', duration=95, layouts=None):
    name = name.strip()
    if not name:
        raise ValueError('筛选姓名不能为空')
    if not 1 <= duration <= 1440:
        raise ValueError('默认宣讲时长须为1至1440分钟')
    result = ReadResult(warnings=list(book.warnings), sheet_count=len(book.sheets), raw_book=book)
    for sheet in book.sheets:
        prefix = f'工作表「{sheet.name}」：'
        selected = (layouts or {}).get(sheet.name, SheetLayout())
        if selected.mode == 'skip':
            result.warnings.append(prefix + '已按您的设置跳过。')
            continue
        if not sheet.rows or not any(text_value(v) for row in sheet.rows for v in row):
            result.warnings.append(prefix + '空工作表。')
            continue
        if sheet.hidden:
            result.warnings.append(prefix + '隐藏工作表也已纳入读取。')
        if selected.mode == 'manual':
            sections = [selected]
            result.warnings.append(prefix + '使用手动列设置。')
        else:
            sections, notes = detect_sections(sheet, name)
            result.warnings.extend(prefix + note for note in notes)
        result.layouts[sheet.name] = sections[0] if len(sections) == 1 else SheetLayout()
        for section in sections:
            columns = section.columns
            if '姓名' not in columns:
                result.warnings.append(prefix + '未指定姓名列，未读取该段。')
                continue
            if any(type(c) is not int or c < 0 or c >= sheet.width for c in columns.values()) or len(set(columns.values())) != len(columns):
                result.warnings.append(prefix + '列设置无效或重复，请重新指定。')
                continue
            start, end = section.start_row-1, section.end_row or len(sheet.rows)
            if start < 0 or end <= start or end > len(sheet.rows):
                result.warnings.append(prefix + '数据行范围无效，请重新指定。')
                continue
            missing = [f for f in FIELDS if f not in columns]
            if missing:
                result.warnings.append(prefix + '缺少字段：' + '、'.join(missing))
            for ri in range(start, end):
                owner = sheet.value(ri, columns['姓名'], section.merged_names)
                if text_value(owner) != name:
                    continue
                if section.merged_names and not any(text_value(sheet.value(ri, col)) for key, col in columns.items() if key != '姓名'):
                    continue
                def get(field):
                    return sheet.value(ri, columns[field]) if field in columns else None
                record = make_record(get, sheet.name, ri+1, duration, book.epoch, section.year)
                record.row_notes = collect_row_notes(sheet, ri, columns, start)
                result.records.append(record)
    return result


def read_excel(path, name='', duration=95, layouts=None):
    path = Path(path)
    if path.suffix.lower() not in ('.xls', '.xlsx', '.xlsm'):
        raise ValueError('请选择 .xls、.xlsx 或 .xlsm 文件')
    log.info('打开Excel，类型=%s', path.suffix.lower())
    return process_book(load_raw_book(path), name, duration, layouts)
