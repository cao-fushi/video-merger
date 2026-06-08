"""视频信息提取模块 - 使用FFprobe获取视频详细信息"""
import subprocess
import json
import os
from dataclasses import dataclass, asdict
from typing import Optional, List
from pathlib import Path
from .ffmpeg_utils import _find_ffprobe


@dataclass
class VideoInfo:
    """视频信息数据类"""
    序号: int = 0
    是否选择: bool = True
    视频文件名称: str = ""
    视频文件名称带扩展: str = ""
    视频时长: str = "00:00:00"
    视频时长秒: float = 0.0
    视频分辨率: str = ""
    视频大小: str = ""
    视频路径: str = ""
    编码器信息: str = ""
    比特率信息: str = ""
    视频比特率信息: str = ""
    音频比特率信息: str = ""
    帧率信息: str = ""
    视频信息: str = ""
    音频信息: str = ""
    视音频类型: int = 1
    处理状态: str = "未处理"
    是否开头视频: bool = False

    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> 'VideoInfo':
        """从字典创建"""
        info = VideoInfo()
        for key, value in data.items():
            if hasattr(info, key):
                setattr(info, key, value)
        return info


def get_video_info(video_path: str) -> Optional[VideoInfo]:
    """
    使用FFprobe获取视频信息

    Args:
        video_path: 视频文件路径

    Returns:
        VideoInfo对象，失败返回None
    """
    if not os.path.exists(video_path):
        print(f"文件不存在: {video_path}")
        return None

    try:
        # 使用ffprobe获取视频信息
        ffprobe = _find_ffprobe()
        cmd = [
            ffprobe,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]

        # 设置超时时间，大文件可能需要更长时间
        file_size = os.path.getsize(video_path)
        timeout = max(30, min(300, file_size // (1024 * 1024)))  # 根据文件大小动态调整超时

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        if result.returncode != 0:
            print(f"FFprobe执行失败: {result.stderr}")
            return None

        data = json.loads(result.stdout)

        # 解析视频流信息
        video_stream = None
        audio_stream = None
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video' and video_stream is None:
                video_stream = stream
            elif stream.get('codec_type') == 'audio' and audio_stream is None:
                audio_stream = stream

        if not video_stream:
            print(f"未找到视频流: {video_path}")
            return None

        # 获取文件信息
        file_name = os.path.basename(video_path)
        file_name_no_ext = os.path.splitext(file_name)[0]
        file_size = os.path.getsize(video_path)
        format_info = data.get('format', {})

        # 计算时长
        duration = float(format_info.get('duration', 0))
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = duration % 60
        duration_str = f"{hours:02d}:{minutes:02d}:{seconds:05.2f}"

        # 获取分辨率
        width = video_stream.get('width', 0)
        height = video_stream.get('height', 0)
        resolution = f"{width}x{height}"

        # 获取帧率
        fps = video_stream.get('r_frame_rate', '0/1')
        if '/' in fps:
            num, den = fps.split('/')
            fps = str(round(int(num) / int(den), 2)) if int(den) != 0 else '0'

        # 获取比特率
        bitrate = format_info.get('bit_rate', '0')
        bitrate_str = f"{int(bitrate) // 1000} kb/s" if bitrate.isdigit() else bitrate

        video_bitrate = video_stream.get('bit_rate', '0')
        video_bitrate_str = f"{int(video_bitrate) // 1000} kb/s" if video_bitrate.isdigit() else video_bitrate

        audio_bitrate = audio_stream.get('bit_rate', '0') if audio_stream else '0'
        audio_bitrate_str = f"{int(audio_bitrate) // 1000} kb/s" if audio_bitrate.isdigit() else audio_bitrate

        # 构建视频信息字符串
        video_codec = video_stream.get('codec_name', '')
        video_profile = video_stream.get('profile', '')
        pix_fmt = video_stream.get('pix_fmt', '')
        video_info_str = (
            f"{video_codec} ({video_profile}), {pix_fmt}, "
            f"{width}x{height}, {video_bitrate_str}, "
            f"{fps} fps"
        )

        # 音频信息字符串
        audio_info_str = ""
        if audio_stream:
            audio_codec = audio_stream.get('codec_name', '')
            audio_profile = audio_stream.get('profile', '')
            sample_rate = audio_stream.get('sample_rate', '')
            channels = audio_stream.get('channels', '')
            audio_info_str = (
                f"{audio_codec} ({audio_profile}), "
                f"{sample_rate} Hz, {channels} channels, "
                f"{audio_bitrate_str}"
            )

        # 编码器信息
        encoder = format_info.get('tags', {}).get('encoder', '')

        # 判断视音频类型
        av_type = 1  # 有视频有音频
        if not audio_stream:
            av_type = 0  # 只有视频

        return VideoInfo(
            序号=0,
            是否选择=True,
            视频文件名称=file_name_no_ext,
            视频文件名称带扩展=file_name,
            视频时长=duration_str,
            视频时长秒=round(duration, 3),
            视频分辨率=resolution,
            视频大小=format_size(file_size),
            视频路径=video_path,
            编码器信息=encoder,
            比特率信息=bitrate_str,
            视频比特率信息=video_bitrate_str,
            音频比特率信息=audio_bitrate_str,
            帧率信息=fps,
            视频信息=video_info_str,
            音频信息=audio_info_str,
            视音频类型=av_type,
            处理状态="未处理",
            是否开头视频=False
        )

    except Exception as e:
        print(f"获取视频信息失败: {e}")
        return None


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f}TB"


def batch_get_video_info(video_paths: List[str]) -> List[VideoInfo]:
    """
    批量获取视频信息

    Args:
        video_paths: 视频文件路径列表

    Returns:
        VideoInfo列表
    """
    videos = []
    for idx, path in enumerate(video_paths, 1):
        info = get_video_info(path)
        if info:
            info.序号 = idx
            videos.append(info)
    return videos


def load_video_list_from_json(json_path: str) -> List[VideoInfo]:
    """
    从JSON文件加载视频列表（兼容江湖工具箱格式）

    Args:
        json_path: JSON文件路径

    Returns:
        VideoInfo列表
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        videos = []
        for idx, item in enumerate(data, 1):
            if isinstance(item, dict):
                info = VideoInfo.from_dict(item)
                info.序号 = idx
                videos.append(info)
        return videos
    except Exception as e:
        print(f"加载JSON失败: {e}")
        return []


def save_video_list_to_json(videos: List[VideoInfo], json_path: str) -> bool:
    """
    保存视频列表到JSON文件

    Args:
        videos: VideoInfo列表
        json_path: JSON文件路径

    Returns:
        是否成功
    """
    try:
        data = [v.to_dict() for v in videos]
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存JSON失败: {e}")
        return False
