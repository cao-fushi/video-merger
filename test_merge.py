"""测试视频合并功能"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from video_merger.core.ffmpeg_utils import _find_ffmpeg, check_ffmpeg_installed
from video_merger.core.video_info import get_video_info
from video_merger.core.video_merger import merge_videos_concat, MergeConfig

def test_ffmpeg():
    """测试FFmpeg是否可用"""
    print("=" * 50)
    print("1. 检查FFmpeg")
    print("=" * 50)

    ffmpeg_path = _find_ffmpeg()
    print(f"FFmpeg路径: {ffmpeg_path}")
    print(f"FFmpeg存在: {os.path.exists(ffmpeg_path)}")
    print(f"FFmpeg已安装: {check_ffmpeg_installed()}")

    # 测试FFmpeg版本
    import subprocess
    try:
        result = subprocess.run([ffmpeg_path, '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"FFmpeg版本: {result.stdout.split(chr(10))[0]}")
        else:
            print(f"FFmpeg执行失败: {result.stderr}")
    except Exception as e:
        print(f"FFmpeg执行异常: {e}")

    return os.path.exists(ffmpeg_path)


def test_video_info(video_path):
    """测试视频信息获取"""
    print("\n" + "=" * 50)
    print("2. 测试视频信息获取")
    print("=" * 50)

    if not os.path.exists(video_path):
        print(f"视频文件不存在: {video_path}")
        return None

    print(f"视频路径: {video_path}")
    print(f"文件大小: {os.path.getsize(video_path)} bytes")

    info = get_video_info(video_path)
    if info:
        print(f"视频名称: {info.视频文件名称}")
        print(f"视频时长: {info.视频时长}")
        print(f"视频分辨率: {info.视频分辨率}")
        print(f"帧率: {info.帧率信息}")
        print(f"编码器: {info.编码器信息}")
    else:
        print("获取视频信息失败!")

    return info


def test_merge(video1_path, video2_path, output_path):
    """测试视频合并"""
    print("\n" + "=" * 50)
    print("3. 测试视频合并")
    print("=" * 50)

    if not os.path.exists(video1_path):
        print(f"视频1不存在: {video1_path}")
        return False

    if not os.path.exists(video2_path):
        print(f"视频2不存在: {video2_path}")
        return False

    print(f"视频1: {video1_path}")
    print(f"视频2: {video2_path}")
    print(f"输出: {output_path}")

    # 获取视频信息
    info1 = get_video_info(video1_path)
    info2 = get_video_info(video2_path)

    if not info1 or not info2:
        print("无法获取视频信息!")
        return False

    # 创建合并配置
    config = MergeConfig(
        output_dir=os.path.dirname(output_path),
        file_prefix=os.path.splitext(os.path.basename(output_path))[0]
    )

    # 测试concat合并
    print("\n尝试使用concat方式合并...")
    success = merge_videos_concat(
        [video1_path, video2_path],
        output_path,
        config,
        lambda progress, status: print(f"  进度: {progress:.1%} - {status}")
    )

    if success:
        print(f"合并成功! 输出文件: {output_path}")
        print(f"输出文件大小: {os.path.getsize(output_path)} bytes")
    else:
        print("合并失败!")

    return success


def main():
    print("视频合并功能测试")
    print("=" * 50)

    # 测试FFmpeg
    if not test_ffmpeg():
        print("\n错误: FFmpeg不可用!")
        return

    # 提示用户输入测试视频路径
    print("\n请提供测试视频路径:")
    video1 = input("视频1路径 (或按Enter跳过): ").strip().strip('"')
    video2 = input("视频2路径 (或按Enter跳过): ").strip().strip('"')

    if not video1 or not video2:
        print("\n未提供测试视频，跳过合并测试")
        print("\n提示: 你可以使用以下命令手动测试FFmpeg:")
        print(f'  {_find_ffmpeg()} -i "视频1.mp4" -i "视频2.mp4" -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" -map "[outv]" output.mp4')
        return

    # 测试视频信息
    test_video_info(video1)
    test_video_info(video2)

    # 测试合并
    output_dir = os.path.dirname(video1) or "."
    output_path = os.path.join(output_dir, "test_merge_output.mp4")
    test_merge(video1, video2, output_path)


if __name__ == '__main__':
    main()
