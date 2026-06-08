"""视频合并核心模块 - 使用FFmpeg合并视频"""
import subprocess
import os
import tempfile
from typing import List, Optional, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from .video_info import VideoInfo
from .ffmpeg_utils import _find_ffmpeg, _run_subprocess


def _check_nvenc_available() -> bool:
    """检查NVENC是否可用"""
    ffmpeg = _find_ffmpeg()
    try:
        result = _run_subprocess([ffmpeg, '-encoders'], capture_output=True, text=True, timeout=5)
        return 'h264_nvenc' in result.stdout
    except:
        return False


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
    hardware_accel: str = "auto"  # 硬件加速: auto, nvenc, qsv, amf, cpu
    transition: str = "none"  # 转场效果: none, fade, dissolve, wipe_left, wipe_right, slide_left, slide_right
    transition_duration: float = 0.5  # 转场时长（秒）


def _get_encoder_cmd(config: MergeConfig) -> list:
    """获取编码器命令参数"""
    hw_accel = config.hardware_accel
    nvenc_available = _check_nvenc_available()

    # 自动选择
    if hw_accel == "auto" and nvenc_available:
        hw_accel = "nvenc"

    cmd = []

    if hw_accel == "nvenc" and nvenc_available:
        # NVIDIA NVENC
        if config.codec == 'h265':
            cmd.extend(['-c:v', 'hevc_nvenc'])
        else:
            cmd.extend(['-c:v', 'h264_nvenc'])

        quality_map = {"low": "30", "medium": "25", "high": "20"}
        cq = quality_map.get(config.quality, "25")
        cmd.extend(['-cq', cq, '-preset', 'medium'])
    else:
        # CPU编码
        if config.codec == 'h265':
            cmd.extend(['-c:v', 'libx265'])
        else:
            cmd.extend(['-c:v', 'libx264'])

        quality_map = {"low": "28", "medium": "23", "high": "18"}
        crf = quality_map.get(config.quality, "23")
        cmd.extend(['-crf', crf, '-preset', 'medium'])

    # 关键：指定像素格式为yuv420p，确保兼容性
    cmd.extend(['-pix_fmt', 'yuv420p'])
    cmd.extend(['-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart'])
    return cmd




def _get_transition_filter(transition: str, duration: float, idx: int, offset: float) -> str:
    """
    生成转场滤镜

    Args:
        transition: 转场类型
        duration: 转场时长（秒）
        idx: 当前视频索引
        offset: 转场开始时间（秒）

    Returns:
        FFmpeg滤镜字符串
    """
    if transition == "none":
        return ""

    # xfade转场效果
    transitions = {
        "fade": "fade",
        "dissolve": "dissolve",
        "wipe_left": "wipeleft",
        "wipe_right": "wiperight",
        "slide_left": "slideleft",
        "slide_right": "slideright",
        "smooth_left": "smoothleft",
        "smooth_right": "smoothright",
        "circle_open": "circleopen",
        "circle_close": "circleclose",
        "pixelize": "pixelize",
        "radial": "radial",
        "horzopen": "horzopen",
        "horzclose": "horzclose",
        "vertopen": "vertopen",
        "vertclose": "vertclose",
        "diag_bl": "diagbl",
        "diag_br": "diagbr",
        "hlslice": "hlslice",
        "hrslice": "hrslice",
        "vuslice": "vuslice",
        "vdslice": "vdslice",
    }

    xfade_type = transitions.get(transition, "fade")
    return f"xfade=transition={xfade_type}:duration={duration}:offset={offset}"


def _get_video_duration(video_path: str) -> float:
    """获取视频时长（秒）"""
    try:
        from .ffmpeg_utils import _find_ffprobe
        ffprobe = _find_ffprobe()
        cmd = [
            ffprobe, '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass
    return 0.0


def _check_audio_streams(video_paths: List[str]) -> bool:
    """检查视频文件是否有音频流"""
    try:
        from .ffmpeg_utils import _find_ffprobe
        ffprobe = _find_ffprobe()
        # 只检查第一个视频
        cmd = [
            ffprobe, '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=codec_type',
            '-of', 'csv=p=0',
            video_paths[0]
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return 'audio' in result.stdout
    except:
        pass
    return False


def merge_videos_concat(
    video_paths: List[str],
    output_path: str,
    config: MergeConfig,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Tuple[bool, str]:
    """
    使用FFmpeg concat方式合并视频

    Returns:
        (是否成功, 错误信息)
    """
    if not video_paths:
        return False, "没有视频文件"

    ffmpeg = _find_ffmpeg()
    filelist_path = None

    try:
        # 创建临时文件列表
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            filelist_path = f.name
            for path in video_paths:
                escaped_path = path.replace("'", "'\\''").replace("\\", "/")
                f.write(f"file '{escaped_path}'\n")

        # 构建FFmpeg命令
        cmd = [ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', filelist_path]

        # 添加视频滤镜
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
        encoder_cmd = _get_encoder_cmd(config)
        cmd.extend(encoder_cmd)
        cmd.append(output_path)

        if progress_callback:
            progress_callback(0, "concat合并中...")

        # 执行命令
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_msg = stderr[-300:] if stderr else "未知错误"
            return False, f"FFmpeg错误: {error_msg}"

        if not os.path.exists(output_path):
            return False, "输出文件未生成"

        if progress_callback:
            progress_callback(1.0, "concat合并完成")

        return True, "成功"

    except Exception as e:
        return False, f"异常: {str(e)}"
    finally:
        if filelist_path and os.path.exists(filelist_path):
            try:
                os.unlink(filelist_path)
            except:
                pass


def merge_videos_filter_complex(
    video_paths: List[str],
    output_path: str,
    config: MergeConfig,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Tuple[bool, str]:
    """
    使用FFmpeg filter_complex方式合并视频（支持转场）

    Returns:
        (是否成功, 错误信息)
    """
    if not video_paths:
        return False, "没有视频文件"

    ffmpeg = _find_ffmpeg()
    n = len(video_paths)
    has_transition = config.transition != "none" and n >= 2

    try:
        cmd = [ffmpeg, '-y']

        # 添加所有输入文件
        for path in video_paths:
            cmd.extend(['-i', path])

        # 检查是否有音频流
        has_audio = _check_audio_streams(video_paths)

        # 构建filter_complex
        video_filters = []
        audio_filters = []

        # 确定目标分辨率
        target_res = config.resolution
        if not target_res:
            target_res = "720x1280"

        target_w, target_h = target_res.split('x')

        # 获取每个视频的时长（用于转场计算）
        durations = []
        if has_transition:
            for path in video_paths:
                dur = _get_video_duration(path)
                durations.append(dur if dur > 0 else 3.0)  # 默认3秒

        for i in range(n):
            # 视频处理：统一分辨率和帧率
            video_filters.append(
                f"[{i}:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,"
                f"setpts=PTS-STARTPTS,fps=25[v{i}]"
            )
            # 音频处理（如果有音频流）
            if has_audio:
                audio_filters.append(f"[{i}:a]aresample=44100,asetpts=PTS-STARTPTS[a{i}]")

        if has_transition:
            # 使用xfade转场
            transition_duration = config.transition_duration

            # 视频转场链
            current_offset = durations[0] - transition_duration

            for i in range(1, n):
                # 视频xfade
                xfade_filter = _get_transition_filter(
                    config.transition, transition_duration, i, current_offset
                )
                if i == 1:
                    video_chain = f"[v0][v1]{xfade_filter}[vt{i}]"
                else:
                    video_chain = f"[vt{i-1}][v{i}]{xfade_filter}[vt{i}]"

                video_filters.append(video_chain)

                # 更新偏移量
                if i < n - 1:
                    current_offset += durations[i] - transition_duration

            # 最终视频输出
            final_video = f"[vt{n-1}]"

            # 音频处理（使用concat拼接，不做转场）
            if has_audio:
                audio_inputs = ''.join(f'[a{i}]' for i in range(n))
                audio_concat = f"{audio_inputs}concat=n={n}:v=0:a=1[outa]"
                audio_filters.append(audio_concat)
                final_audio = "[outa]"
            else:
                final_audio = None
        else:
            # 无转场，使用concat
            video_inputs = ''.join(f'[v{i}]' for i in range(n))
            if has_audio:
                audio_inputs = ''.join(f'[a{i}]' for i in range(n))
                concat_filter = f"{video_inputs}{audio_inputs}concat=n={n}:v=1:a=1[outv][outa]"
            else:
                concat_filter = f"{video_inputs}concat=n={n}:v=1:a=0[outv]"
            video_filters.append(concat_filter)
            final_video = "[outv]"
            final_audio = "[outa]" if has_audio else None

        # 构建完整filter_complex
        filter_complex = ';'.join(video_filters + audio_filters)

        cmd.extend(['-filter_complex', filter_complex])
        cmd.extend(['-map', final_video])
        if final_audio:
            cmd.extend(['-map', final_audio])

        # 编码参数
        encoder_cmd = _get_encoder_cmd(config)
        cmd.extend(encoder_cmd)
        cmd.append(output_path)

        if progress_callback:
            progress_callback(0, f"合并中（转场: {config.transition}）...")

        # 执行命令
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_msg = stderr[-500:] if stderr else "未知错误"
            return False, f"FFmpeg错误: {error_msg}"

        if not os.path.exists(output_path):
            return False, "输出文件未生成"

        if progress_callback:
            progress_callback(1.0, "合并完成")

        return True, "成功"

    except Exception as e:
        return False, f"异常: {str(e)}"


def merge_videos(
    videos: List[VideoInfo],
    output_path: str,
    config: MergeConfig,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Tuple[bool, str]:
    """
    合并视频（自动选择最佳方式）

    Returns:
        (是否成功, 错误信息)
    """
    if not videos or len(videos) < 2:
        return False, "视频数量不足"

    video_paths = [v.视频路径 for v in videos]

    # 检查文件是否存在
    for path in video_paths:
        if not os.path.exists(path):
            return False, f"文件不存在: {os.path.basename(path)}"

    # 检查视频格式是否一致
    formats = set()
    for v in videos:
        formats.add(v.视频分辨率)

    format_consistent = len(formats) <= 1
    need_preprocess = config.resolution is not None or config.fps is not None
    has_transition = config.transition != "none"

    # 选择合并方式
    if has_transition:
        # 有转场必须使用filter_complex
        if progress_callback:
            progress_callback(0, f"使用转场效果: {config.transition}")
        success, msg = merge_videos_filter_complex(video_paths, output_path, config, progress_callback)
    elif format_consistent and not need_preprocess:
        if progress_callback:
            progress_callback(0, "格式一致，使用concat方式")
        success, msg = merge_videos_concat(video_paths, output_path, config, progress_callback)
    else:
        if progress_callback:
            progress_callback(0, "格式不一致，使用filter_complex方式")
        success, msg = merge_videos_filter_complex(video_paths, output_path, config, progress_callback)

    # 如果第一种方式失败，尝试另一种
    if not success:
        if progress_callback:
            progress_callback(0, f"第一种方式失败，尝试另一种...")

        if format_consistent and not need_preprocess:
            success, msg = merge_videos_filter_complex(video_paths, output_path, config, progress_callback)
        else:
            success, msg = merge_videos_concat(video_paths, output_path, config, progress_callback)

    return success, msg


def batch_merge_videos(
    combinations: List[List[VideoInfo]],
    config: MergeConfig,
    progress_callback: Optional[Callable[[int, int, float, str], None]] = None
) -> Tuple[int, int, List[str], List[str]]:
    """
    批量合并视频

    Returns:
        (成功数, 失败数, 成功文件列表, 失败原因列表)
    """
    success_count = 0
    fail_count = 0
    output_files = []
    fail_reasons = []

    total = len(combinations)

    # 确保输出目录存在
    if config.output_dir:
        os.makedirs(config.output_dir, exist_ok=True)

    for idx, combo in enumerate(combinations):
        file_name = f"{config.file_prefix}_{idx + 1:03d}.mp4"

        if config.output_dir:
            output_path = os.path.join(config.output_dir, file_name)
        else:
            output_path = file_name

        def local_progress(progress, status):
            if progress_callback:
                progress_callback(idx + 1, total, progress, status)

        # 显示当前合成信息
        video_names = [v.视频文件名称[:20] for v in combo]
        if progress_callback:
            progress_callback(idx + 1, total, 0, f"准备: {' + '.join(video_names)}")

        # 检查视频文件
        all_exist = True
        for v in combo:
            if not os.path.exists(v.视频路径):
                error_msg = f"文件不存在: {v.视频文件名称}"
                fail_reasons.append(error_msg)
                if progress_callback:
                    progress_callback(idx + 1, total, 0, error_msg)
                all_exist = False
                break

        if not all_exist:
            fail_count += 1
            continue

        # 合并视频
        success, error_msg = merge_videos(combo, output_path, config, local_progress)

        if success and os.path.exists(output_path):
            success_count += 1
            output_files.append(output_path)
            if progress_callback:
                progress_callback(idx + 1, total, 1.0, f"成功: {file_name}")
        else:
            fail_count += 1
            fail_reasons.append(f"{file_name}: {error_msg}")
            if progress_callback:
                progress_callback(idx + 1, total, 0, f"失败: {error_msg}")

    return success_count, fail_count, output_files, fail_reasons
