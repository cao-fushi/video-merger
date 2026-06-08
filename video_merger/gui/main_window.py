"""主窗口模块 - 视频批量合成工具GUI"""
import sys
import os
from typing import List, Optional
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QLabel, QSpinBox, QComboBox, QLineEdit, QCheckBox, QGroupBox,
    QProgressBar, QTextEdit, QMessageBox, QSplitter, QFrame,
    QAbstractItemView, QMenu, QAction, QDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont, QColor

from ..core.video_info import VideoInfo, get_video_info, batch_get_video_info
from ..core.combination import (
    generate_combinations, generate_random_combinations,
    generate_sequential_combinations, estimate_combination_count
)
from ..core.video_merger import MergeConfig, batch_merge_videos
from ..core.ffmpeg_utils import check_ffmpeg_installed


class MergeThread(QThread):
    """合并线程"""
    progress_updated = pyqtSignal(int, int, float, str)  # 当前索引, 总数, 进度, 状态
    finished_signal = pyqtSignal(int, int, list)  # 成功数, 失败数, 输出文件列表

    def __init__(self, combinations, config):
        super().__init__()
        self.combinations = combinations
        self.config = config
        self._is_cancelled = False

    def run(self):
        def progress_callback(current, total, progress, status):
            if not self._is_cancelled:
                self.progress_updated.emit(current, total, progress, status)

        success, fail, files = batch_merge_videos(
            self.combinations,
            self.config,
            progress_callback
        )

        if not self._is_cancelled:
            self.finished_signal.emit(success, fail, files)

    def cancel(self):
        self._is_cancelled = True


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
                self, "警告",
                "未检测到FFmpeg，请先安装FFmpeg并添加到系统PATH环境变量。\n"
                "下载地址: https://ffmpeg.org/download.html"
            )

    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("视频批量合成工具")
        self.setMinimumSize(1000, 700)

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 工具栏
        toolbar_layout = QHBoxLayout()

        btn_add_files = QPushButton("添加视频文件")
        btn_add_files.clicked.connect(self.add_video_files)
        toolbar_layout.addWidget(btn_add_files)

        btn_add_folder = QPushButton("添加文件夹")
        btn_add_folder.clicked.connect(self.add_video_folder)
        toolbar_layout.addWidget(btn_add_folder)

        btn_load_json = QPushButton("从JSON加载")
        btn_load_json.clicked.connect(self.load_from_json)
        toolbar_layout.addWidget(btn_load_json)

        btn_save_json = QPushButton("保存为JSON")
        btn_save_json.clicked.connect(self.save_to_json)
        toolbar_layout.addWidget(btn_save_json)

        toolbar_layout.addStretch()

        btn_remove_selected = QPushButton("移除选中")
        btn_remove_selected.clicked.connect(self.remove_selected)
        toolbar_layout.addWidget(btn_remove_selected)

        btn_clear = QPushButton("清空列表")
        btn_clear.clicked.connect(self.clear_videos)
        toolbar_layout.addWidget(btn_clear)

        main_layout.addLayout(toolbar_layout)

        # 使用分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：视频列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 视频统计
        self.video_count_label = QLabel("视频数量: 0")
        left_layout.addWidget(self.video_count_label)

        # 视频表格
        self.video_table = QTableWidget()
        self.video_table.setColumnCount(7)
        self.video_table.setHorizontalHeaderLabels([
            "✓", "序号", "文件名", "时长", "分辨率", "大小", "开头视频"
        ])
        self.video_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.video_table.setColumnWidth(0, 30)
        self.video_table.setColumnWidth(1, 50)
        self.video_table.setColumnWidth(3, 80)
        self.video_table.setColumnWidth(4, 100)
        self.video_table.setColumnWidth(5, 80)
        self.video_table.setColumnWidth(6, 100)
        self.video_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.video_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.video_table.customContextMenuRequested.connect(self.show_context_menu)

        left_layout.addWidget(self.video_table)

        splitter.addWidget(left_widget)

        # 右侧：设置面板
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 合成配置组
        config_group = QGroupBox("合成配置")
        config_layout = QVBoxLayout(config_group)

        # 开头视频设置
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("开头视频:"))

        self.start_mode_combo = QComboBox()
        self.start_mode_combo.addItems(["不指定（按顺序轮流）", "指定开头视频", "随机选择开头"])
        self.start_mode_combo.currentIndexChanged.connect(self.on_start_mode_changed)
        start_layout.addWidget(self.start_mode_combo)

        config_layout.addLayout(start_layout)

        # 指定开头视频选择
        self.start_video_layout = QHBoxLayout()
        self.start_video_layout.addWidget(QLabel("选择开头:"))

        self.start_video_combo = QComboBox()
        self.start_video_combo.setMinimumWidth(200)
        self.start_video_layout.addWidget(self.start_video_combo)

        self.btn_set_start = QPushButton("设为开头")
        self.btn_set_start.clicked.connect(self.set_start_video)
        self.start_video_layout.addWidget(self.btn_set_start)

        config_layout.addLayout(self.start_video_layout)

        # 每组片段数
        group_layout = QHBoxLayout()
        group_layout.addWidget(QLabel("每组片段数:"))

        self.group_size_spin = QSpinBox()
        self.group_size_spin.setRange(2, 20)
        self.group_size_spin.setValue(2)
        self.group_size_spin.valueChanged.connect(self.update_estimate)
        group_layout.addWidget(self.group_size_spin)

        group_layout.addStretch()
        config_layout.addLayout(group_layout)

        # 合成数量
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("合成数量:"))

        self.count_mode_combo = QComboBox()
        self.count_mode_combo.addItems(["全部组合", "自定义数量"])
        self.count_mode_combo.currentIndexChanged.connect(self.on_count_mode_changed)
        count_layout.addWidget(self.count_mode_combo)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 10000)
        self.count_spin.setValue(100)
        self.count_spin.setEnabled(False)
        count_layout.addWidget(self.count_spin)

        config_layout.addLayout(count_layout)

        # 预计合成数
        self.estimate_label = QLabel("预计合成数量: 0")
        config_layout.addWidget(self.estimate_label)

        # 文件命名
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("文件前缀:"))

        self.prefix_edit = QLineEdit("合成视频")
        name_layout.addWidget(self.prefix_edit)

        config_layout.addLayout(name_layout)

        # 输出目录
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("输出目录:"))

        self.output_dir_edit = QLineEdit()
        output_layout.addWidget(self.output_dir_edit)

        btn_select_dir = QPushButton("选择")
        btn_select_dir.clicked.connect(self.select_output_dir)
        output_layout.addWidget(btn_select_dir)

        config_layout.addLayout(output_layout)

        right_layout.addWidget(config_group)

        # 预处理设置组
        preprocess_group = QGroupBox("预处理设置（可选）")
        preprocess_layout = QVBoxLayout(preprocess_group)

        # 统一分辨率
        self.enable_resolution_cb = QCheckBox("统一分辨率")
        self.enable_resolution_cb.stateChanged.connect(self.on_preprocess_changed)
        preprocess_layout.addWidget(self.enable_resolution_cb)

        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("  分辨率:"))

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "1080x1920", "1920x1080", "720x1280", "1280x720",
            "640x1136", "1136x640", "640x480", "480x640"
        ])
        self.resolution_combo.setEnabled(False)
        resolution_layout.addWidget(self.resolution_combo)

        resolution_layout.addStretch()
        preprocess_layout.addLayout(resolution_layout)

        # 统一帧率
        self.enable_fps_cb = QCheckBox("统一帧率")
        self.enable_fps_cb.stateChanged.connect(self.on_preprocess_changed)
        preprocess_layout.addWidget(self.enable_fps_cb)

        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("  帧率:"))

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(10, 120)
        self.fps_spin.setValue(30)
        self.fps_spin.setEnabled(False)
        fps_layout.addWidget(self.fps_spin)
        fps_layout.addWidget(QLabel("fps"))

        fps_layout.addStretch()
        preprocess_layout.addLayout(fps_layout)

        # 编码设置
        codec_layout = QHBoxLayout()
        codec_layout.addWidget(QLabel("编码器:"))

        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["H.264", "H.265"])
        codec_layout.addWidget(self.codec_combo)

        codec_layout.addWidget(QLabel("质量:"))

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高", "中", "低"])
        self.quality_combo.setCurrentIndex(0)
        codec_layout.addWidget(self.quality_combo)

        codec_layout.addStretch()
        preprocess_layout.addLayout(codec_layout)

        right_layout.addWidget(preprocess_group)

        # 操作按钮
        btn_layout = QHBoxLayout()

        self.btn_preview = QPushButton("预览合成方案")
        self.btn_preview.clicked.connect(self.preview_combinations)
        btn_layout.addWidget(self.btn_preview)

        self.btn_start = QPushButton("开始合成")
        self.btn_start.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.btn_start.clicked.connect(self.start_merge)
        btn_layout.addWidget(self.btn_start)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_merge)
        btn_layout.addWidget(self.btn_cancel)

        right_layout.addLayout(btn_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        right_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("就绪")
        right_layout.addWidget(self.progress_label)

        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setSizes([600, 400])
        main_layout.addWidget(splitter)

        # 日志区域
        log_group = QGroupBox("日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        main_layout.addWidget(log_group)

    def add_video_files(self):
        """添加视频文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm *.m4v);;所有文件 (*.*)"
        )

        if files:
            self.log(f"正在加载 {len(files)} 个视频文件...")
            new_videos = batch_get_video_info(files)

            for video in new_videos:
                video.序号 = len(self.videos) + 1
                self.videos.append(video)

            self.update_video_table()
            self.update_start_video_combo()
            self.log(f"成功加载 {len(new_videos)} 个视频文件")

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
                self.log(f"在文件夹中找到 {len(video_files)} 个视频文件")
                new_videos = batch_get_video_info(video_files)

                for video in new_videos:
                    video.序号 = len(self.videos) + 1
                    self.videos.append(video)

                self.update_video_table()
                self.update_start_video_combo()
                self.log(f"成功加载 {len(new_videos)} 个视频文件")
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
                self.log(f"从JSON加载 {len(videos)} 个视频")
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
                self.log(f"视频列表已保存到: {file}")
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
            self.log(f"已移除 {len(selected_rows)} 个视频")

    def clear_videos(self):
        """清空视频列表"""
        if self.videos:
            reply = QMessageBox.question(
                self, "确认", "确定要清空视频列表吗？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.videos.clear()
                self.start_video = None
                self.update_video_table()
                self.update_start_video_combo()
                self.log("已清空视频列表")

    def update_video_table(self):
        """更新视频表格"""
        self.video_table.setRowCount(len(self.videos))

        for row, video in enumerate(self.videos):
            # 选择复选框
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox.setCheckState(Qt.Checked if video.是否选择 else Qt.Unchecked)
            self.video_table.setItem(row, 0, checkbox)

            # 序号
            self.video_table.setItem(row, 1, QTableWidgetItem(str(video.序号)))

            # 文件名
            self.video_table.setItem(row, 2, QTableWidgetItem(video.视频文件名称带扩展))

            # 时长
            self.video_table.setItem(row, 3, QTableWidgetItem(video.视频时长))

            # 分辨率
            self.video_table.setItem(row, 4, QTableWidgetItem(video.视频分辨率))

            # 大小
            self.video_table.setItem(row, 5, QTableWidgetItem(video.视频大小))

            # 开头视频按钮
            btn = QPushButton("设为开头")
            btn.setProperty("row", row)
            btn.clicked.connect(lambda checked, r=row: self.set_start_from_table(r))
            self.video_table.setCellWidget(row, 6, btn)

        self.video_count_label.setText(f"视频数量: {len(self.videos)}")
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
            self.log(f"已设置开头视频: {self.videos[row].视频文件名称带扩展}")

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
            self.log(f"已设置开头视频: {self.videos[index].视频文件名称带扩展}")

    def on_start_mode_changed(self, index):
        """开头模式改变"""
        self.start_video_combo.setEnabled(index == 1)
        self.btn_set_start.setEnabled(index == 1)
        self.update_estimate()

    def on_count_mode_changed(self, index):
        """合成数量模式改变"""
        self.count_spin.setEnabled(index == 1)
        self.update_estimate()

    def on_preprocess_changed(self):
        """预处理设置改变"""
        self.resolution_combo.setEnabled(self.enable_resolution_cb.isChecked())
        self.fps_spin.setEnabled(self.enable_fps_cb.isChecked())

    def update_estimate(self):
        """更新预计合成数量"""
        if not self.videos:
            self.estimate_label.setText("预计合成数量: 0")
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
            self.estimate_label.setText(f"预计合成数量: {count}")
        else:
            self.estimate_label.setText(f"预计合成数量: {estimate}")

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
        preview_text = "合成方案预览（前10个）:\n\n"
        for idx, combo in enumerate(combos, 1):
            names = [v.视频文件名称 for v in combo]
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
            QMessageBox.warning(self, "警告", "请选择输出目录")
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

        if not combos:
            QMessageBox.warning(self, "警告", "无法生成合成方案")
            return

        # 确认
        reply = QMessageBox.question(
            self, "确认",
            f"即将合成 {len(combos)} 个视频，是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # 创建合并配置
        config = MergeConfig(
            output_dir=output_dir,
            file_prefix=self.prefix_edit.text() or "合成视频",
            resolution=self.resolution_combo.currentText() if self.enable_resolution_cb.isChecked() else None,
            fps=self.fps_spin.value() if self.enable_fps_cb.isChecked() else None,
            codec="h265" if self.codec_combo.currentIndex() == 1 else "h264",
            quality=["high", "medium", "low"][self.quality_combo.currentIndex()]
        )

        # 禁用按钮
        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_preview.setEnabled(False)

        # 启动合并线程
        self.merge_thread = MergeThread(combos, config)
        self.merge_thread.progress_updated.connect(self.on_merge_progress)
        self.merge_thread.finished_signal.connect(self.on_merge_finished)
        self.merge_thread.start()

        self.log(f"开始合成 {len(combos)} 个视频...")

    def cancel_merge(self):
        """取消合成"""
        if self.merge_thread:
            self.merge_thread.cancel()
            self.log("正在取消合成...")

    def on_merge_progress(self, current, total, progress, status):
        """合成进度更新"""
        overall_progress = int(((current - 1) / total + progress / total) * 100)
        self.progress_bar.setValue(overall_progress)
        self.progress_label.setText(f"正在处理第 {current}/{total} 个: {status}")

    def on_merge_finished(self, success, fail, files):
        """合成完成"""
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_preview.setEnabled(True)
        self.progress_bar.setValue(100)

        self.log(f"合成完成！成功: {success}, 失败: {fail}")

        if files:
            self.log(f"输出目录: {os.path.dirname(files[0])}")

        QMessageBox.information(
            self, "完成",
            f"视频合成完成！\n成功: {success}\n失败: {fail}"
        )

    def log(self, message):
        """添加日志"""
        self.log_text.append(message)
        # 滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
