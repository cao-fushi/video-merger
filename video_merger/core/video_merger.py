"""视频合并核心模块 - 使用FFmpeg合并视频"""
import subprocess
import os
import tempfile
from typing import List, Optional, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass
from .video_info import VideoInfo
from .ffmpeg_utils import _find_ffmpeg


@dataclass
class MergeConfig:
    """合并配置"""
    output_dir: str = ""  # 输出目录
    file_prefix: str = "合成视频"  # 文件前缀
    resolution: Optional[str] = None  # 统一分辨率，如 "1080x1920"
    fps: Optional[int] = None  # 统一帧率
    codec: str = "h264"  # 编码器: h264, h265
    quality: str = "high"  # 质量: low, medium, high
    crop_black_bars: bool = False  # 裁剪黑边
    hardware_accel: Optional[str] = None  # 硬件加速: cuda, qsv, etc.


def get_quality_params(quality: str, codec: str) -> dict:
    """获取质量参数"""
    params = {
        "low": {"crf": "28", "preset": "ultrafast"},
        "medium": {"crf": "23", "preset": "medium"},
        "high": {"crf": "18", "preset": "slow"},
    }
    return params.get(quality, params["high"])


def normalize_video(
    input_path: str,
    output_path: str,
    target_resolution: Optional[str] = None,
    target_fps: Optional[int] = None,
    crop_black_bars: bool = False,
    progress_callback: Optional[Callable[[float], None]] = None
) -> bool:
    """
    标准化视频格式（统一分辨率、帧率等）

    Args:
        input_path: 输入视频路径
        output_path: 输出视频路径
        target_resolution: 目标分辨率，如 "1080x1920"
        target_fps: 目标帧率
        crop_black_bars: 是否裁剪黑边
        progress_callback: 进度回调函数

    Returns:
        是否成功
    """
    try:
        ffmpeg = _find_ffmpeg()
        cmd = [ffmpeg, '-y', '-i', input_path]

        # 构建视频滤镜
        filters = []

        # 裁剪黑边
        if crop_black_bars:
            filters.append("cropdetect=24:16:0")

        # 调整分辨率
        if target_resolution:
            width, height = target_resolution.split('x')
            filters.append(f"scale={width}:{height}:force_original_aspect_ratio=decrease")
            filters.append(f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")

        # 调整帧率
        if target_fps:
            filters.append(f"fps={target_fps}")

        if filters:
            cmd.extend(['-vf', ','.join(filters)])

        # 编码参数
        cmd.extend([
            '-c:v', 'libx264',
            '-crf', '23',
            '-preset', 'medium',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            output_path
        ])

        # 执行命令
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        _, stderr = process.communicate()

        if process.returncode != 0:
            print(f"视频标准化失败: {stderr}")
            return False

        return True

    except Exception as e:
        print(f"视频标准化异常: {e}")
        return False


def merge_videos_concat(
    video_paths: List[str],
    output_path: str,
    config: MergeConfig,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> bool:
    """
    使用FFmpeg concat方式合并视频

    Args:
        video_paths: 视频文件路径列表
        output_path: 输出文件路径
        config: 合并配置
        progress_callback: 进度回调函数 (进度0-1, 状态信息)

    Returns:
        是否成功
    """
    if not video_paths:
        return False

    try:
        # 创建临时文件列表
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            filelist_path = f.name
            for path in video_paths:
                # 转义路径中的特殊字符
                escaped_path = path.replace("'", "'\\''").replace("\\", "/")
                f.write(f"file '{escaped_path}'\n")

        # 构建FFmpeg命令
        ffmpeg = _find_ffmpeg()
        cmd = [ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', filelist_path]

        # 添加视频滤镜（如果需要）
        filters = []
        if config.resolution:
            width, height = config.resolution.split('x')
            filters.append(f"scale={width}:{height}:force_original_aspect_ratio=decrease")
            filters.append(f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")

        if config.fps:
            filters.append(f"fps={config.fps}")

        if filters:
            cmd.extend(['-vf', ','.join(filters)])

        # 编码参数
        quality_params = get_quality_params(config.quality, config.codec)

        if config.codec == 'h265':
            cmd.extend(['-c:v', 'libx265'])
        else:
            cmd.extend(['-c:v', 'libx264'])

        cmd.extend([
            '-crf', quality_params['crf'],
            '-preset', quality_params['preset'],
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            output_path
        ])

        if progress_callback:
            progress_callback(0, "开始合并...")

        # 执行命令
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        _, stderr = process.communicate()

        # 清理临时文件
        try:
            os.unlink(filelist_path)
        except:
            pass

        if process.returncode != 0:
            if progress_callback:
                progress_callback(0, f"合并失败: {stderr[:200]}")
            return False

        if progress_callback:
            progress_callback(1.0, "合并完成")

        return True

    except Exception as e:
        if progress_callback:
            progress_callback(0, f"合并异常: {str(e)}")
        return False


def merge_videos_filter_complex(
    video_paths: List[str],
    output_path: str,
    config: MergeConfig,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> bool:
    """
    使用FFmpeg filter_complex方式合并视频（更灵活，可处理不同格式）

    Args:
        video_paths: 视频文件路径列表
        output_path: 输出文件路径
        config: 合并配置
        progress_callback: 进度回调函数

    Returns:
        是否成功
    """
    if not video_paths:
        return False

    try:
        ffmpeg = _find_ffmpeg()
        cmd = [ffmpeg, '-y']

        # 添加所有输入文件
        for path in video_paths:
            cmd.extend(['-i', path])

        n = len(video_paths)

        # 构建filter_complex
        video_filters = []
        audio_filters = []

        for i in range(n):
            # 视频处理
            vf_parts = []
            if config.resolution:
                width, height = config.resolution.split('x')
                vf_parts.append(f"scale={width}:{height}:force_original_aspect_ratio=decrease")
                vf_parts.append(f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")
            if config.fps:
                vf_parts.append(f"fps={config.fps}")

            if vf_parts:
                video_filters.append(f"[{i}:v]{','.join(vf_parts)}[v{i}]")
            else:
                video_filters.append(f"[{i}:v]copy[v{i}]")

            # 音频处理
            audio_filters.append(f"[{i}:a]aresample=44100[a{i}]")

        # 拼接
        video_inputs = ''.join(f'[v{i}]' for i in range(n))
        audio_inputs = ''.join(f'[a{i}]' for i in range(n))
        concat_filter = f"{video_inputs}{audio_inputs}concat=n={n}:v=1:a=1[outv][outa]"

        filter_complex = ';'.join(video_filters + audio_filters + [concat_filter])

        cmd.extend(['-filter_complex', filter_complex])
        cmd.extend(['-map', '[outv]', '-map', '[outa]'])

        # 编码参数
        quality_params = get_quality_params(config.quality, config.codec)

        if config.codec == 'h265':
            cmd.extend(['-c:v', 'libx265'])
        else:
            cmd.extend(['-c:v', 'libx264'])

        cmd.extend([
            '-crf', quality_params['crf'],
            '-preset', quality_params['preset'],
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            output_path
        ])

        if progress_callback:
            progress_callback(0, "开始合并...")

        # 执行命令
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        _, stderr = process.communicate()

        if process.returncode != 0:
            if progress_callback:
                progress_callback(0, f"合并失败: {stderr[:200]}")
            return False

        if progress_callback:
            progress_callback(1.0, "合并完成")

        return True

    except Exception as e:
        if progress_callback:
            progress_callback(0, f"合并异常: {str(e)}")
        return False


def merge_videos(
    videos: List[VideoInfo],
    output_path: str,
    config: MergeConfig,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> bool:
    """
    合并视频（自动选择最佳方式）

    Args:
        videos: 视频信息列表
        output_path: 输出文件路径
        config: 合并配置
        progress_callback: 进度回调函数

    Returns:
        是否成功
    """
    video_paths = [v.视频路径 for v in videos]

    # 检查是否需要预处理
    need_preprocess = (
        config.resolution is not None or
        config.fps is not None or
        config.crop_black_bars
    )

    # 检查视频格式是否一致
    formats = set()
    for v in videos:
        formats.add(v.视频分辨率)
        formats.add(v.帧率信息)

    format_consistent = len(formats) <= 2  # 允许分辨率和帧率各一种

    if need_preprocess or not format_consistent:
        # 需要预处理或格式不一致，使用filter_complex
        return merge_videos_filter_complex(video_paths, output_path, config, progress_callback)
    else:
        # 格式一致，使用concat（更快）
        return merge_videos_concat(video_paths, output_path, config, progress_callback)


def batch_merge_videos(
    combinations: List[List[VideoInfo]],
    config: MergeConfig,
    progress_callback: Optional[Callable[[int, int, float, str], None]] = None
) -> Tuple[int, int, List[str]]:
    """
    批量合并视频

    Args:
        combinations: 合成方案列表
        config: 合并配置
        progress_callback: 进度回调函数 (当前索引, 总数, 当前进度, 状态信息)

    Returns:
        (成功数, 失败数, 输出文件路径列表)
    """
    success_count = 0
    fail_count = 0
    output_files = []

    total = len(combinations)

    for idx, combo in enumerate(combinations):
        # 生成输出文件名
        file_name = f"{config.file_prefix}_{idx + 1:03d}.mp4"

        # 确定输出目录（按开头视频分组）
        if combo and config.output_dir:
            first_video_name = combo[0].视频文件名称
            # 清理文件名中的非法字符
            first_video_name = "".join(c for c in first_video_name if c.isalnum() or c in "._- ")
            first_video_name = first_video_name[:50]  # 限制长度

            output_dir = os.path.join(config.output_dir, first_video_name)
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, file_name)
        else:
            output_path = os.path.join(config.output_dir or ".", file_name)

        def local_progress(progress, status):
            if progress_callback:
                progress_callback(idx + 1, total, progress, status)

        # 合并视频
        success = merge_videos(combo, output_path, config, local_progress)

        if success:
            success_count += 1
            output_files.append(output_path)
        else:
            fail_count += 1

    return success_count, fail_count, output_files
