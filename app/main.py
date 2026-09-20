import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox
from app.config import setup_logging
from app.ui.main_window import MainWindow
from app.ui.appearance import configure_appearance


def main():
    application = QApplication(sys.argv)
    configure_appearance(application)
    application.setApplicationName('宣讲会信息助手')
    application.setOrganizationName('TalkAssistant')
    try:
        setup_logging()
    except OSError:
        logging.getLogger('app').addHandler(logging.NullHandler())
    def exception_hook(exc_type, exc_value, traceback):
        logging.getLogger('app').error('未处理异常，类型=%s', exc_type.__name__)
        QMessageBox.critical(None, '程序遇到问题', '操作未完成，请重新打开程序后重试。原始 Excel 不会被修改。')
    sys.excepthook = exception_hook
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == '__main__':
    raise SystemExit(main())
