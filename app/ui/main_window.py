import logging
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QTableWidgetItem, QMessageBox

from app.config import load_config, save_config
from app.excel_reader import read_excel
from app.exporter import export_records
from app.ui.import_dialog import ImportDialog
from app.ui.layout import build_main_ui
from app.schedule_builder import build_schedule, short_room

log = logging.getLogger(__name__)


class ReadWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, path, name, duration, parent=None, layouts=None):
        super().__init__(parent)
        self.path, self.name, self.duration = path, name, duration
        self.layouts = layouts

    def run(self):
        try:
            self.succeeded.emit(read_excel(self.path, self.name, self.duration, self.layouts))
        except Exception as exc:
            log.error('Excel解析异常，类型=%s', type(exc).__name__)
            if isinstance(exc, PermissionError):
                message = '无法访问文件。请关闭占用文件的程序，或把文件复制到可读取的文件夹。'
            elif isinstance(exc, ValueError):
                message = '读取失败：' + str(exc)
            else:
                message = '读取失败：文件可能损坏、被加密，或扩展名与内容不符。请用 Excel 另存为新文件后重试。'
            self.failed.emit(message)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.records, self.visible_records = [], []
        self.source_path = None
        self.loaded_name = ''
        self.worker = None
        self.raw_book = None
        self.layouts, self.suggested_layouts = {}, {}
        self.layout_path = None
        build_main_ui(self, load_config())

    def refresh_schedule(self):
        schedule = build_schedule(self.records, self.sort_schedule.isChecked())
        self.schedule_text.setPlainText(schedule.text)
        self.copy_schedule.setEnabled(bool(schedule.count))
        self.schedule_summary.setText(f'共 {schedule.count} 条；{schedule.attention} 条需核对。包含全部读取结果，不受搜索影响。')

    def copy_schedule_text(self):
        if self.records:
            self.copy(self.schedule_text.toPlainText(), '接待清单已复制，可粘贴到手机')

    def current_record(self):
        index = self.table.currentRow()
        return self.visible_records[index] if 0 <= index < len(self.visible_records) else None

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, '选择宣讲会 Excel', self.path_edit.text(), 'Excel 工作簿 (*.xls *.xlsx *.xlsm)')
        if path:
            self.path_edit.setText(path)
            self.statusBar().showMessage('已选择文件，请点击“读取 Excel”。', 5000)

    def persist(self):
        try:
            save_config({'name': self.name_edit.text().strip() or '', 'duration': self.duration.value(),
                         'remember_path': self.remember.isChecked(),
                         'last_path': self.path_edit.text().strip() if self.remember.isChecked() else ''})
        except OSError:
            self.statusBar().showMessage('设置保存失败，本次仍可正常使用。', 6000)

    def set_busy(self, busy):
        for widget in (self.path_edit, self.choose_btn, self.name_edit, self.duration, self.read_btn, self.reload_btn):
            widget.setEnabled(not busy)
        self.export_btn.setEnabled(not busy and bool(self.records))
        self.layout_btn.setEnabled(not busy and self.raw_book is not None)

    def configure_columns(self):
        if self.raw_book is None:
            return
        if Path(self.path_edit.text().strip()).resolve() != self.source_path:
            self.statusBar().showMessage('文件路径已改变，请先读取新文件，再指定列。', 6000)
            return
        dialog = ImportDialog(self.raw_book, self.name_edit.text().strip(), self.layouts, self.suggested_layouts, self)
        if dialog.exec():
            self.layouts = dialog.layouts
            self.layout_path = self.source_path
            self.start_read()

    def start_read(self):
        if self.worker is not None:
            return
        path, name = self.path_edit.text().strip(), self.name_edit.text().strip()
        if not path or not name:
            QMessageBox.warning(self, '请补充信息', '请选择 Excel 文件并填写筛选姓名。')
            return
        self.persist()
        if self.layout_path != Path(path).resolve():
            self.layouts = {}
            self.layout_path = Path(path).resolve()
        self.raw_book = None
        self.records = []
        self.refresh_schedule()
        self.refresh_list()
        self.warnings.hide()
        self.stats.setText('正在读取全部工作表，请稍候……')
        self.set_busy(True)
        self.worker = ReadWorker(path, name, self.duration.value(), self, self.layouts)
        self.worker.succeeded.connect(self.read_succeeded)
        self.worker.failed.connect(self.read_failed)
        self.worker.finished.connect(self.read_finished)
        self.worker.start()

    def read_succeeded(self, result):
        self.records = result.records
        self.refresh_schedule()
        self.raw_book = result.raw_book
        self.suggested_layouts = result.layouts
        self.source_path = Path(self.worker.path).resolve()
        self.loaded_name = self.worker.name
        complete = sum(not r.issues for r in self.records)
        phone_ok = sum(r.phone_valid for r in self.records)
        count = len(self.records)
        self.stats.setText(f'{self.loaded_name} · {count} 条记录 · {count-complete} 条需核对')
        self.stats.setToolTip(f'信息完整：{complete}；手机号正常：{phone_ok}；工作表：{result.sheet_count}')
        self.stats.setTextFormat(Qt.PlainText)
        self.warnings.setPlainText('\n'.join(result.warnings))
        self.warnings.setVisible(bool(result.warnings))
        if not count and result.warnings:
            self.options_btn.setChecked(True)
        self.search.clear()
        self.refresh_list()
        self.statusBar().showMessage('读取完成，请留意上方识别说明。' if count else '没有可用匹配记录。请检查上方提示，或打开“列设置 / 原表预览”。', 7000)

    def read_failed(self, message):
        self.stats.setText('读取失败，请检查文件后重试。')
        self.warnings.setPlainText(message)
        self.warnings.show()
        self.statusBar().showMessage('读取失败', 5000)

    def read_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.set_busy(False)

    def refresh_list(self):
        query = self.search.text().strip().casefold()
        self.visible_records = [r for r in self.records if not query or any(query in v.casefold() for v in (r.company, r.contact, r.phone))]
        self.table.blockSignals(True)
        self.table.clearContents()
        self.table.setRowCount(len(self.visible_records))
        for i, record in enumerate(self.visible_records):
            for col, value in enumerate((record.company or '公司名称缺失', record.start_time.strftime('%m-%d %H:%M') if record.start_time else '时间待核对', short_room(record.address)[0])):
                item = QTableWidgetItem(value)
                item.setToolTip(f'{record.company}\n{record.time_text}\n{record.address}\n{record.status}')
                if record.issues:
                    item.setForeground(QColor('#b42318'))
                self.table.setItem(i, col, item)
        self.table.clearSelection()
        self.table.setCurrentCell(-1, -1)
        self.table.blockSignals(False)
        if self.visible_records:
            self.table.selectRow(0)
        self.list_count.setText(f'显示 {len(self.visible_records)} / {len(self.records)} 条企业记录')
        self.show_record()

    def show_record(self):
        record = self.current_record()
        for button in (self.copy_phone, self.copy_message, self.copy_all, self.previous, self.next):
            button.setEnabled(False)
        if record is None:
            self.company.setText('暂无企业，请读取文件或调整搜索')
            self.record_status.clear()
            for label in (self.contact, self.phone, self.time, self.address, self.source):
                label.setText('—')
                label.setStyleSheet('')
                label.setToolTip('')
            self.message.clear()
            self.position.setText('0 / 0')
            return
        self.company.setText(record.company or '公司名称缺失')
        self.company.setStyleSheet('font-size:18px; font-weight:600;' + ('color:#b42318;' if not record.company else ''))
        self.record_status.setText(('⚠ 信息异常：' if record.issues else '信息完整 · 正常') + (record.status if record.issues else ''))
        self.record_status.setStyleSheet('color: #b42318;' if record.issues else 'color: #187047;')
        self.record_status.setVisible(bool(record.issues))
        for label, value, valid in ((self.contact, record.contact, bool(record.contact)), (self.phone, record.phone, record.phone_valid),
                                    (self.time, record.time_text or record.raw_time, bool(record.time_text)), (self.address, record.address, bool(record.address) and not any('地点' in s for s in record.issues))):
            label.setText(value or '未填写')
            label.setStyleSheet('' if valid else 'color: #b42318;')
        self.time.setToolTip('原始值：' + record.raw_time)
        self.phone.setToolTip('原始值：' + record.raw_phone)
        self.address.setToolTip('原始值：' + record.raw_address)
        self.source.setText(f'{record.sheet}，第 {record.row} 行')
        self.message.setPlainText(record.message or record.message_error)
        self.message.setStyleSheet('' if record.message else 'color: #b42318;')
        self.copy_phone.setEnabled(bool(record.phone))
        self.copy_message.setEnabled(bool(record.message))
        self.copy_all.setEnabled(True)
        index = self.table.currentRow()
        self.position.setText(f'{index+1} / {len(self.visible_records)}')
        self.previous.setEnabled(index > 0)
        self.next.setEnabled(index < len(self.visible_records)-1)

    def copy(self, text, status):
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage(status, 2500)

    def copy_number(self):
        record = self.current_record()
        if record and record.phone:
            self.copy(record.phone, '已复制手机号' if record.phone_valid else '已复制原号码，请先核对：手机号格式异常')

    def copy_sms(self):
        record = self.current_record()
        if record and record.message:
            self.copy(record.message, '短信已复制')

    def copy_details(self):
        record = self.current_record()
        if record:
            self.copy(record.all_info(), '已复制全部信息')

    def move(self, offset):
        row = self.table.currentRow() + offset
        if 0 <= row < len(self.visible_records):
            self.table.selectRow(row)

    def export(self):
        if not self.records:
            return
        import re
        safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', self.loaded_name)
        suggested = str(self.source_path.parent / f'{safe_name}_宣讲短信整理.xlsx')
        path, _ = QFileDialog.getSaveFileName(self, '导出全部处理结果（不受搜索限制）', suggested, 'Excel 工作簿 (*.xlsx)')
        if not path:
            return
        if not Path(path).suffix:
            path += '.xlsx'
        try:
            export_records(self.records, path, self.source_path)
            self.statusBar().showMessage(f'已导出 {len(self.records)} 条记录：{path}', 8000)
        except Exception as exc:
            log.error('导出异常，类型=%s', type(exc).__name__)
            QMessageBox.warning(self, '导出失败', str(exc) if isinstance(exc, ValueError) else '无法写入文件。请确认文件未被 Excel 占用，且文件夹可写。')

    def closeEvent(self, event):
        if self.worker is not None:
            self.statusBar().showMessage('正在读取文件，请读取完成后再关闭。', 5000)
            event.ignore()
            return
        self.persist()
        event.accept()
