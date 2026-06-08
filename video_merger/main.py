"""视频批量合成工具 - 主程序入口"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from video_merger.gui.main_window import MainWindow


# 飞书/钉钉风格 - 专业办公工具设计
PROFESSIONAL_THEME = """
/* ============================================
   视频批量合成工具 - 专业办公风格
   设计理念：简洁、专业、高效
   参考：飞书、钉钉、Notion 等现代办公工具
   ============================================ */

/* ========== 全局基础 ========== */
* {
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", -apple-system, BlinkMacSystemFont, sans-serif;
}

QWidget {
    background-color: #f5f6f7;
    color: #1f2329;
    font-size: 12px;
    line-height: 1.5;
}

QMainWindow {
    background-color: #f5f6f7;
}

/* ========== 分组框 - 卡片式设计 ========== */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e5e6eb;
    border-radius: 12px;
    margin-top: 20px;
    padding: 24px 20px 20px 20px;
    font-weight: 600;
    font-size: 14px;
    color: #1f2329;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 20px;
    padding: 0 12px;
    color: #3370ff;
    background-color: #ffffff;
    font-size: 15px;
    font-weight: 600;
}

/* ========== 按钮系统 ========== */

/* 默认按钮 */
QPushButton {
    background-color: #ffffff;
    color: #1f2329;
    border: 1px solid #dee0e3;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    min-height: 30px;
}

QPushButton:hover {
    background-color: #f5f6f7;
    border-color: #3370ff;
    color: #3370ff;
}

QPushButton:pressed {
    background-color: #e8e9eb;
}

QPushButton:disabled {
    background-color: #f5f6f7;
    color: #bbbfc4;
    border-color: #e5e6eb;
}

/* 主要按钮 - 蓝色实心 */
QPushButton#btn_primary {
    background-color: #3370ff;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

QPushButton#btn_primary:hover {
    background-color: #2860e1;
}

QPushButton#btn_primary:pressed {
    background-color: #1d4ed8;
}

QPushButton#btn_primary:disabled {
    background-color: #94bfff;
    color: #ffffff;
}

/* 危险按钮 - 红色 */
QPushButton#btn_danger {
    background-color: #ffffff;
    color: #f53f3f;
    border: 1px solid #f53f3f;
}

QPushButton#btn_danger:hover {
    background-color: #fff2f0;
    border-color: #f53f3f;
}

QPushButton#btn_danger:pressed {
    background-color: #ffe0e0;
}

/* 成功按钮 - 绿色 */
QPushButton#btn_success {
    background-color: #00b42a;
    color: #ffffff;
    border: none;
}

QPushButton#btn_success:hover {
    background-color: #009a24;
}

QPushButton#btn_success:pressed {
    background-color: #00801d;
}

/* 链接按钮 */
QPushButton#btn_link {
    background-color: transparent;
    color: #3370ff;
    border: none;
    padding: 4px 8px;
    min-height: 24px;
    font-size: 12px;
}

QPushButton#btn_link:hover {
    background-color: #f2f3ff;
    border-radius: 6px;
}

/* ========== 输入框 ========== */
QLineEdit {
    background-color: #ffffff;
    color: #1f2329;
    border: 1px solid #dee0e3;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #3370ff;
    selection-color: #ffffff;
}

QLineEdit:focus {
    border-color: #3370ff;
    background-color: #ffffff;
}

QLineEdit:hover {
    border-color: #bbbfc4;
}

QLineEdit::placeholder {
    color: #bbbfc4;
}

/* ========== 数值输入框 ========== */
QSpinBox, QDoubleSpinBox {
    background-color: #ffffff;
    color: #1f2329;
    border: 1px solid #dee0e3;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 13px;
    min-height: 30px;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #3370ff;
}

QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #bbbfc4;
}

QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid #dee0e3;
    border-bottom: 1px solid #dee0e3;
    border-top-right-radius: 6px;
    background-color: #f5f6f7;
}

QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 24px;
    border-left: 1px solid #dee0e3;
    border-bottom-right-radius: 6px;
    background-color: #f5f6f7;
}

QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #e8e9eb;
}

QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
    background-color: #3370ff;
}

QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    width: 8px;
    height: 8px;
}

QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    width: 8px;
    height: 8px;
}

/* ========== 下拉框 ========== */
QComboBox {
    background-color: #ffffff;
    color: #1f2329;
    border: 1px solid #dee0e3;
    border-radius: 6px;
    padding: 5px 10px;
    padding-right: 30px;
    font-size: 13px;
    min-height: 30px;
}

QComboBox:focus {
    border-color: #3370ff;
}

QComboBox:hover {
    border-color: #bbbfc4;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 30px;
    border-left: 1px solid #dee0e3;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: transparent;
}

QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1f2329;
    border: 1px solid #e5e6eb;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #f2f3ff;
    selection-color: #3370ff;
    outline: none;
}

QComboBox QAbstractItemView::item {
    padding: 8px 12px;
    border-radius: 4px;
    min-height: 24px;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #f2f3ff;
    color: #3370ff;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #f5f6f7;
}

/* ========== 复选框 ========== */
QCheckBox {
    spacing: 10px;
    color: #1f2329;
    font-size: 13px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #dee0e3;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #3370ff;
    border-color: #3370ff;
}

QCheckBox::indicator:hover {
    border-color: #3370ff;
}

/* ========== 表格 ========== */
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #fafbfc;
    color: #1f2329;
    border: 1px solid #e5e6eb;
    border-radius: 12px;
    gridline-color: #f0f1f2;
    selection-background-color: #f2f3ff;
    selection-color: #1f2329;
    font-size: 13px;
}

QTableWidget::item {
    padding: 10px 8px;
    border-bottom: 1px solid #f0f1f2;
}

QTableWidget::item:selected {
    background-color: #f2f3ff;
    color: #3370ff;
}

QTableWidget::item:hover {
    background-color: #f5f6f7;
}

QHeaderView::section {
    background-color: #fafbfc;
    color: #646a73;
    border: none;
    border-bottom: 1px solid #e5e6eb;
    border-right: 1px solid #f0f1f2;
    padding: 12px 10px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QHeaderView::section:horizontal:hover {
    background-color: #f0f1f2;
    color: #1f2329;
}

/* ========== 进度条 ========== */
QProgressBar {
    background-color: #f0f1f2;
    border: none;
    border-radius: 12px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    font-size: 11px;
    height: 24px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #3370ff, stop:0.5 #5b8ff9, stop:1 #3370ff);
    border-radius: 12px;
}

/* ========== 文本编辑器 (日志) ========== */
QTextEdit {
    background-color: #fafbfc;
    color: #1f2329;
    border: 1px solid #e5e6eb;
    border-radius: 10px;
    padding: 14px;
    font-family: "JetBrains Mono", "Cascadia Code", "SF Mono", "Consolas", "Microsoft YaHei", monospace;
    font-size: 12px;
    line-height: 1.6;
    selection-background-color: #3370ff;
    selection-color: #ffffff;
}

/* ========== 分割器 ========== */
QSplitter::handle {
    background-color: #e5e6eb;
    width: 1px;
    margin: 8px 0;
}

QSplitter::handle:hover {
    background-color: #3370ff;
    width: 3px;
}

/* ========== 标签 ========== */
QLabel {
    color: #646a73;
    padding: 2px;
    font-size: 13px;
}

QLabel#label_title {
    color: #1f2329;
    font-size: 14px;
    font-weight: 600;
}

QLabel#label_subtitle {
    color: #8f959e;
    font-size: 12px;
}

QLabel#label_accent {
    color: #3370ff;
    font-weight: 600;
}

/* ========== 滚动条 ========== */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    border-radius: 4px;
    margin: 4px 2px;
}

QScrollBar::handle:vertical {
    background-color: #dee0e3;
    border-radius: 4px;
    min-height: 40px;
}

QScrollBar::handle:vertical:hover {
    background-color: #bbbfc4;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    border-radius: 4px;
    margin: 2px 4px;
}

QScrollBar::handle:horizontal {
    background-color: #dee0e3;
    border-radius: 4px;
    min-width: 40px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #bbbfc4;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ========== 工具提示 ========== */
QToolTip {
    background-color: #1f2329;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}

/* ========== 菜单 ========== */
QMenu {
    background-color: #ffffff;
    color: #1f2329;
    border: 1px solid #e5e6eb;
    border-radius: 10px;
    padding: 6px;
}

QMenu::item {
    padding: 10px 24px;
    border-radius: 6px;
    font-size: 13px;
}

QMenu::item:selected {
    background-color: #f2f3ff;
    color: #3370ff;
}

QMenu::separator {
    height: 1px;
    background-color: #f0f1f2;
    margin: 4px 10px;
}

/* ========== 消息框 ========== */
QMessageBox {
    background-color: #ffffff;
}

QMessageBox QLabel {
    color: #1f2329;
    font-size: 14px;
    padding: 8px;
}

QMessageBox QPushButton {
    min-width: 80px;
    padding: 8px 20px;
}

/* ========== 选项卡 (如果有的话) ========== */
QTabWidget::pane {
    background-color: #ffffff;
    border: 1px solid #e5e6eb;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: transparent;
    color: #646a73;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 500;
}

QTabBar::tab:selected {
    color: #3370ff;
    border-bottom-color: #3370ff;
}

QTabBar::tab:hover {
    color: #1f2329;
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

    # 应用专业主题
    app.setStyleSheet(PROFESSIONAL_THEME)

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
