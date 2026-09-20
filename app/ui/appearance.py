import os
from pathlib import Path
from PySide6.QtGui import QFont, QFontDatabase


def configure_appearance(application):
    # 离屏验收插件不枚举 Windows 字体，显式加载本机字体以验证中文渲染。
    if application.platformName() == 'offscreen':
        font_path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts' / 'msyh.ttc'
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))
    font = QFont()
    font.setFamilies(['Microsoft YaHei UI', 'Microsoft YaHei', 'SimSun', 'Segoe UI'])
    font.setPointSize(10)
    application.setFont(font)
