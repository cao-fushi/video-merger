"""主窗口模块 - 视频批量合成工具GUI (专业办公风格)"""
import sys
import os
from typing import List, Optional
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit, QCheckBox, QGroupBox,
    QProgressBar, QTextEdit, QMessageBox, QSplitter, QFrame,
    QAbstractItemView, QMenu, QAction, QDialog, QSizePolicy,
    QScrollArea, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette, QPainter, QLinearGradient, QCursor

from ..core.video_info import VideoInfo, get_video_info, batch_get_video_info
from ..core.combination import (
    generate_combinations, generate_random_combinations,
    generate_sequential_combinations, estimate_combination_count
)
from ..core.video_merger import MergeConfig, batch_merge_videos
from ..core.ffmpeg_utils import check_ffmpeg_installed


class MergeThread(QThread):
    """合并线程"""
    progress_updated = pyqtSignal(int, int, float, str)
    finished_signal = pyqtSignal(int, int, list, list)

    def __init__(self, combinations, config):
        super().__init__()
        self.combinations = combinations
        self.config = config
        self._is_cancelled = False

    def run(self):
        def progress_callback(current, total, progress, status):
            if not self._is_cancelled:
                self.progress_updated.emit(current, total, progress, status)

        success, fail, files, reasons = batch_merge_videos(
            self.combinations,
            self.config,
            progress_callback
        )

        if not self._is_cancelled:
            self.finished_signal.emit(success, fail, files, reasons)

    def cancel(self):
        self._is_cancelled = True


class ModernButton(QPushButton):
    """现代化按钮组件"""
    def __init__(self, text, style="default", icon=None, parent=None):
        super().__init__(text, parent)
        self.style_type = style
        self.setObjectName(f"btn_{style}")
        self.setCursor(QCursor(Qt.PointingHandCursor))


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.videos: List[VideoInfo] = []
        self.merge_thread: Optional[MergeThread] = None
        self.start_video: Optional[VideoInfo] = None

        self.init_ui()

        # 检查FFmpeg
        if not check_ffmpeg_installed():
            QMessageBox.warning(
                self, "环境检测",
                "未检测到FFmpeg，请先安装FFmpeg并添加到系统PATH环境变量。\n\n"
                "下载地址: https://ffmpeg.org/download.html"
            )

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("视频批量合成工具")
        self.setMinimumSize(1280, 860)

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ========== 顶部工具栏 ==========
        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e5e6eb;
                border-radius: 12px;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setSpacing(12)
        toolbar_layout.setContentsMargins(20, 16, 20, 16)

        # 左侧：导入按钮组
        import_label = QLabel("导入")
        import_label.setStyleSheet("color: #8f959e; font-size: 12px; font-weight: 600; margin-right: 4px;")
        toolbar_layout.addWidget(import_label)

        btn_add_files = ModernButton("添加文件", "default")
        btn_add_files.clicked.connect(self.add_video_files)

        btn_add_folder = ModernButton("添加文件夹", "default")
        btn_add_folder.clicked.connect(self.add_video_folder)

        toolbar_layout.addWidget(btn_add_files)
        toolbar_layout.addWidget(btn_add_folder)

        # 分隔线
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.VLine)
        separator1.setStyleSheet("background-color: #e5e6eb; max-width: 1px; margin: 4px 8px;")
        toolbar_layout.addWidget(separator1)

        # 数据按钮组
        data_label = QLabel("数据")
        data_label.setStyleSheet("color: #8f959e; font-size: 12px; font-weight: 600; margin-right: 4px;")
        toolbar_layout.addWidget(data_label)

        btn_load_json = ModernButton("导入JSON", "link")
        btn_load_json.clicked.connect(self.load_from_json)

        btn_save_json = ModernButton("导出JSON", "link")
        btn_save_json.clicked.connect(self.save_to_json)

        toolbar_layout.addWidget(btn_load_json)
        toolbar_layout.addWidget(btn_save_json)

        toolbar_layout.addStretch()

        # 右侧：操作按钮组
        btn_remove = ModernButton("移除选中", "danger")
        btn_remove.setObjectName("btn_danger")
        btn_remove.clicked.connect(self.remove_selected)

        btn_clear = ModernButton("清空列表", "danger")
        btn_clear.setObjectName("btn_danger")
        btn_clear.clicked.connect(self.clear_videos)

        toolbar_layout.addWidget(btn_remove)
        toolbar_layout.addWidget(btn_clear)

        main_layout.addWidget(toolbar_widget)

        # ========== 中间内容区 ==========
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # 左侧：视频列表
        left_widget = QWidget()
        left_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e5e6eb;
                border-radius: 12px;
            }
        """)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(20, 20, 20, 20)

        # 视频列表标题
        header_layout = QHBoxLayout()

        title_label = QLabel("视频列表")
        title_label.setObjectName("label_title")
        title_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #1f2329;")
        header_layout.addWidget(title_label)

        self.video_count_label = QLabel("0 个视频")
        self.video_count_label.setObjectName("label_subtitle")
        self.video_count_label.setStyleSheet("""
            QLabel {
                background-color: #f0f1f2;
                color: #646a73;
                border: none;
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        header_layout.addWidget(self.video_count_label)
        header_layout.addStretch()

        left_layout.addLayout(header_layout)

        # 视频表格
        self.video_table = QTableWidget()
        self.video_table.setColumnCount(7)
        self.video_table.setHorizontalHeaderLabels([
            "✓", "序号", "文件名", "时长", "分辨率", "大小", "操作"
        ])
        self.video_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.video_table.setColumnWidth(0, 40)
        self.video_table.setColumnWidth(1, 50)
        self.video_table.setColumnWidth(3, 80)
        self.video_table.setColumnWidth(4, 100)
        self.video_table.setColumnWidth(5, 80)
        self.video_table.setColumnWidth(6, 90)
        self.video_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.video_table.setAlternatingRowColors(True)
        self.video_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.video_table.customContextMenuRequested.connect(self.show_context_menu)
        self.video_table.verticalHeader().setVisible(False)
        self.video_table.verticalHeader().setDefaultSectionSize(48)

        left_layout.addWidget(self.video_table)

        # 空状态提示
        self.empty_hint = QLabel("暂无视频，请点击上方「添加文件」或「添加文件夹」导入")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setStyleSheet("""
            QLabel {
                color: #bbbfc4;
                font-size: 14px;
                padding: 40px;
            }
        """)
        left_layout.addWidget(self.empty_hint)
        self.empty_hint.setVisible(True)

        splitter.addWidget(left_widget)

        # 右侧：设置面板
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(0)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 使用滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QWidget#scroll_content {
                background-color: transparent;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("scroll_content")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)
        scroll_layout.setContentsMargins(0, 0, 12, 0)

        # ===== 合成配置组 =====
        config_group = QGroupBox("合成配置")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(16)

        # 开头视频设置
        config_layout.addWidget(self._create_form_label("开头模式"))
        self.start_mode_combo = QComboBox()
        self.start_mode_combo.addItems(["按顺序轮流", "指定开头视频", "随机选择开头"])
        self.start_mode_combo.currentIndexChanged.connect(self.on_start_mode_changed)
        config_layout.addWidget(self.start_mode_combo)

        # 指定开头视频选择
        self.start_video_widget = QWidget()
        start_video_layout = QHBoxLayout(self.start_video_widget)
        start_video_layout.setContentsMargins(0, 0, 0, 0)
        start_video_layout.setSpacing(10)

        self.start_video_combo = QComboBox()
        self.start_video_combo.setMinimumWidth(150)
        start_video_layout.addWidget(self.start_video_combo, 1)

        self.btn_set_start = ModernButton("确认", "primary")
        self.btn_set_start.setObjectName("btn_primary")
        self.btn_set_start.clicked.connect(self.set_start_video)
        start_video_layout.addWidget(self.btn_set_start)

        config_layout.addWidget(self.start_video_widget)
        self.start_video_widget.setVisible(False)

        # 每组片段数
        config_layout.addWidget(self._create_form_label("每组片段数"))
        self.group_size_spin = QSpinBox()
        self.group_size_spin.setRange(2, 20)
        self.group_size_spin.setValue(2)
        self.group_size_spin.valueChanged.connect(self.update_estimate)
        config_layout.addWidget(self.group_size_spin)

        # 合成数量
        config_layout.addWidget(self._create_form_label("合成数量"))
        count_layout = QHBoxLayout()
        count_layout.setSpacing(10)

        self.count_mode_combo = QComboBox()
        self.count_mode_combo.addItems(["全部组合", "自定义数量"])
        self.count_mode_combo.currentIndexChanged.connect(self.on_count_mode_changed)
        count_layout.addWidget(self.count_mode_combo, 1)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 10000)
        self.count_spin.setValue(100)
        self.count_spin.setEnabled(False)
        count_layout.addWidget(self.count_spin)

        config_layout.addLayout(count_layout)

        # 预计合成数
        self.estimate_label = QLabel("预计合成: 0 个")
        self.estimate_label.setStyleSheet("""
            QLabel {
                background-color: #f2f3ff;
                border: 1px solid #3370ff;
                border-radius: 8px;
                padding: 12px;
                color: #3370ff;
                font-weight: 600;
                font-size: 14px;
            }
        """)
        self.estimate_label.setAlignment(Qt.AlignCenter)
        config_layout.addWidget(self.estimate_label)

        # 文件前缀
        config_layout.addWidget(self._create_form_label("文件前缀"))
        self.prefix_edit = QLineEdit("合成视频")
        self.prefix_edit.setPlaceholderText("输入输出文件名前缀")
        config_layout.addWidget(self.prefix_edit)

        # 输出目录
        config_layout.addWidget(self._create_form_label("输出目录"))
        output_layout = QHBoxLayout()
        output_layout.setSpacing(10)

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("请选择视频输出目录...")
        output_layout.addWidget(self.output_dir_edit, 1)

        btn_select_dir = ModernButton("浏览", "default")
        btn_select_dir.clicked.connect(self.select_output_dir)
        output_layout.addWidget(btn_select_dir)

        config_layout.addLayout(output_layout)

        scroll_layout.addWidget(config_group)

        # ===== 预处理设置组 =====
        preprocess_group = QGroupBox("预处理设置")
        preprocess_layout = QVBoxLayout(preprocess_group)
        preprocess_layout.setSpacing(14)

        # 统一分辨率
        self.enable_resolution_cb = QCheckBox("统一分辨率")
        self.enable_resolution_cb.stateChanged.connect(self.on_preprocess_changed)
        preprocess_layout.addWidget(self.enable_resolution_cb)

        self.resolution_widget = QWidget()
        resolution_layout = QHBoxLayout(self.resolution_widget)
        resolution_layout.setContentsMargins(28, 0, 0, 0)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "1080x1920 (竖屏)", "1920x1080 (横屏)", "720x1280", "1280x720",
            "640x1136", "1136x640", "640x480", "480x640"
        ])
        self.resolution_combo.setEnabled(False)
        resolution_layout.addWidget(self.resolution_combo)
        preprocess_layout.addWidget(self.resolution_widget)
        self.resolution_widget.setVisible(False)

        # 统一帧率
        self.enable_fps_cb = QCheckBox("统一帧率")
        self.enable_fps_cb.stateChanged.connect(self.on_preprocess_changed)
        preprocess_layout.addWidget(self.enable_fps_cb)

        self.fps_widget = QWidget()
        fps_layout = QHBoxLayout(self.fps_widget)
        fps_layout.setContentsMargins(28, 0, 0, 0)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(10, 120)
        self.fps_spin.setValue(30)
        self.fps_spin.setEnabled(False)
        fps_layout.addWidget(self.fps_spin)
        fps_layout.addWidget(QLabel("fps"))
        fps_layout.addStretch()
        preprocess_layout.addWidget(self.fps_widget)
        self.fps_widget.setVisible(False)

        # 分隔线
        preprocess_layout.addWidget(self._create_separator())

        # 编码设置
        preprocess_layout.addWidget(self._create_form_label("编码器"))
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["H.264 (兼容性好)", "H.265 (压缩率高)"])
        preprocess_layout.addWidget(self.codec_combo)

        preprocess_layout.addWidget(self._create_form_label("输出质量"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高质量 (文件较大)", "中等质量 (推荐)", "低质量 (文件较小)"])
        self.quality_combo.setCurrentIndex(1)
        preprocess_layout.addWidget(self.quality_combo)

        # 分隔线
        preprocess_layout.addWidget(self._create_separator())

        # 硬件加速
        preprocess_layout.addWidget(self._create_form_label("硬件加速"))
        self.hw_accel_combo = QComboBox()
        self.hw_accel_combo.addItems(["自动检测 (推荐)", "NVIDIA 显卡加速", "仅使用 CPU"])
        self.hw_accel_combo.setToolTip("自动检测会优先使用NVIDIA显卡加速编码")
        preprocess_layout.addWidget(self.hw_accel_combo)

        scroll_layout.addWidget(preprocess_group)

        # ===== 转场效果组 =====
        transition_group = QGroupBox("转场效果")
        transition_layout = QVBoxLayout(transition_group)
        transition_layout.setSpacing(14)

        # 转场类型
        transition_layout.addWidget(self._create_form_label("转场类型"))
        self.transition_combo = QComboBox()
        self.transition_combo.addItems([
            "无转场 (直接拼接)",
            "淡入淡出",
            "溶解",
            "向左擦除",
            "向右擦除",
            "向左滑动",
            "向右滑动",
            "向左平滑",
            "向右平滑",
            "圆形打开",
            "圆形关闭",
            "像素化",
            "径向",
            "左下对角线",
            "右下对角线"
        ])
        transition_layout.addWidget(self.transition_combo)

        # 转场时长
        transition_layout.addWidget(self._create_form_label("转场时长"))
        trans_dur_layout = QHBoxLayout()
        trans_dur_layout.setSpacing(10)

        self.transition_duration_spin = QDoubleSpinBox()
        self.transition_duration_spin.setRange(0.1, 3.0)
        self.transition_duration_spin.setValue(0.5)
        self.transition_duration_spin.setSingleStep(0.1)
        self.transition_duration_spin.setSuffix(" 秒")
        trans_dur_layout.addWidget(self.transition_duration_spin)
        trans_dur_layout.addStretch()

        transition_layout.addLayout(trans_dur_layout)

        # 提示
        hint_label = QLabel("💡 转场效果会让视频过渡更自然，但会增加处理时间")
        hint_label.setObjectName("label_hint")
        hint_label.setStyleSheet("color: #8f959e; font-size: 12px; padding: 4px 0;")
        hint_label.setWordWrap(True)
        transition_layout.addWidget(hint_label)

        scroll_layout.addWidget(transition_group)

        scroll_layout.addStretch()

        scroll_area.setWidget(scroll_content)
        right_layout.addWidget(scroll_area)

        # ===== 操作按钮区 =====
        btn_widget = QWidget()
        btn_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e5e6eb;
                border-radius: 12px;
            }
        """)
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setSpacing(12)
        btn_layout.setContentsMargins(20, 16, 20, 16)

        self.btn_preview = ModernButton("预览方案", "default")
        self.btn_preview.clicked.connect(self.preview_combinations)
        btn_layout.addWidget(self.btn_preview)

        self.btn_start = ModernButton("开始合成", "primary")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.setMinimumHeight(44)
        self.btn_start.setStyleSheet("""
            QPushButton#btn_primary {
                background-color: #3370ff;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: 600;
                padding: 12px 32px;
            }
            QPushButton#btn_primary:hover {
                background-color: #2860e1;
            }
            QPushButton#btn_primary:pressed {
                background-color: #1d4ed8;
            }
            QPushButton#btn_primary:disabled {
                background-color: #94bfff;
            }
        """)
        self.btn_start.clicked.connect(self.start_merge)
        btn_layout.addWidget(self.btn_start)

        self.btn_cancel = ModernButton("取消", "danger")
        self.btn_cancel.setObjectName("btn_danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_merge)
        btn_layout.addWidget(self.btn_cancel)

        right_layout.addWidget(btn_widget)

        # 进度区
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        progress_layout.setSpacing(8)
        progress_layout.setContentsMargins(0, 8, 0, 0)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #f0f1f2;
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #3370ff;
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("就绪")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #8f959e; font-size: 12px;")
        progress_layout.addWidget(self.progress_label)

        right_layout.addWidget(progress_widget)

        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setSizes([680, 480])
        main_layout.addWidget(splitter, 1)

        # ========== 底部日志区 ==========
        log_group = QGroupBox("运行日志")
        log_group.setStyleSheet("""
            QGroupBox {
                background-color: #ffffff;
                border: 1px solid #e5e6eb;
                border-radius: 12px;
                margin-top: 20px;
                padding-top: 20px;
            }
        """)
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(12, 12, 12, 12)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        main_layout.addWidget(log_group)

        # 初始化日志
        self.log("✨ 程序已启动，等待操作...")
        self.log("💡 提示：点击「添加文件」或「添加文件夹」导入视频")

    def _create_form_label(self, text):
        """创建表单标签"""
        label = QLabel(text)
        label.setStyleSheet("color: #1f2329; font-size: 13px; font-weight: 500;")
        return label

    def _create_separator(self):
        """创建分隔线"""
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #f0f1f2; max-height: 1px; margin: 4px 0;")
        return separator

    # ========== 以下为原有功能逻辑 ==========

    def add_video_files(self):
        """添加视频文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v);;所有文件 (*.*)"
        )

        if files:
            self.log(f"📂 正在加载 {len(files)} 个视频文件...")
            new_videos = batch_get_video_info(files)

            for video in new_videos:
                video.序号 = len(self.videos) + 1
                self.videos.append(video)

            self.update_video_table()
            self.update_start_video_combo()
            self.log(f"✅ 成功加载 {len(new_videos)} 个视频文件")

    def add_video_folder(self):
        """添加文件夹中的所有视频"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            video_extensions = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
            video_files = []

            for root, dirs, files in os.walk(folder):
                for file in files:
                    if os.path.splitext(file)[1].lower() in video_extensions:
                        video_files.append(os.path.join(root, file))

            if video_files:
                self.log(f"📂 在文件夹中找到 {len(video_files)} 个视频文件")
                new_videos = batch_get_video_info(video_files)

                for video in new_videos:
                    video.序号 = len(self.videos) + 1
                    self.videos.append(video)

                self.update_video_table()
                self.update_start_video_combo()
                self.log(f"✅ 成功加载 {len(new_videos)} 个视频文件")
            else:
                QMessageBox.information(self, "提示", "所选文件夹中没有找到视频文件")

    def load_from_json(self):
        """从JSON文件加载视频列表"""
        file, _ = QFileDialog.getOpenFileName(
            self, "选择JSON文件", "",
            "JSON文件 (*.json *.txt);;所有文件 (*.*)"
        )

        if file:
            from ..core.video_info import load_video_list_from_json
            videos = load_video_list_from_json(file)

            if videos:
                for video in videos:
                    video.序号 = len(self.videos) + 1
                    self.videos.append(video)

                self.update_video_table()
                self.update_start_video_combo()
                self.log(f"📥 从JSON加载 {len(videos)} 个视频")
            else:
                QMessageBox.warning(self, "警告", "无法从JSON文件加载视频列表")

    def save_to_json(self):
        """保存视频列表到JSON文件"""
        if not self.videos:
            QMessageBox.information(self, "提示", "视频列表为空")
            return

        file, _ = QFileDialog.getSaveFileName(
            self, "保存JSON文件", "",
            "JSON文件 (*.json);;所有文件 (*.*)"
        )

        if file:
            from ..core.video_info import save_video_list_to_json
            if save_video_list_to_json(self.videos, file):
                self.log(f"💾 视频列表已保存到: {file}")
            else:
                QMessageBox.warning(self, "警告", "保存失败")

    def remove_selected(self):
        """移除选中的视频"""
        selected_rows = set()
        for item in self.video_table.selectedItems():
            selected_rows.add(item.row())

        if selected_rows:
            for row in sorted(selected_rows, reverse=True):
                if row < len(self.videos):
                    del self.videos[row]

            # 重新编号
            for idx, video in enumerate(self.videos, 1):
                video.序号 = idx

            self.update_video_table()
            self.update_start_video_combo()
            self.log(f"🗑️ 已移除 {len(selected_rows)} 个视频")

    def clear_videos(self):
        """清空视频列表"""
        if self.videos:
            reply = QMessageBox.question(
                self, "确认操作",
                "确定要清空所有视频吗？此操作不可撤销。",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.videos.clear()
                self.start_video = None
                self.update_video_table()
                self.update_start_video_combo()
                self.log("🗑️ 已清空视频列表")

    def update_video_table(self):
        """更新视频表格"""
        self.video_table.setRowCount(len(self.videos))
        self.empty_hint.setVisible(len(self.videos) == 0)

        for row, video in enumerate(self.videos):
            # 选择复选框
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox.setCheckState(Qt.Checked if video.是否选择 else Qt.Unchecked)
            self.video_table.setItem(row, 0, checkbox)

            # 序号
            self.video_table.setItem(row, 1, QTableWidgetItem(str(video.序号)))

            # 文件名
            name_item = QTableWidgetItem(video.视频文件名称带扩展)
            if video.是否开头视频:
                name_item.setForeground(QColor("#3370ff"))
                font = QFont("Microsoft YaHei", 10, QFont.Bold)
                name_item.setFont(font)
            self.video_table.setItem(row, 2, name_item)

            # 时长
            self.video_table.setItem(row, 3, QTableWidgetItem(video.视频时长))

            # 分辨率
            self.video_table.setItem(row, 4, QTableWidgetItem(video.视频分辨率))

            # 大小
            self.video_table.setItem(row, 5, QTableWidgetItem(video.视频大小))

            # 操作按钮
            btn = QPushButton("设为开头")
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setProperty("row", row)
            btn.clicked.connect(lambda checked, r=row: self.set_start_from_table(r))
            if video.是否开头视频:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3370ff;
                        color: #ffffff;
                        border: none;
                        border-radius: 6px;
                        padding: 6px 14px;
                        font-weight: 600;
                        font-size: 12px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ffffff;
                        color: #3370ff;
                        border: 1px solid #3370ff;
                        border-radius: 6px;
                        padding: 6px 14px;
                        font-weight: 500;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #f2f3ff;
                    }
                """)
            self.video_table.setCellWidget(row, 6, btn)

        self.video_count_label.setText(f"{len(self.videos)} 个视频")
        self.update_estimate()

    def update_start_video_combo(self):
        """更新开头视频下拉框"""
        self.start_video_combo.clear()
        for video in self.videos:
            self.start_video_combo.addItem(video.视频文件名称带扩展, video)

    def show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)

        action_set_start = menu.addAction("设为开头视频")
        action_set_start.triggered.connect(self.set_selected_as_start)

        menu.addSeparator()

        action_remove = menu.addAction("移除选中")
        action_remove.triggered.connect(self.remove_selected)

        menu.exec_(self.video_table.viewport().mapToGlobal(pos))

    def set_selected_as_start(self):
        """将选中的视频设为开头"""
        current_row = self.video_table.currentRow()
        if 0 <= current_row < len(self.videos):
            self.set_start_from_table(current_row)

    def set_start_from_table(self, row):
        """从表格设置开头视频"""
        if 0 <= row < len(self.videos):
            # 清除之前的开头标记
            for video in self.videos:
                video.是否开头视频 = False

            # 设置新的开头
            self.videos[row].是否开头视频 = True
            self.start_video = self.videos[row]
            self.start_mode_combo.setCurrentIndex(1)  # 切换到"指定开头视频"模式

            # 更新下拉框
            self.start_video_combo.setCurrentIndex(row)

            self.update_video_table()
            self.log(f"⭐ 已设置开头视频: {self.videos[row].视频文件名称带扩展}")

    def set_start_video(self):
        """从下拉框设置开头视频"""
        index = self.start_video_combo.currentIndex()
        if 0 <= index < len(self.videos):
            # 清除之前的开头标记
            for video in self.videos:
                video.是否开头视频 = False

            # 设置新的开头
            self.videos[index].是否开头视频 = True
            self.start_video = self.videos[index]

            self.update_video_table()
            self.log(f"⭐ 已设置开头视频: {self.videos[index].视频文件名称带扩展}")

    def on_start_mode_changed(self, index):
        """开头模式改变"""
        self.start_video_widget.setVisible(index == 1)
        self.update_estimate()

    def on_count_mode_changed(self, index):
        """合成数量模式改变"""
        self.count_spin.setEnabled(index == 1)
        self.update_estimate()

    def on_preprocess_changed(self):
        """预处理设置改变"""
        self.resolution_widget.setVisible(self.enable_resolution_cb.isChecked())
        self.resolution_combo.setEnabled(self.enable_resolution_cb.isChecked())
        self.fps_widget.setVisible(self.enable_fps_cb.isChecked())
        self.fps_spin.setEnabled(self.enable_fps_cb.isChecked())

    def update_estimate(self):
        """更新预计合成数量"""
        if not self.videos:
            self.estimate_label.setText("预计合成: 0 个")
            return

        selected_videos = [v for v in self.videos if v.是否选择]
        group_size = self.group_size_spin.value()
        start_mode = self.start_mode_combo.currentIndex()

        has_start = start_mode == 1 and self.start_video is not None

        estimate = estimate_combination_count(
            len(selected_videos),
            group_size,
            has_start
        )

        if self.count_mode_combo.currentIndex() == 1:
            count = min(estimate, self.count_spin.value())
            self.estimate_label.setText(f"预计合成: {count} 个")
        else:
            self.estimate_label.setText(f"预计合成: {estimate} 个")

    def select_output_dir(self):
        """选择输出目录"""
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if folder:
            self.output_dir_edit.setText(folder)

    def preview_combinations(self):
        """预览合成方案"""
        if not self.videos:
            QMessageBox.information(self, "提示", "请先添加视频文件")
            return

        selected_videos = [v for v in self.videos if v.是否选择]
        if len(selected_videos) < 2:
            QMessageBox.information(self, "提示", "至少需要2个视频才能合成")
            return

        group_size = self.group_size_spin.value()
        start_mode = self.start_mode_combo.currentIndex()

        # 获取开头视频
        start_video = None
        if start_mode == 1:
            start_video = self.start_video

        # 生成组合
        if start_mode == 2:  # 随机
            combos = generate_random_combinations(selected_videos, group_size, 10, start_video)
        else:
            combos = generate_combinations(selected_videos, group_size, start_video, 10)

        # 显示预览
        preview_text = "📋 合成方案预览（前10个）:\n\n"
        for idx, combo in enumerate(combos, 1):
            names = [v.视频文件名称[:20] for v in combo]
            preview_text += f"{idx}. {' + '.join(names)}\n"

        QMessageBox.information(self, "合成方案预览", preview_text)

    def start_merge(self):
        """开始合成"""
        if not self.videos:
            QMessageBox.information(self, "提示", "请先添加视频文件")
            return

        selected_videos = [v for v in self.videos if v.是否选择]
        if len(selected_videos) < 2:
            QMessageBox.information(self, "提示", "至少需要2个视频才能合成")
            return

        output_dir = self.output_dir_edit.text()
        if not output_dir:
            QMessageBox.warning(self, "提示", "请选择输出目录")
            return

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 获取配置
        group_size = self.group_size_spin.value()
        start_mode = self.start_mode_combo.currentIndex()

        start_video = None
        if start_mode == 1:
            start_video = self.start_video

        # 生成组合
        if start_mode == 2:  # 随机
            count = self.count_spin.value() if self.count_mode_combo.currentIndex() == 1 else None
            combos = generate_random_combinations(
                selected_videos, group_size, count or 100, start_video
            )
        else:
            count = self.count_spin.value() if self.count_mode_combo.currentIndex() == 1 else None
            combos = generate_combinations(selected_videos, group_size, start_video, count)

        # 调试日志
        self.log(f"📋 合成模式: {['轮流开头', '指定开头', '随机开头'][start_mode]}")
        if start_video:
            self.log(f"⭐ 指定开头视频: {start_video.视频文件名称带扩展}")
        self.log(f"📦 每组片段数: {group_size}")
        self.log(f"🔢 生成组合数: {len(combos)}")

        # 验证组合是否正确
        if start_video and combos:
            for i, combo in enumerate(combos[:3]):
                if combo[0].视频路径 == start_video.视频路径:
                    self.log(f"  ✅ 组合{i+1}: 开头正确 - {combo[0].视频文件名称}")
                else:
                    self.log(f"  ❌ 组合{i+1}: 开头错误 - {combo[0].视频文件名称}")

        if not combos:
            QMessageBox.warning(self, "警告", "无法生成合成方案")
            return

        # 检查分辨率一致性
        if not self.enable_resolution_cb.isChecked():
            # 获取所有选中视频的分辨率
            resolutions = set(v.视频分辨率 for v in selected_videos)
            if len(resolutions) > 1:
                res_list = '\n'.join(f"  • {r}" for r in sorted(resolutions))
                reply = QMessageBox.warning(
                    self, "分辨率不一致",
                    f"检测到选中的视频包含不同的分辨率：\n\n{res_list}\n\n"
                    "合成时可能会出现画面变形或黑边。\n"
                    "建议：勾选「统一分辨率」选项后再合成。\n\n"
                    "是否继续合成？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

        # 确认
        reply = QMessageBox.question(
            self, "确认合成",
            f"即将合成 {len(combos)} 个视频，是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # 硬件加速模式
        hw_accel_map = {0: "auto", 1: "nvenc", 2: "cpu"}
        hw_accel = hw_accel_map.get(self.hw_accel_combo.currentIndex(), "auto")

        # 转场效果
        transition_map = {
            0: "none", 1: "fade", 2: "dissolve", 3: "wipe_left", 4: "wipe_right",
            5: "slide_left", 6: "slide_right", 7: "smooth_left", 8: "smooth_right",
            9: "circle_open", 10: "circle_close", 11: "pixelize", 12: "radial",
            13: "diag_bl", 14: "diag_br"
        }
        transition = transition_map.get(self.transition_combo.currentIndex(), "none")
        transition_duration = self.transition_duration_spin.value()

        # 创建合并配置
        config = MergeConfig(
            output_dir=output_dir,
            file_prefix=self.prefix_edit.text() or "合成视频",
            resolution=self.resolution_combo.currentText().split(" ")[0] if self.enable_resolution_cb.isChecked() else None,
            fps=self.fps_spin.value() if self.enable_fps_cb.isChecked() else None,
            codec="h265" if self.codec_combo.currentIndex() == 1 else "h264",
            quality=["high", "medium", "low"][self.quality_combo.currentIndex()],
            hardware_accel=hw_accel,
            transition=transition,
            transition_duration=transition_duration
        )

        # 显示配置信息
        if transition != "none":
            self.log(f"🎬 转场效果: {transition}, 时长: {transition_duration}秒")

        # 禁用按钮
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_preview.setEnabled(False)

        # 启动合并线程
        self.merge_thread = MergeThread(combos, config)
        self.merge_thread.progress_updated.connect(self.on_merge_progress)
        self.merge_thread.finished_signal.connect(self.on_merge_finished)
        self.merge_thread.start()

        self.log(f"🚀 开始合成 {len(combos)} 个视频...")

    def cancel_merge(self):
        """取消合成"""
        if self.merge_thread:
            self.merge_thread.cancel()
            self.log("⏹️ 正在取消合成...")

    def on_merge_progress(self, current, total, progress, status):
        """合成进度更新"""
        overall_progress = int(((current - 1) / total + progress / total) * 100)
        self.progress_bar.setValue(overall_progress)
        self.progress_label.setText(f"正在处理 {current}/{total}")

    def on_merge_finished(self, success, fail, files, reasons):
        """合成完成"""
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_preview.setEnabled(True)
        self.progress_bar.setValue(100)

        self.log("")
        self.log("=" * 50)
        self.log(f"✅ 合成完成！成功: {success}, 失败: {fail}")
        self.log("=" * 50)

        if files:
            self.log(f"📁 输出目录: {os.path.dirname(files[0])}")
            self.log(f"📄 成功文件:")
            for f in files:
                self.log(f"  ✓ {os.path.basename(f)}")

        if reasons:
            self.log(f"❌ 失败原因:")
            for r in reasons:
                self.log(f"  ✗ {r}")

        self.progress_label.setText(f"完成 · 成功 {success} · 失败 {fail}")

        QMessageBox.information(
            self, "合成完成",
            f"视频合成完成！\n\n成功: {success}\n失败: {fail}"
        )

    def log(self, message):
        """添加日志"""
        self.log_text.append(message)
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
