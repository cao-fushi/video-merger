"""系统环境检查模块 - 首次运行时检查系统是否满足使用条件"""
import os
import sys
import subprocess
import shutil
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class SystemChecker:
    """系统环境检查器"""

    def __init__(self):
        self.results = []
        self.all_passed = True

    def check_all(self) -> Tuple[bool, List[Dict]]:
        """
        执行所有检查

        Returns:
            (是否全部通过, 检查结果列表)
        """
        self.results = []
        self.all_passed = True

        # 检查FFmpeg
        self._check_ffmpeg()

        # 检查FFprobe
        self._check_ffprobe()

        # 检查NVIDIA显卡
        self._check_nvidia_gpu()

        # 检查NVENC支持
        self._check_nvenc_support()

        # 检查磁盘空间
        self._check_disk_space()

        # 检查写入权限
        self._check_write_permission()

        return self.all_passed, self.results

    def _add_result(self, name: str, passed: bool, message: str, suggestion: str = ""):
        """添加检查结果"""
        self.results.append({
            "name": name,
            "passed": passed,
            "message": message,
            "suggestion": suggestion
        })
        if not passed:
            self.all_passed = False

    def _get_ffmpeg_path(self) -> str:
        """获取FFmpeg路径"""
        # 从打包环境查找
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            internal_dir = os.path.join(exe_dir, '_internal')

            # 检查imageio_ffmpeg目录
            ffmpeg_path = os.path.join(internal_dir, 'imageio_ffmpeg', 'binaries', 'ffmpeg-win-x86_64-v7.1.exe')
            if os.path.exists(ffmpeg_path):
                return ffmpeg_path

        # 从PATH查找
        path = shutil.which('ffmpeg')
        if path:
            return path

        return None

    def _get_ffprobe_path(self) -> str:
        """获取FFprobe路径"""
        # 从打包环境查找
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            internal_dir = os.path.join(exe_dir, '_internal')

            ffprobe_path = os.path.join(internal_dir, 'ffprobe.exe')
            if os.path.exists(ffprobe_path):
                return ffprobe_path

        # 从PATH查找
        path = shutil.which('ffprobe')
        if path:
            return path

        return None

    def _check_ffmpeg(self):
        """检查FFmpeg"""
        ffmpeg_path = self._get_ffmpeg_path()

        if ffmpeg_path and os.path.exists(ffmpeg_path):
            try:
                result = subprocess.run(
                    [ffmpeg_path, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=0x08000000 if os.name == 'nt' else 0
                )
                if result.returncode == 0:
                    version = result.stdout.split('\n')[0].strip()
                    self._add_result("FFmpeg", True, f"已安装: {version}")
                else:
                    self._add_result("FFmpeg", False, "FFmpeg无法运行", "请重新安装FFmpeg")
            except Exception as e:
                self._add_result("FFmpeg", False, f"FFmpeg执行失败: {e}", "请重新安装FFmpeg")
        else:
            self._add_result("FFmpeg", False, "未找到FFmpeg", "请安装FFmpeg或重新安装本程序")

    def _check_ffprobe(self):
        """检查FFprobe"""
        ffprobe_path = self._get_ffprobe_path()

        if ffprobe_path and os.path.exists(ffprobe_path):
            try:
                result = subprocess.run(
                    [ffprobe_path, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=0x08000000 if os.name == 'nt' else 0
                )
                if result.returncode == 0:
                    version = result.stdout.split('\n')[0].strip()
                    self._add_result("FFprobe", True, f"已安装: {version}")
                else:
                    self._add_result("FFprobe", False, "FFprobe无法运行", "请重新安装FFmpeg")
            except Exception as e:
                self._add_result("FFprobe", False, f"FFprobe执行失败: {e}", "请重新安装FFmpeg")
        else:
            self._add_result("FFprobe", False, "未找到FFprobe", "请安装FFmpeg或重新安装本程序")

    def _check_nvidia_gpu(self):
        """检查NVIDIA显卡"""
        try:
            # 使用wmic检查显卡
            result = subprocess.run(
                ['wmic', 'path', 'win32_videocontroller', 'get', 'name'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if 'NVIDIA' in output:
                    # 提取显卡名称
                    for line in output.split('\n'):
                        if 'NVIDIA' in line:
                            gpu_name = line.strip()
                            self._add_result("NVIDIA显卡", True, f"检测到: {gpu_name}")
                            return
                else:
                    self._add_result("NVIDIA显卡", False, "未检测到NVIDIA显卡", "将使用CPU编码（速度较慢）")
            else:
                self._add_result("NVIDIA显卡", False, "无法检测显卡信息", "将使用CPU编码")

        except Exception as e:
            self._add_result("NVIDIA显卡", False, f"显卡检测失败: {e}", "将使用CPU编码")

    def _check_nvenc_support(self):
        """检查NVENC支持"""
        ffmpeg_path = self._get_ffmpeg_path()
        if not ffmpeg_path:
            self._add_result("NVENC编码", False, "FFmpeg未找到", "无法使用硬件加速")
            return

        try:
            result = subprocess.run(
                [ffmpeg_path, '-encoders'],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )

            if result.returncode == 0:
                if 'h264_nvenc' in result.stdout:
                    self._add_result("NVENC编码", True, "支持NVIDIA硬件加速编码")
                else:
                    self._add_result("NVENC编码", False, "FFmpeg不支持NVENC", "将使用CPU编码")
            else:
                self._add_result("NVENC编码", False, "无法检测编码器", "将使用CPU编码")

        except Exception as e:
            self._add_result("NVENC编码", False, f"检测失败: {e}", "将使用CPU编码")

    def _check_disk_space(self, min_mb: int = 500):
        """检查磁盘空间"""
        try:
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
            else:
                exe_dir = os.getcwd()

            # 获取磁盘空间
            usage = shutil.disk_usage(exe_dir)
            free_mb = usage.free // (1024 * 1024)

            if free_mb >= min_mb:
                self._add_result("磁盘空间", True, f"可用空间: {free_mb}MB")
            else:
                self._add_result("磁盘空间", False, f"可用空间不足: {free_mb}MB", f"建议至少{min_mb}MB可用空间")

        except Exception as e:
            self._add_result("磁盘空间", False, f"检测失败: {e}", "请确保有足够的磁盘空间")

    def _check_write_permission(self):
        """检查写入权限"""
        try:
            # 尝试在exe目录创建临时文件
            if getattr(sys, 'frozen', False):
                test_dir = os.path.dirname(sys.executable)
            else:
                test_dir = os.getcwd()

            test_file = os.path.join(test_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)

            self._add_result("写入权限", True, "有写入权限")

        except Exception as e:
            self._add_result("写入权限", False, f"没有写入权限: {e}", "请以管理员身份运行或选择其他目录")


def run_system_check() -> Tuple[bool, List[Dict]]:
    """
    运行系统检查

    Returns:
        (是否全部通过, 检查结果列表)
    """
    checker = SystemChecker()
    return checker.check_all()
