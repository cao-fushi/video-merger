"""FFmpeg工具函数模块"""
import subprocess
import shutil
import os
from typing import Optional, Tuple

# Windows下隐藏命令行窗口的标志
CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0


def _run_subprocess(cmd, **kwargs):
    """运行subprocess命令，自动添加CREATE_NO_WINDOW标志"""
    if os.name == 'nt':
        kwargs.setdefault('creationflags', CREATE_NO_WINDOW)
    return subprocess.run(cmd, **kwargs)

# FFmpeg路径配置 - 可以手动指定FFmpeg路径
FFMPEG_PATH = None  # 例如: "C:/ffmpeg/bin/ffmpeg.exe"
FFPROBE_PATH = None  # 例如: "C:/ffmpeg/bin/ffprobe.exe"


def _get_imageio_ffmpeg_path() -> str:
    """获取imageio-ffmpeg包中的FFmpeg路径（完整版）"""
    try:
        import imageio_ffmpeg
        path = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(path):
            return path
    except:
        pass
    return ""


# 常见的FFmpeg安装位置（优先使用完整版）
COMMON_FFMPEG_PATHS = [
    # imageio-ffmpeg包中的完整版FFmpeg
    _get_imageio_ffmpeg_path(),
    # 其他位置
    "C:/ffmpeg/bin/ffmpeg.exe",
    "C:/Program Files/ffmpeg/bin/ffmpeg.exe",
]


def _find_ffmpeg() -> str:
    """查找FFmpeg可执行文件路径"""
    global FFMPEG_PATH

    # 如果已配置，直接返回
    if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
        return FFMPEG_PATH

    # 尝试从PATH中查找
    path = shutil.which('ffmpeg')
    if path:
        return path

    # 尝试常见路径
    for common_path in COMMON_FFMPEG_PATHS:
        if os.path.exists(common_path):
            FFMPEG_PATH = common_path
            return common_path

    return 'ffmpeg'  # 返回默认名称，让系统尝试


def _find_ffprobe() -> str:
    """查找FFprobe可执行文件路径"""
    global FFPROBE_PATH

    # 如果已配置，直接返回
    if FFPROBE_PATH and os.path.exists(FFPROBE_PATH):
        return FFPROBE_PATH

    # 尝试从PATH中查找
    path = shutil.which('ffprobe')
    if path:
        return path

    # 尝试常见路径（与ffmpeg同目录）
    ffmpeg_path = _find_ffmpeg()
    if ffmpeg_path and ffmpeg_path != 'ffmpeg':
        ffmpeg_dir = os.path.dirname(ffmpeg_path)
        ffprobe_path = os.path.join(ffmpeg_dir, 'ffprobe.exe')
        if os.path.exists(ffprobe_path):
            FFPROBE_PATH = ffprobe_path
            return ffprobe_path

    # 使用TRAE的ffprobe（精简版但ffprobe功能足够）
    trae_ffprobe = "D:/123/ai/TRAE SOLO CN/resources/app/bin/ffprobe.exe"
    if os.path.exists(trae_ffprobe):
        FFPROBE_PATH = trae_ffprobe
        return trae_ffprobe

    return 'ffprobe'  # 返回默认名称


def set_ffmpeg_path(ffmpeg_path: str, ffprobe_path: str = None):
    """
    手动设置FFmpeg路径

    Args:
        ffmpeg_path: ffmpeg可执行文件路径
        ffprobe_path: ffprobe可执行文件路径（可选）
    """
    global FFMPEG_PATH, FFPROBE_PATH
    FFMPEG_PATH = ffmpeg_path
    FFPROBE_PATH = ffprobe_path or ffmpeg_path.replace('ffmpeg', 'ffprobe')


def check_ffmpeg_installed() -> bool:
    """检查FFmpeg是否已安装"""
    ffmpeg = _find_ffmpeg()
    return os.path.exists(ffmpeg) or shutil.which('ffmpeg') is not None


def check_ffprobe_installed() -> bool:
    """检查FFprobe是否已安装"""
    ffprobe = _find_ffprobe()
    return os.path.exists(ffprobe) or shutil.which('ffprobe') is not None


def get_ffmpeg_version() -> Optional[str]:
    """获取FFmpeg版本"""
    try:
        ffmpeg = _find_ffmpeg()
        result = _run_subprocess(
            [ffmpeg, '-version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # 解析版本号
            first_line = result.stdout.split('\n')[0]
            return first_line
        return None
    except:
        return None


def get_video_duration(video_path: str) -> float:
    """获取视频时长（秒）"""
    try:
        ffprobe = _find_ffprobe()
        cmd = [
            ffprobe,
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = _run_subprocess(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return 0.0
    except:
        return 0.0


def get_video_resolution(video_path: str) -> Optional[Tuple[int, int]]:
    """获取视频分辨率"""
    try:
        ffprobe = _find_ffprobe()
        cmd = [
            ffprobe,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=s=x:p=0',
            video_path
        ]
        result = _run_subprocess(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            parts = result.stdout.strip().split('x')
            if len(parts) == 2:
                return (int(parts[0]), int(parts[1]))
        return None
    except:
        return None


def get_video_fps(video_path: str) -> Optional[float]:
    """获取视频帧率"""
    try:
        ffprobe = _find_ffprobe()
        cmd = [
            ffprobe,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=r_frame_rate',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = _run_subprocess(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            fps_str = result.stdout.strip()
            if '/' in fps_str:
                num, den = fps_str.split('/')
                return round(int(num) / int(den), 2)
            return float(fps_str)
        return None
    except:
        return None


def extract_video_segment(
    input_path: str,
    output_path: str,
    start_time: float,
    duration: float
) -> bool:
    """
    提取视频片段

    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径
        start_time: 开始时间（秒）
        duration: 持续时间（秒）

    Returns:
        是否成功
    """
    try:
        ffmpeg = _find_ffmpeg()
        cmd = [
            ffmpeg, '-y',
            '-ss', str(start_time),
            '-i', input_path,
            '-t', str(duration),
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            output_path
        ]
        result = _run_subprocess(cmd, capture_output=True, timeout=300)
        return result.returncode == 0
    except:
        return False


def add_silence_audio(video_path: str, output_path: str, duration: float) -> bool:
    """
    为视频添加静音音频轨道（如果没有音频）

    Args:
        video_path: 输入视频路径
        output_path: 输出视频路径
        duration: 静音时长（秒）

    Returns:
        是否成功
    """
    try:
        ffmpeg = _find_ffmpeg()
        cmd = [
            ffmpeg, '-y',
            '-i', video_path,
            '-f', 'lavfi', '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-t', str(duration),
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-shortest',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0
    except:
        return False


def create_video_from_image(image_path: str, output_path: str, duration: float = 3.0) -> bool:
    """
    从图片创建视频

    Args:
        image_path: 图片路径
        output_path: 输出视频路径
        duration: 视频时长（秒）

    Returns:
        是否成功
    """
    try:
        ffmpeg = _find_ffmpeg()
        cmd = [
            ffmpeg, '-y',
            '-loop', '1',
            '-i', image_path,
            '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-t', str(duration),
            '-c:v', 'libx264',
            '-tune', 'stillimage',
            '-c:a', 'aac',
            '-shortest',
            '-pix_fmt', 'yuv420p',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0
    except:
        return False


def get_hardware_encoders() -> list:
    """获取可用的硬件编码器"""
    encoders = []

    try:
        ffmpeg = _find_ffmpeg()
        result = subprocess.run(
            [ffmpeg, '-encoders'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            output = result.stdout.lower()

            # 检查各种硬件编码器
            if 'h264_nvenc' in output:
                encoders.append(('NVIDIA NVENC (H.264)', 'h264_nvenc'))
            if 'hevc_nvenc' in output:
                encoders.append(('NVIDIA NVENC (H.265)', 'hevc_nvenc'))
            if 'h264_qsv' in output:
                encoders.append(('Intel QSV (H.264)', 'h264_qsv'))
            if 'hevc_qsv' in output:
                encoders.append(('Intel QSV (H.265)', 'hevc_qsv'))
            if 'h264_amf' in output:
                encoders.append(('AMD AMF (H.264)', 'h264_amf'))
            if 'hevc_amf' in output:
                encoders.append(('AMD AMF (H.265)', 'hevc_amf'))

    except:
        pass

    return encoders


def estimate_output_size(
    duration_seconds: float,
    video_bitrate_kbps: int = 2000,
    audio_bitrate_kbps: int = 128
) -> float:
    """
    估算输出文件大小（MB）

    Args:
        duration_seconds: 视频时长（秒）
        video_bitrate_kbps: 视频比特率（kbps）
        audio_bitrate_kbps: 音频比特率（kbps）

    Returns:
        预估大小（MB）
    """
    total_bitrate = video_bitrate_kbps + audio_bitrate_kbps
    size_bytes = (total_bitrate * 1000 / 8) * duration_seconds
    return size_bytes / (1024 * 1024)
