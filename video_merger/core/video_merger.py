"""视频合并核心模块 - 使用FFmpeg合并视频（优化版）"""
import subprocess
import os
import tempfile
import logging
from typing import List, Optional, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from .video_info import VideoInfo
from .ffmpeg_utils import _find_ffmpeg, _run_subprocess

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Windows下隐藏命令行窗口的标志
CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0


def _test_encoder(encoder_name: str) -> bool:
    """测试指定编码器是否能正常工作"""
    ffmpeg = _find_ffmpeg()

    # 首先检查FFmpeg是否编译了该编码器
    try:
        result = _run_subprocess([ffmpeg, '-encoders'], capture_output=True, text=True, timeout=5)
        if encoder_name not in result.stdout:
            return False
    except Exception as e:
        logger.warning(f"检查编码器 {encoder_name} 失败: {e}")
        return False

    # 实际测试编码器是否能工作
    import tempfile
    test_dir = tempfile.mkdtemp()
    test_output = os.path.join(test_dir, f'{encoder_name}_test.mp4')

    try:
        cmd = [
            ffmpeg, '-y',
            '-f', 'lavfi', '-i', 'color=c=red:s=64x64:d=0.1',
            '-c:v', encoder_name,
            '-preset', 'fast',
            test_output
        ]
        result = _run_subprocess(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and os.path.exists(test_output):
            logger.info(f"{encoder_name} 测试通过")
            return True
        else:
            logger.info(f"{encoder_name} 测试失败")
            return False
    except Exception as e:
        logger.info(f"{encoder_name} 测试异常: {e}")
        return False
    finally:
        # 清理测试文件
        try:
            if os.path.exists(test_output):
                os.unlink(test_output)
            os.rmdir(test_dir)
        except:
            pass


def _check_nvenc_available() -> bool:
    """检查NVIDIA NVENC是否可用"""
    return _test_encoder('h264_nvenc')


def _check_amf_available() -> bool:
    """检查AMD AMF是否可用"""
    return _test_encoder('h264_amf')


def _check_qsv_available() -> bool:
    """检查Intel QSV是否可用"""
    return _test_encoder('h264_qsv')


def get_best_encoder() -> str:
    """自动检测最佳编码器"""
    # 按优先级测试：NVENC > AMF > QSV > CPU
    if _check_nvenc_available():
        return 'nvenc'
    elif _check_amf_available():
        return 'amf'
    elif _check_qsv_available():
        return 'qsv'
    else:
        return 'cpu'


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
    transition: str = "none"  # 转场效果
    transition_duration: float = 0.5  # 转场时长（秒）
    audio_fade: bool = True  # 音频淡入淡出
    audio_fade_duration: float = 0.5  # 音频淡入淡出时长（秒）
    max_workers: int = 2  # 并行合成线程数
    overwrite_existing: bool = True  # 是否覆盖已存在的文件


def _get_transition_filter(transition: str, duration: float, idx: int, offset: float) -> str:
    """生成转场滤镜"""
    if transition == "none":
        return ""

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
        "diag_bl": "diagbl",
        "diag_br": "diagbr",
    }

    xfade_type = transitions.get(transition, "fade")
    return f"xfade=transition={xfade_type}:duration={duration}:offset={offset}"


def _get_audio_fade_filter(duration: float, fade_in: bool = True, fade_out: bool = True) -> str:
    """生成音频淡入淡出滤镜"""
    filters = []
    if fade_in:
        filters.append(f"afade=t=in:st=0:d={duration}")
    if fade_out:
        # 淡出需要知道总时长，这里先返回淡入部分
        pass
    return ','.join(filters) if filters else None


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
        result = _run_subprocess(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"获取视频时长失败 {video_path}: {e}")
    return 0.0


def _check_audio_streams(video_paths: List[str]) -> bool:
    """检查视频文件是否有音频流"""
    try:
        from .ffmpeg_utils import _find_ffprobe
        ffprobe = _find_ffprobe()
        cmd = [
            ffprobe, '-v', 'error',
            '-select_streams', 'a',
            '-show_entries', 'stream=codec_type',
            '-of', 'csv=p=0',
            video_paths[0]
        ]
        result = _run_subprocess(cmd, capture_output=True, text=True, timeout=30)
        return 'audio' in result.stdout
    except Exception as e:
        logger.warning(f"检查音频流失败: {e}")
    return False


def _get_encoder_cmd(config: MergeConfig) -> list:
    """获取编码器命令参数"""
    hw_accel = config.hardware_accel

    # 自动选择最佳编码器
    if hw_accel == "auto":
        hw_accel = get_best_encoder()
        logger.info(f"自动选择编码器: {hw_accel}")

    cmd = []

    if hw_accel == "nvenc" and _check_nvenc_available():
        # NVIDIA NVENC
        if config.codec == 'h265':
            cmd.extend(['-c:v', 'hevc_nvenc'])
        else:
            cmd.extend(['-c:v', 'h264_nvenc'])

        quality_map = {"low": "30", "medium": "25", "high": "20"}
        cq = quality_map.get(config.quality, "25")
        cmd.extend(['-cq', cq, '-preset', 'medium'])
        logger.info("使用NVIDIA NVENC编码")

    elif hw_accel == "amf" and _check_amf_available():
        # AMD AMF
        if config.codec == 'h265':
            cmd.extend(['-c:v', 'hevc_amf'])
        else:
            cmd.extend(['-c:v', 'h264_amf'])

        quality_map = {"low": "30", "medium": "25", "high": "20"}
        quality = quality_map.get(config.quality, "25")
        cmd.extend(['-quality', 'balanced', '-rc', 'cqp', '-qp_p', quality, '-qp_i', quality])
        logger.info("使用AMD AMF编码")

    elif hw_accel == "qsv" and _check_qsv_available():
        # Intel QSV
        if config.codec == 'h265':
            cmd.extend(['-c:v', 'hevc_qsv'])
        else:
            cmd.extend(['-c:v', 'h264_qsv'])

        quality_map = {"low": "30", "medium": "25", "high": "20"}
        quality = quality_map.get(config.quality, "25")
        cmd.extend(['-global_quality', quality, '-preset', 'medium'])
        logger.info("使用Intel QSV编码")

    else:
        # CPU编码（默认）
        if config.codec == 'h265':
            cmd.extend(['-c:v', 'libx265'])
        else:
            cmd.extend(['-c:v', 'libx264'])

        quality_map = {"low": "28", "medium": "23", "high": "18"}
        crf = quality_map.get(config.quality, "23")
        cmd.extend(['-crf', crf, '-preset', 'medium'])
        logger.info("使用CPU编码")

    # 关键：指定像素格式为yuv420p，确保兼容性
    cmd.extend(['-pix_fmt', 'yuv420p'])
    cmd.extend(['-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart'])
    return cmd


def _generate_output_path(config: MergeConfig, idx: int, combo: List[VideoInfo]) -> str:
    """生成输出文件路径，处理文件名冲突"""
    file_name = f"{config.file_prefix}_{idx + 1:03d}.mp4"

    if config.output_dir:
        output_path = os.path.join(config.output_dir, file_name)
    else:
        output_path = file_name

    # 处理文件名冲突
    if not config.overwrite_existing and os.path.exists(output_path):
        base, ext = os.path.splitext(output_path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        output_path = f"{base}_{counter}{ext}"

    return output_path


def merge_videos_concat(
    video_paths: List[str],
    output_path: str,
    config: MergeConfig,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Tuple[bool, str]:
    """
    使用FFmpeg concat方式合并视频（支持音频淡入淡出）

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
            creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_msg = stderr[-300:] if stderr else "未知错误"
            return False, f"FFmpeg错误: {error_msg}"

        if not os.path.exists(output_path):
            return False, "输出文件未生成"

        # 如果启用音频淡入淡出，单独处理音频
        if config.audio_fade:
            _apply_audio_fade(output_path, config)

        if progress_callback:
            progress_callback(1.0, "concat合并完成")

        return True, "成功"

    except Exception as e:
        logger.error(f"concat合并异常: {e}")
        return False, f"异常: {str(e)}"
    finally:
        if filelist_path and os.path.exists(filelist_path):
            try:
                os.unlink(filelist_path)
            except:
                pass


def _apply_audio_fade(video_path: str, config: MergeConfig):
    """对已合成的视频应用音频淡入淡出"""
    ffmpeg = _find_ffmpeg()
    temp_output = video_path + ".temp.mp4"

    try:
        duration = _get_video_duration(video_path)
        if duration <= 0:
            return

        fade_duration = min(config.audio_fade_duration, duration / 4)

        # 构建音频淡入淡出滤镜
        audio_filter = f"afade=t=in:st=0:d={fade_duration},afade=t=out:st={duration - fade_duration}:d={fade_duration}"

        cmd = [
            ffmpeg, '-y',
            '-i', video_path,
            '-c:v', 'copy',
            '-af', audio_filter,
            '-c:a', 'aac',
            '-b:a', '128k',
            temp_output
        ]

        result = _run_subprocess(cmd, capture_output=True, timeout=300)

        if result.returncode == 0 and os.path.exists(temp_output):
            os.replace(temp_output, video_path)
            logger.info(f"音频淡入淡出已应用: {video_path}")
        else:
            logger.warning(f"音频淡入淡出应用失败")

    except Exception as e:
        logger.error(f"音频淡入淡出异常: {e}")
    finally:
        if os.path.exists(temp_output):
            try:
                os.unlink(temp_output)
            except:
                pass


def merge_videos_filter_complex(
    video_paths: List[str],
    output_path: str,
    config: MergeConfig,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Tuple[bool, str]:
    """
    使用FFmpeg filter_complex方式合并视频（支持转场和音频淡入淡出）

    Returns:
        (是否成功, 错误信息)
    """
    if not video_paths:
        return False, "没有视频文件"

    ffmpeg = _find_ffmpeg()
    n = len(video_paths)
    has_transition = config.transition != "none" and n >= 2
    has_audio_fade = config.audio_fade and n >= 2

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
                durations.append(dur if dur > 0 else 3.0)

        for i in range(n):
            # 视频处理：统一分辨率和帧率
            video_filters.append(
                f"[{i}:v]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
                f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,"
                f"setpts=PTS-STARTPTS,fps=25[v{i}]"
            )
            # 音频处理
            if has_audio:
                if has_audio_fade:
                    # 添加音频淡入效果
                    fade_duration = min(config.audio_fade_duration, durations[i] / 4 if has_transition else 1.0)
                    audio_filters.append(f"[{i}:a]aresample=44100,asetpts=PTS-STARTPTS,afade=t=in:st=0:d={fade_duration}[a{i}]")
                else:
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

            # 音频处理
            if has_audio:
                if has_audio_fade:
                    # 使用acrossfade实现音频交叉淡入淡出
                    for i in range(1, n):
                        if i == 1:
                            audio_chain = f"[a0][a1]acrossfade=d={transition_duration}[at{i}]"
                        else:
                            audio_chain = f"[at{i-1}][a{i}]acrossfade=d={transition_duration}[at{i}]"
                        audio_filters.append(audio_chain)
                    final_audio = f"[at{n-1}]"
                else:
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
            creationflags=CREATE_NO_WINDOW if os.name == 'nt' else 0
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
        logger.error(f"filter_complex合并异常: {e}")
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
    has_audio_fade = config.audio_fade

    # 选择合并方式
    if has_transition or has_audio_fade:
        # 有转场或音频淡入淡出，必须使用filter_complex
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

    # 如果失败，尝试回退方案
    if not success:
        # 检查是否是NVENC导致的失败
        if config.hardware_accel != "cpu" and "Invalid argument" in msg:
            if progress_callback:
                progress_callback(0, "显卡编码失败，尝试使用CPU编码...")
            # 回退到CPU编码
            config_cpu = MergeConfig(
                output_dir=config.output_dir,
                file_prefix=config.file_prefix,
                resolution=config.resolution,
                fps=config.fps,
                codec=config.codec,
                quality=config.quality,
                hardware_accel="cpu",
                transition=config.transition,
                transition_duration=config.transition_duration,
                audio_fade=config.audio_fade,
                audio_fade_duration=config.audio_fade_duration,
                max_workers=config.max_workers,
                overwrite_existing=config.overwrite_existing
            )
            # 重新选择合并方式
            if has_transition or has_audio_fade:
                success, msg = merge_videos_filter_complex(video_paths, output_path, config_cpu, progress_callback)
            elif format_consistent and not need_preprocess:
                success, msg = merge_videos_concat(video_paths, output_path, config_cpu, progress_callback)
            else:
                success, msg = merge_videos_filter_complex(video_paths, output_path, config_cpu, progress_callback)

    # 如果还是失败，尝试去掉特效
    if not success:
        if progress_callback:
            progress_callback(0, f"尝试简化合成...")

        if has_transition or has_audio_fade:
            # 转场/音频淡入淡出失败，尝试不使用
            config_no_effects = MergeConfig(
                output_dir=config.output_dir,
                file_prefix=config.file_prefix,
                resolution=config.resolution,
                fps=config.fps,
                codec=config.codec,
                quality=config.quality,
                hardware_accel=config.hardware_accel,
                transition="none",
                audio_fade=False
            )
            success, msg = merge_videos_concat(video_paths, output_path, config_no_effects, progress_callback)
        elif format_consistent and not need_preprocess:
            success, msg = merge_videos_filter_complex(video_paths, output_path, config, progress_callback)
        else:
            success, msg = merge_videos_concat(video_paths, output_path, config, progress_callback)

    return success, msg


def _merge_single_combo(idx: int, combo: List[VideoInfo], config: MergeConfig,
                        total: int, progress_callback: Optional[Callable] = None) -> Tuple[int, bool, str, str]:
    """合成单个组合（用于多线程）"""
    output_path = _generate_output_path(config, idx, combo)

    def local_progress(progress, status):
        if progress_callback:
            progress_callback(idx + 1, total, progress, status)

    # 显示当前合成信息
    video_names = [v.视频文件名称[:20] for v in combo]
    if progress_callback:
        progress_callback(idx + 1, total, 0, f"准备: {' + '.join(video_names)}")

    # 检查视频文件
    for v in combo:
        if not os.path.exists(v.视频路径):
            error_msg = f"文件不存在: {v.视频文件名称}"
            return idx, False, output_path, error_msg

    # 合并视频
    try:
        success, error_msg = merge_videos(combo, output_path, config, local_progress)
    except Exception as e:
        success, error_msg = False, f"合成异常: {str(e)}"

    if success and os.path.exists(output_path):
        return idx, True, output_path, "成功"
    else:
        return idx, False, output_path, error_msg


def batch_merge_videos(
    combinations: List[List[VideoInfo]],
    config: MergeConfig,
    progress_callback: Optional[Callable[[int, int, float, str], None]] = None
) -> Tuple[int, int, List[str], List[str]]:
    """
    批量合并视频（支持多线程并行）

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

    # 确定线程数（不超过组合数和CPU核心数）
    max_workers = min(config.max_workers, total, os.cpu_count() or 1)
    max_workers = max(1, max_workers)  # 至少1个线程

    logger.info(f"开始批量合成: {total}个组合, {max_workers}个并行线程")

    if max_workers <= 1:
        # 单线程模式
        for idx, combo in enumerate(combinations):
            idx, success, output_path, error_msg = _merge_single_combo(
                idx, combo, config, total, progress_callback
            )

            if success:
                success_count += 1
                output_files.append(output_path)
                if progress_callback:
                    progress_callback(idx + 1, total, 1.0, f"成功: {os.path.basename(output_path)}")
            else:
                fail_count += 1
                fail_reasons.append(f"{os.path.basename(output_path)}: {error_msg}")
                if progress_callback:
                    progress_callback(idx + 1, total, 0, f"失败: {error_msg}")
    else:
        # 多线程模式
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            futures = []
            for idx, combo in enumerate(combinations):
                future = executor.submit(
                    _merge_single_combo,
                    idx, combo, config, total, progress_callback
                )
                futures.append(future)

            # 等待所有任务完成
            for future in as_completed(futures):
                try:
                    idx, success, output_path, error_msg = future.result()

                    if success:
                        success_count += 1
                        output_files.append(output_path)
                        if progress_callback:
                            progress_callback(idx + 1, total, 1.0, f"成功: {os.path.basename(output_path)}")
                    else:
                        fail_count += 1
                        fail_reasons.append(f"{os.path.basename(output_path)}: {error_msg}")
                        if progress_callback:
                            progress_callback(idx + 1, total, 0, f"失败: {error_msg}")
                except Exception as e:
                    fail_count += 1
                    fail_reasons.append(f"线程异常: {str(e)}")

    logger.info(f"批量合成完成: 成功{success_count}, 失败{fail_count}")
    return success_count, fail_count, output_files, fail_reasons
