"""只提取当前行的原文提示，不继承其他企业或空白行的信息。"""
import re
from app.import_layout import header_key
from app.phone_utils import text_value

NOTE_HEADERS = re.compile(r'备注|提示|说明|注意事项|特殊要求|补充|接待要求')
NOTE_CONTENT = re.compile(r'备用|若|如果|需要|无需|不用|仅供|请|待定|另行|多媒体|设备|调整|取消|改为|调到|通知|确认|开门|开启|开放')


def collect_row_notes(sheet, row, columns, first_data_row):
    notes = []
    mapped = set(columns.values())
    for col in range(sheet.width):
        if col in mapped:
            continue
        value = text_value(sheet.value(row, col))
        if not value:
            continue
        headers = [header_key(sheet.value(r, col, merged=True)) for r in range(max(0, first_data_row-3), first_data_row)]
        if any(NOTE_HEADERS.search(header) for header in headers) or NOTE_CONTENT.search(value):
            # 清单一条记录占一行，仅把单元格内部换行/连续空白合为一个空格。
            value = re.sub(r'\s+', ' ', value).strip()
            if value not in notes:
                notes.append(value)
    return notes
