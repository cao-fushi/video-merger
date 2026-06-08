"""视频批量合成工具 - 主程序入口"""
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from video_merger.gui.main_window import MainWindow


def main():
    """主函数"""
    # 设置高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # 设置应用样式 - 支持中文显示
    app.setStyleSheet("""
        * {
            font-family: "Microsoft YaHei", "SimHei", "SimSun", "WenQuanYi Micro Hei", sans-serif;
            font-size: 12px;
        }
        QMainWindow {
            background-color: #f5f5f5;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #cccccc;
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 15px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QPushButton {
            padding: 6px 16px;
            border: 1px solid #cccccc;
            border-radius: 4px;
            background-color: #ffffff;
            min-height: 24px;
        }
        QPushButton:hover {
            background-color: #e6e6e6;
            border-color: #999999;
        }
        QPushButton:pressed {
            background-color: #d9d9d9;
        }
        QPushButton:disabled {
            background-color: #f0f0f0;
            color: #999999;
        }
        QTableWidget {
            border: 1px solid #cccccc;
            border-radius: 3px;
            background-color: #ffffff;
            gridline-color: #e0e0e0;
        }
        QTableWidget::item {
            padding: 5px;
        }
        QTableWidget::item:selected {
            background-color: #3399ff;
            color: white;
        }
        QHeaderView::section {
            background-color: #f0f0f0;
            border: none;
            border-bottom: 1px solid #cccccc;
            padding: 6px;
            font-weight: bold;
        }
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            padding: 5px 8px;
            border: 1px solid #cccccc;
            border-radius: 4px;
            background-color: #ffffff;
            min-height: 24px;
        }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border-color: #3399ff;
        }
        QComboBox::drop-down {
            border: none;
            padding-right: 8px;
        }
        QProgressBar {
            border: 1px solid #cccccc;
            border-radius: 4px;
            text-align: center;
            background-color: #f0f0f0;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 3px;
        }
        QTextEdit {
            border: 1px solid #cccccc;
            border-radius: 4px;
            background-color: #ffffff;
            font-family: "Consolas", "Microsoft YaHei", monospace;
            font-size: 11px;
        }
        QCheckBox {
            spacing: 6px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
    """)

    # 创建主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
