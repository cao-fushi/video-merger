@echo off
echo 正在启动视频批量合成工具...
echo.
echo 请确保已安装以下依赖:
echo   - Python 3.10+
echo   - PyQt5: pip install PyQt5
echo   - FFmpeg: https://ffmpeg.org/download.html
echo.
cd /d "%~dp0"
python -m video_merger.main
pause
