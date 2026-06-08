"""视频批量合成工具 - 主程序入口"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from video_merger.gui.main_window import MainWindow


# 亮色现代风格配色方案
LIGHT_THEME = """
/* ========== 全局基础 ========== */
QWidget {
    background-color: #f8f9fa;
    color: #2d3436;
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif;
    font-size: 12px;
}

QMainWindow {
    background-color: #f8f9fa;
}

/* ========== 分组框 ========== */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    margin-top: 16px;
    padding: 18px 14px 14px 14px;
    font-weight: bold;
    font-size: 13px;
    color: #2d3436;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 10px;
    color: #0984e3;
    background-color: #ffffff;
}

/* ========== 按钮 ========== */
QPushButton {
    background-color: #ffffff;
    color: #2d3436;
    border: 1px solid #dfe6e9;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: bold;
    min-height: 28px;
}

QPushButton:hover {
    background-color: #dfe6e9;
    border-color: #0984e3;
    color: #0984e3;
}

QPushButton:pressed {
    background-color: #b2bec3;
}

QPushButton:disabled {
    background-color: #f1f2f6;
    color: #b2bec3;
    border-color: #e0e0e0;
}

/* 主操作按钮 - 开始合成 */
QPushButton#btn_start {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #0984e3, stop:1 #74b9ff);
    color: #ffffff;
    border: none;
    font-size: 14px;
    padding: 12px 28px;
}

QPushButton#btn_start:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #0770c2, stop:1 #5aa3e8);
}

QPushButton#btn_start:disabled {
    background: #dfe6e9;
    color: #b2bec3;
}

/* 取消按钮 */
QPushButton#btn_cancel {
    background-color: #d63031;
    color: #ffffff;
    border: none;
}

QPushButton#btn_cancel:hover {
    background-color: #e84393;
}

QPushButton#btn_cancel:disabled {
    background-color: #dfe6e9;
    color: #b2bec3;
    border: 1px solid #e0e0e0;
}

/* 预览按钮 */
QPushButton#btn_preview {
    background-color: #ffffff;
    border: 2px solid #0984e3;
    color: #0984e3;
    font-weight: bold;
}

QPushButton#btn_preview:hover {
    background-color: #0984e3;
    color: #ffffff;
}

/* ========== 输入框 ========== */
QLineEdit {
    background-color: #ffffff;
    color: #2d3436;
    border: 2px solid #dfe6e9;
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: #74b9ff;
    selection-color: #2d3436;
}

QLineEdit:focus {
    border-color: #0984e3;
    background-color: #f8f9fa;
}

/* ========== 数值输入框 ========== */
QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    color: #2d3436;
    border: 2px solid #dfe6e9;
    border-radius: 8px;
    padding: 6px 10px;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #0984e3;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
    background-color: #dfe6e9;
    border-left: 1px solid #e0e0e0;
    border-top-right-radius: 6px;
    width: 22px;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #dfe6e9;
    border-left: 1px solid #e0e0e0;
    border-bottom-right-radius: 6px;
    width: 22px;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #0984e3;
}

/* ========== 下拉框 ========== */
QComboBox {
    background-color: #ffffff;
    color: #2d3436;
    border: 2px solid #dfe6e9;
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 28px;
}

QComboBox:focus {
    border-color: #0984e3;
}

QComboBox::drop-down {
    border: none;
    width: 32px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #0984e3;
    margin-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #2d3436;
    border: 1px solid #dfe6e9;
    selection-background-color: #74b9ff;
    selection-color: #2d3436;
    border-radius: 4px;
}

/* ========== 复选框 ========== */
QCheckBox {
    spacing: 8px;
    color: #2d3436;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border: 2px solid #b2bec3;
    border-radius: 5px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #0984e3;
    border-color: #0984e3;
}

QCheckBox::indicator:hover {
    border-color: #0984e3;
}

/* ========== 表格 ========== */
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f8f9fa;
    color: #2d3436;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    gridline-color: #f1f2f6;
    selection-background-color: #74b9ff;
    selection-color: #2d3436;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #f1f2f6;
}

QTableWidget::item:selected {
    background-color: #74b9ff;
    color: #2d3436;
}

QHeaderView::section {
    background-color: #0984e3;
    color: #ffffff;
    border: none;
    border-right: 1px solid #0770c2;
    padding: 10px 8px;
    font-weight: bold;
    font-size: 12px;
}

QHeaderView::section:horizontal:hover {
    background-color: #0770c2;
}

/* ========== 进度条 ========== */
QProgressBar {
    background-color: #f1f2f6;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    text-align: center;
    color: #2d3436;
    font-weight: bold;
    height: 26px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #0984e3, stop:0.5 #74b9ff, stop:1 #0984e3);
    border-radius: 9px;
    margin: 2px;
}

/* ========== 文本编辑器 (日志) ========== */
QTextEdit {
    background-color: #ffffff;
    color: #2d3436;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 12px;
    font-family: "Cascadia Code", "Consolas", "Microsoft YaHei", monospace;
    font-size: 11px;
    selection-background-color: #74b9ff;
}

/* ========== 分割器 ========== */
QSplitter::handle {
    background-color: #e0e0e0;
    width: 3px;
}

QSplitter::handle:hover {
    background-color: #0984e3;
}

/* ========== 标签 ========== */
QLabel {
    color: #636e72;
    padding: 2px;
}

QLabel#label_title {
    color: #0984e3;
    font-size: 14px;
    font-weight: bold;
}

QLabel#label_hint {
    color: #b2bec3;
    font-size: 11px;
}

/* ========== 滚动条 ========== */
QScrollBar:vertical {
    background-color: #f8f9fa;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #b2bec3;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #0984e3;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #f8f9fa;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #b2bec3;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #0984e3;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ========== 工具提示 ========== */
QToolTip {
    background-color: #ffffff;
    color: #2d3436;
    border: 1px solid #0984e3;
    border-radius: 6px;
    padding: 8px;
}

/* ========== 菜单 ========== */
QMenu {
    background-color: #ffffff;
    color: #2d3436;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 10px 28px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #74b9ff;
    color: #2d3436;
}

QMenu::separator {
    height: 1px;
    background-color: #e0e0e0;
    margin: 4px 10px;
}

/* ========== 消息框 ========== */
QMessageBox {
    background-color: #ffffff;
}

QMessageBox QLabel {
    color: #2d3436;
    font-size: 13px;
}

QMessageBox QPushButton {
    min-width: 80px;
}
"""


def main():
    """主函数"""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    font.setHintingPreference(QFont.PreferNoHinting)
    app.setFont(font)

    # 应用亮色主题
    app.setStyleSheet(LIGHT_THEME)

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
