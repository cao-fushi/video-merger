"""视频批量合成工具 - 主程序入口"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from video_merger.gui.main_window import MainWindow


# 深色科技风格配色方案
DARK_THEME = """
/* ========== 全局基础 ========== */
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
    font-size: 12px;
}

QMainWindow {
    background-color: #1a1a2e;
}

/* ========== 分组框 ========== */
QGroupBox {
    background-color: #16213e;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    margin-top: 14px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
    font-size: 13px;
    color: #00d4ff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: #00d4ff;
    background-color: #16213e;
}

/* ========== 按钮 ========== */
QPushButton {
    background-color: #2a2a4a;
    color: #e0e0e0;
    border: 1px solid #3a3a5a;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    min-height: 28px;
}

QPushButton:hover {
    background-color: #3a3a5a;
    border-color: #00d4ff;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #1a1a3e;
    border-color: #00aaff;
}

QPushButton:disabled {
    background-color: #1a1a2e;
    color: #555577;
    border-color: #2a2a3a;
}

/* 主操作按钮 - 开始合成 */
QPushButton#btn_start {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #00b4d8, stop:1 #0077b6);
    color: #ffffff;
    border: none;
    font-size: 14px;
    padding: 10px 24px;
}

QPushButton#btn_start:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #00d4ff, stop:1 #00aaff);
}

QPushButton#btn_start:disabled {
    background: #2a2a4a;
    color: #555577;
}

/* 取消按钮 */
QPushButton#btn_cancel {
    background-color: #e63946;
    color: #ffffff;
    border: none;
}

QPushButton#btn_cancel:hover {
    background-color: #ff4d5a;
}

QPushButton#btn_cancel:disabled {
    background-color: #2a2a4a;
    color: #555577;
    border: 1px solid #3a3a5a;
}

/* 预览按钮 */
QPushButton#btn_preview {
    background-color: #2a2a4a;
    border: 1px solid #00d4ff;
    color: #00d4ff;
}

QPushButton#btn_preview:hover {
    background-color: #00d4ff;
    color: #1a1a2e;
}

/* ========== 输入框 ========== */
QLineEdit {
    background-color: #1a1a3e;
    color: #e0e0e0;
    border: 1px solid #3a3a5a;
    border-radius: 6px;
    padding: 8px 10px;
    selection-background-color: #00d4ff;
    selection-color: #1a1a2e;
}

QLineEdit:focus {
    border-color: #00d4ff;
    background-color: #1e1e42;
}

/* ========== 数值输入框 ========== */
QSpinBox, QDoubleSpinBox {
    background-color: #1a1a3e;
    color: #e0e0e0;
    border: 1px solid #3a3a5a;
    border-radius: 6px;
    padding: 6px 10px;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #00d4ff;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
    background-color: #2a2a4a;
    border-left: 1px solid #3a3a5a;
    border-top-right-radius: 5px;
    width: 20px;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #2a2a4a;
    border-left: 1px solid #3a3a5a;
    border-bottom-right-radius: 5px;
    width: 20px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #3a3a5a;
}

/* ========== 下拉框 ========== */
QComboBox {
    background-color: #1a1a3e;
    color: #e0e0e0;
    border: 1px solid #3a3a5a;
    border-radius: 6px;
    padding: 8px 10px;
    min-height: 28px;
}

QComboBox:focus {
    border-color: #00d4ff;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #00d4ff;
    margin-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #1a1a3e;
    color: #e0e0e0;
    border: 1px solid #3a3a5a;
    selection-background-color: #00d4ff;
    selection-color: #1a1a2e;
}

/* ========== 复选框 ========== */
QCheckBox {
    spacing: 8px;
    color: #e0e0e0;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #3a3a5a;
    border-radius: 4px;
    background-color: #1a1a3e;
}

QCheckBox::indicator:checked {
    background-color: #00d4ff;
    border-color: #00d4ff;
}

QCheckBox::indicator:hover {
    border-color: #00d4ff;
}

/* ========== 表格 ========== */
QTableWidget {
    background-color: #1a1a3e;
    alternate-background-color: #1e1e42;
    color: #e0e0e0;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    gridline-color: #2a2a4a;
    selection-background-color: #00d4ff;
    selection-color: #1a1a2e;
}

QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #2a2a4a;
}

QTableWidget::item:selected {
    background-color: #00d4ff;
    color: #1a1a2e;
}

QHeaderView::section {
    background-color: #16213e;
    color: #00d4ff;
    border: none;
    border-bottom: 2px solid #00d4ff;
    border-right: 1px solid #2a2a4a;
    padding: 10px 8px;
    font-weight: bold;
    font-size: 12px;
}

QHeaderView::section:horizontal:hover {
    background-color: #1e2d50;
}

/* ========== 进度条 ========== */
QProgressBar {
    background-color: #1a1a3e;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    height: 24px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #00b4d8, stop:0.5 #00d4ff, stop:1 #00b4d8);
    border-radius: 7px;
    margin: 2px;
}

/* ========== 文本编辑器 (日志) ========== */
QTextEdit {
    background-color: #0d1117;
    color: #8b949e;
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    padding: 10px;
    font-family: "Cascadia Code", "Consolas", "Microsoft YaHei", monospace;
    font-size: 11px;
    selection-background-color: #264f78;
}

/* ========== 分割器 ========== */
QSplitter::handle {
    background-color: #2a2a4a;
    width: 2px;
}

QSplitter::handle:hover {
    background-color: #00d4ff;
}

/* ========== 标签 ========== */
QLabel {
    color: #b0b0c0;
    padding: 2px;
}

QLabel#label_title {
    color: #00d4ff;
    font-size: 14px;
    font-weight: bold;
}

QLabel#label_hint {
    color: #666688;
    font-size: 11px;
}

/* ========== 滚动条 ========== */
QScrollBar:vertical {
    background-color: #1a1a2e;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #3a3a5a;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00d4ff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #1a1a2e;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #3a3a5a;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #00d4ff;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ========== 工具提示 ========== */
QToolTip {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #00d4ff;
    border-radius: 4px;
    padding: 6px;
}

/* ========== 菜单 ========== */
QMenu {
    background-color: #16213e;
    color: #e0e0e0;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #00d4ff;
    color: #1a1a2e;
}

QMenu::separator {
    height: 1px;
    background-color: #2a2a4a;
    margin: 4px 8px;
}

/* ========== 消息框 ========== */
QMessageBox {
    background-color: #16213e;
}

QMessageBox QLabel {
    color: #e0e0e0;
    font-size: 13px;
}

QMessageBox QPushButton {
    min-width: 80px;
}
"""


def main():
    """主函数"""
    # 设置高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    font.setHintingPreference(QFont.PreferNoHinting)
    app.setFont(font)

    # 应用深色主题
    app.setStyleSheet(DARK_THEME)

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
