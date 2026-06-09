"""系统环境检查模块 - 首次运行时检查系统是否满足使用条件"""
import os
import sys
import subprocess
import shutil
import tempfile
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class SystemChecker:
    """系统环境检查器"""

    def __init__(self):
        self.results = []
        self.all_passed = True
        self.critical_passed = True  # 关键检查是否通过

    def check_all(self) -> Tuple[bool, List[Dict]]:
        """
        执行所有检查

        Returns:
            (是否全部通过, 检查结果列表)
        """
        self.results = []
        self.all_passed = True
        self.critical_passed = True

        # 1. 检查FFmpeg（关键）
        self._check_ffmpeg()

        # 2. 检查FFprobe（关键）
        self._check_ffprobe()

        # 3. 实际测试视频合成功能（关键）
        self._test_video_merge()

        # 4. 实际测试导出像素格式（关键）
        self._test_pixel_format()

        # 5. 检测可用的硬件编码器（非关键）
        self._check_hardware_encoders()

        # 6. 检查磁盘空间
        self._check_disk_space()

        # 7. 检查写入权限
        self._check_write_permission()

        return self.all_passed, self.results

    def _add_result(self, name: str, passed: bool, message: str, suggestion: str = "", critical: bool = False):
        """添加检查结果"""
        self.results.append({
            "name": name,
            "passed": passed,
            "message": message,
            "suggestion": suggestion,
            "critical": critical
        })
        if not passed:
            self.all_passed = False
            if critical:
                self.critical_passed = False

    def _get_base_dir(self) -> str:
        """获取程序基础目录"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def _get_ffmpeg_path(self) -> str:
        """获取FFmpeg路径"""
        base_dir = self._get_base_dir()

        # 搜索路径列表
        search_paths = [
            os.path.join(base_dir, '_internal', 'imageio_ffmpeg', 'binaries', 'ffmpeg-win-x86_64-v7.1.exe'),
            os.path.join(base_dir, '_internal', 'ffmpeg.exe'),
            os.path.join(base_dir, 'ffmpeg.exe'),
            # imageio_ffmpeg包中的FFmpeg
            'D:/123/ai/Python310/lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe',
            # TRAE的ffmpeg（精简版，最后选择）
            'D:/123/ai/TRAE SOLO CN/resources/app/bin/ffmpeg.exe',
        ]

        for path in search_paths:
            if path and os.path.exists(path):
                return path

        # 从PATH查找
        path = shutil.which('ffmpeg')
        if path:
            return path

        return None

    def _get_ffprobe_path(self) -> str:
        """获取FFprobe路径"""
        base_dir = self._get_base_dir()

        # 搜索路径列表
        search_paths = [
            os.path.join(base_dir, '_internal', 'ffprobe.exe'),
            os.path.join(base_dir, 'ffprobe.exe'),
            # TRAE的ffprobe
            'D:/123/ai/TRAE SOLO CN/resources/app/bin/ffprobe.exe',
        ]

        for path in search_paths:
            if path and os.path.exists(path):
                return path

        # 从PATH查找
        path = shutil.which('ffprobe')
        if path:
            return path

        return None

    def _run_cmd(self, cmd: list, timeout: int = 30) -> Tuple[bool, str, str]:
        """运行命令"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                creationflags=0x08000000 if os.name == 'nt' else 0
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)

    def _check_ffmpeg(self):
        """检查FFmpeg是否可用"""
        ffmpeg_path = self._get_ffmpeg_path()

        if not ffmpeg_path or not os.path.exists(ffmpeg_path):
            self._add_result("FFmpeg", False, "未找到FFmpeg", "请重新安装本程序", critical=True)
            return

        # 测试FFmpeg版本
        success, stdout, stderr = self._run_cmd([ffmpeg_path, '-version'])
        if success:
            version = stdout.split('\n')[0].strip()[:80]
            self._add_result("FFmpeg", True, f"已安装: {version}", critical=True)
        else:
            self._add_result("FFmpeg", False, "FFmpeg无法运行", "请重新安装本程序", critical=True)

    def _check_ffprobe(self):
        """检查FFprobe是否可用"""
        ffprobe_path = self._get_ffprobe_path()

        if not ffprobe_path or not os.path.exists(ffprobe_path):
            self._add_result("FFprobe", False, "未找到FFprobe", "请重新安装本程序", critical=True)
            return

        # 测试FFprobe版本
        success, stdout, stderr = self._run_cmd([ffprobe_path, '-version'])
        if success:
            version = stdout.split('\n')[0].strip()[:80]
            self._add_result("FFprobe", True, f"已安装: {version}", critical=True)
        else:
            self._add_result("FFprobe", False, "FFprobe无法运行", "请重新安装本程序", critical=True)

    def _test_video_merge(self):
        """实际测试视频合成功能"""
        ffmpeg_path = self._get_ffmpeg_path()
        ffprobe_path = self._get_ffprobe_path()

        if not ffmpeg_path or not ffprobe_path:
            self._add_result("视频合成", False, "FFmpeg或FFprobe不可用", "请重新安装本程序", critical=True)
            return

        test_dir = tempfile.mkdtemp()
        test_video1 = os.path.join(test_dir, 'test1.mp4')
        test_video2 = os.path.join(test_dir, 'test2.mp4')
        output_video = os.path.join(test_dir, 'output.mp4')

        try:
            # 创建测试视频
            self._run_cmd([
                ffmpeg_path, '-y', '-f', 'lavfi', '-i', 'color=c=red:s=320x240:d=1:r=25',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', test_video1
            ])
            self._run_cmd([
                ffmpeg_path, '-y', '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=1:r=25',
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', test_video2
            ])

            if not os.path.exists(test_video1) or not os.path.exists(test_video2):
                self._add_result("视频合成", False, "无法创建测试视频", "请重新安装本程序", critical=True)
                return

            # 测试concat合并
            filelist = os.path.join(test_dir, 'list.txt')
            with open(filelist, 'w') as f:
                f.write(f"file '{test_video1}'\n")
                f.write(f"file '{test_video2}'\n")

            success, stdout, stderr = self._run_cmd([
                ffmpeg_path, '-y', '-f', 'concat', '-safe', '0', '-i', filelist,
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', output_video
            ])

            if success and os.path.exists(output_video):
                self._add_result("视频合成", True, "concat合并测试通过", critical=True)
            else:
                self._add_result("视频合成", False, "concat合并测试失败", "请重新安装本程序", critical=True)

        except Exception as e:
            self._add_result("视频合成", False, f"测试异常: {e}", "请重新安装本程序", critical=True)
        finally:
            # 清理
            try:
                shutil.rmtree(test_dir, ignore_errors=True)
            except:
                pass

    def _test_pixel_format(self):
        """测试导出视频的像素格式是否为yuv420p"""
        ffmpeg_path = self._get_ffmpeg_path()
        ffprobe_path = self._get_ffprobe_path()

        if not ffmpeg_path or not ffprobe_path:
            self._add_result("像素格式", False, "FFmpeg或FFprobe不可用", "请重新安装本程序", critical=True)
            return

        test_dir = tempfile.mkdtemp()
        test_video_yuv444p = os.path.join(test_dir, 'test_yuv444p.mp4')
        output_video = os.path.join(test_dir, 'output.mp4')

        try:
            # 创建yuv444p格式的测试视频（模拟不兼容的源视频）
            self._run_cmd([
                ffmpeg_path, '-y', '-f', 'lavfi', '-i', 'color=c=red:s=320x240:d=1:r=25',
                '-c:v', 'libx264', '-pix_fmt', 'yuv444p', test_video_yuv444p
            ])

            if not os.path.exists(test_video_yuv444p):
                self._add_result("像素格式", False, "无法创建测试视频", "请重新安装本程序", critical=True)
                return

            # 使用yuv420p导出
            success, stdout, stderr = self._run_cmd([
                ffmpeg_path, '-y', '-i', test_video_yuv444p,
                '-c:v', 'libx264', '-crf', '23', '-pix_fmt', 'yuv420p',
                output_video
            ])

            if not success or not os.path.exists(output_video):
                self._add_result("像素格式", False, "视频导出测试失败", "请重新安装本程序", critical=True)
                return

            # 检查输出视频的像素格式
            success, stdout, stderr = self._run_cmd([
                ffprobe_path, '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=pix_fmt', '-of', 'default=noprint_wrappers=1:nokey=1',
                output_video
            ])

            if success:
                pix_fmt = stdout.strip()
                if pix_fmt == 'yuv420p':
                    self._add_result("像素格式", True, "yuv420p格式测试通过", critical=True)
                else:
                    self._add_result("像素格式", False, f"输出格式为{pix_fmt}，应为yuv420p", "请重新安装本程序", critical=True)
            else:
                self._add_result("像素格式", False, "无法检测像素格式", "请重新安装本程序", critical=True)

        except Exception as e:
            self._add_result("像素格式", False, f"测试异常: {e}", "请重新安装本程序", critical=True)
        finally:
            # 清理
            try:
                shutil.rmtree(test_dir, ignore_errors=True)
            except:
                pass

    def _check_hardware_encoders(self):
        """检测可用的硬件编码器"""
        ffmpeg_path = self._get_ffmpeg_path()
        if not ffmpeg_path:
            return

        # 检测NVIDIA NVENC
        nvenc_ok = self._test_encoder(ffmpeg_path, 'h264_nvenc')
        if nvenc_ok:
            self._add_result("NVIDIA NVENC", True, "支持NVIDIA硬件加速编码")
        else:
            self._add_result("NVIDIA NVENC", False, "不支持（需要NVIDIA显卡）")

        # 检测AMD AMF
        amf_ok = self._test_encoder(ffmpeg_path, 'h264_amf')
        if amf_ok:
            self._add_result("AMD AMF", True, "支持AMD硬件加速编码")
        else:
            self._add_result("AMD AMF", False, "不支持（需要AMD显卡）")

        # 检测Intel QSV
        qsv_ok = self._test_encoder(ffmpeg_path, 'h264_qsv')
        if qsv_ok:
            self._add_result("Intel QSV", True, "支持Intel核显加速编码")
        else:
            self._add_result("Intel QSV", False, "不支持（需要Intel核显）")

    def _test_encoder(self, ffmpeg_path: str, encoder_name: str) -> bool:
        """测试指定编码器是否可用"""
        test_dir = tempfile.mkdtemp()
        test_output = os.path.join(test_dir, f'{encoder_name}_test.mp4')

        try:
            success, stdout, stderr = self._run_cmd([
                ffmpeg_path, '-y', '-f', 'lavfi', '-i', 'color=c=red:s=64x64:d=0.1',
                '-c:v', encoder_name, '-preset', 'fast', test_output
            ], timeout=10)

            return success and os.path.exists(test_output)
        except:
            return False
        finally:
            try:
                if os.path.exists(test_output):
                    os.unlink(test_output)
                os.rmdir(test_dir)
            except:
                pass

    def _check_disk_space(self, min_mb: int = 500):
        """检查磁盘空间"""
        try:
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
            else:
                exe_dir = os.getcwd()

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
