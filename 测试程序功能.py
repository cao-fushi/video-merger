"""
视频批量合成工具 - 功能测试脚本
在全新Windows系统上运行此脚本测试所有功能
"""
import sys
import os
import subprocess
import tempfile
import json

# 获取exe所在目录
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
    INTERNAL_DIR = os.path.join(BASE_DIR, '_internal')
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    INTERNAL_DIR = os.path.join(BASE_DIR, '_internal') if os.path.exists(os.path.join(BASE_DIR, '_internal')) else BASE_DIR

print("=" * 60)
print("视频批量合成工具 - 功能测试")
print("=" * 60)
print()

# 测试结果记录
test_results = []


def test_result(name, success, message=""):
    """记录测试结果"""
    status = "[PASS]" if success else "[FAIL]"
    test_results.append((name, success, message))
    print(f"  {status} - {name}")
    if message:
        print(f"         {message}")


def run_ffmpeg_cmd(args, timeout=30):
    """运行FFmpeg命令"""
    ffmpeg_path = os.path.join(INTERNAL_DIR, 'imageio_ffmpeg', 'binaries', 'ffmpeg-win-x86_64-v7.1.exe')
    if not os.path.exists(ffmpeg_path):
        # 尝试从PATH查找
        ffmpeg_path = 'ffmpeg'

    try:
        result = subprocess.run(
            [ffmpeg_path] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=0x08000000 if os.name == 'nt' else 0
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def run_ffprobe_cmd(args, timeout=30):
    """运行FFprobe命令"""
    ffprobe_path = os.path.join(INTERNAL_DIR, 'ffprobe.exe')
    if not os.path.exists(ffprobe_path):
        ffprobe_path = 'ffprobe'

    try:
        result = subprocess.run(
            [ffprobe_path] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=0x08000000 if os.name == 'nt' else 0
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


# ============================================
# 测试1：检查必要文件
# ============================================
print("[1/8] 检查必要文件...")

required_files = [
    'ffmpeg-win-x86_64-v7.1.exe',
    'ffprobe.exe',
]

for file in required_files:
    # 检查多个可能的位置
    found = False
    for search_dir in [INTERNAL_DIR, os.path.join(INTERNAL_DIR, 'imageio_ffmpeg', 'binaries')]:
        if os.path.exists(os.path.join(search_dir, file)):
            found = True
            break
    test_result(f"文件: {file}", found)

# ============================================
# 测试2：FFmpeg功能
# ============================================
print()
print("[2/8] 测试FFmpeg功能...")

# 测试FFmpeg版本
success, stdout, stderr = run_ffmpeg_cmd(['-version'])
test_result("FFmpeg版本检测", success, stdout.split('\n')[0] if success else stderr[:100])

# 测试FFprobe版本
success, stdout, stderr = run_ffprobe_cmd(['-version'])
test_result("FFprobe版本检测", success, stdout.split('\n')[0] if success else stderr[:100])

# ============================================
# 测试3：创建测试视频
# ============================================
print()
print("[3/8] 创建测试视频...")

test_dir = os.path.join(tempfile.gettempdir(), 'video_merger_test')
os.makedirs(test_dir, exist_ok=True)

test_videos = []

# 创建不同分辨率的测试视频
test_configs = [
    ('test_1080p.mp4', '1080x1920', 3),
    ('test_720p.mp4', '720x1280', 3),
    ('test_480p.mp4', '480x640', 2),
]

for filename, resolution, duration in test_configs:
    filepath = os.path.join(test_dir, filename)
    success, _, stderr = run_ffmpeg_cmd([
        '-y', '-f', 'lavfi', '-i', f'color=c=red:s={resolution}:d={duration}:r=25',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        filepath
    ])
    test_result(f"创建 {filename} ({resolution})", success and os.path.exists(filepath))
    if success:
        test_videos.append(filepath)

# ============================================
# 测试4：视频信息获取
# ============================================
print()
print("[4/8] 测试视频信息获取...")

for video_path in test_videos:
    if os.path.exists(video_path):
        success, stdout, stderr = run_ffprobe_cmd([
            '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams',
            video_path
        ])
        if success:
            try:
                data = json.loads(stdout)
                video_stream = None
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        video_stream = stream
                        break
                if video_stream:
                    width = video_stream.get('width', 0)
                    height = video_stream.get('height', 0)
                    test_result(f"获取信息: {os.path.basename(video_path)}", True, f"{width}x{height}")
                else:
                    test_result(f"获取信息: {os.path.basename(video_path)}", False, "未找到视频流")
            except json.JSONDecodeError:
                test_result(f"获取信息: {os.path.basename(video_path)}", False, "JSON解析失败")
        else:
            test_result(f"获取信息: {os.path.basename(video_path)}", False, stderr[:100])

# ============================================
# 测试5：视频合并（concat方式）
# ============================================
print()
print("[5/8] 测试视频合并（concat方式）...")

if len(test_videos) >= 2:
    concat_output = os.path.join(test_dir, 'concat_output.mp4')

    # 创建文件列表
    filelist_path = os.path.join(test_dir, 'filelist.txt')
    with open(filelist_path, 'w') as f:
        for v in test_videos[:2]:
            f.write(f"file '{v.replace(chr(92), '/')}'\n")

    success, _, stderr = run_ffmpeg_cmd([
        '-y', '-f', 'concat', '-safe', '0', '-i', filelist_path,
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        concat_output
    ])
    test_result("concat合并", success and os.path.exists(concat_output), f"输出: {os.path.getsize(concat_output) if os.path.exists(concat_output) else 0} bytes")
else:
    test_result("concat合并", False, "测试视频不足")

# ============================================
# 测试6：视频合并（filter_complex方式）
# ============================================
print()
print("[6/8] 测试视频合并（filter_complex方式）...")

if len(test_videos) >= 2:
    filter_output = os.path.join(test_dir, 'filter_output.mp4')

    success, _, stderr = run_ffmpeg_cmd([
        '-y',
        '-i', test_videos[0],
        '-i', test_videos[1],
        '-filter_complex',
        '[0:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2[v0];[1:v]scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2[v1];[v0][v1]concat=n=2:v=1:a=0[outv]',
        '-map', '[outv]',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        filter_output
    ])
    test_result("filter_complex合并", success and os.path.exists(filter_output), f"输出: {os.path.getsize(filter_output) if os.path.exists(filter_output) else 0} bytes")
else:
    test_result("filter_complex合并", False, "测试视频不足")

# ============================================
# 测试7：转场效果
# ============================================
print()
print("[7/8] 测试转场效果（xfade）...")

if len(test_videos) >= 2:
    xfade_output = os.path.join(test_dir, 'xfade_output.mp4')

    success, _, stderr = run_ffmpeg_cmd([
        '-y',
        '-i', test_videos[0],
        '-i', test_videos[1],
        '-filter_complex',
        '[0:v]scale=720:1280[v0];[1:v]scale=720:1280[v1];[v0][v1]xfade=transition=fade:duration=0.5:offset=2.5[outv]',
        '-map', '[outv]',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
        xfade_output
    ])
    test_result("xfade转场", success and os.path.exists(xfade_output), f"输出: {os.path.getsize(xfade_output) if os.path.exists(xfade_output) else 0} bytes")
else:
    test_result("xfade转场", False, "测试视频不足")

# ============================================
# 测试8：NVENC硬件加速
# ============================================
print()
print("[8/8] 测试NVENC硬件加速...")

success, stdout, stderr = run_ffmpeg_cmd(['-encoders'])
if success and 'h264_nvenc' in stdout:
    # 测试NVENC编码
    nvenc_output = os.path.join(test_dir, 'nvenc_output.mp4')
    success, _, stderr = run_ffmpeg_cmd([
        '-y', '-f', 'lavfi', '-i', 'color=c=blue:s=320x240:d=2:r=25',
        '-c:v', 'h264_nvenc', '-cq', '25',
        nvenc_output
    ])
    test_result("NVENC编码", success and os.path.exists(nvenc_output))
else:
    test_result("NVENC编码", False, "NVENC不可用（需要NVIDIA显卡）")

# ============================================
# 清理测试文件
# ============================================
print()
print("清理测试文件...")
try:
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    print("  已清理")
except:
    print("  清理失败，可手动删除: " + test_dir)

# ============================================
# 测试结果汇总
# ============================================
print()
print("=" * 60)
print("测试结果汇总")
print("=" * 60)

passed = sum(1 for _, success, _ in test_results if success)
failed = sum(1 for _, success, _ in test_results if not success)

print(f"  通过: {passed}")
print(f"  失败: {failed}")
print(f"  总计: {len(test_results)}")

if failed > 0:
    print()
    print("失败的测试:")
    for name, success, message in test_results:
        if not success:
            print(f"  - {name}: {message}")

print()
if failed == 0:
    print("[OK] 所有测试通过！程序可以在当前系统上正常运行。")
else:
    print("[!] 部分测试失败，请检查相关功能。")

print()
print("=" * 60)
input("按回车键退出...")
