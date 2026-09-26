@echo off
rem SDK 使用 python3 命令；允许指定解释器，默认使用 Windows 的 python。
if defined DS5_PYTHON (
    "%DS5_PYTHON%" %*
) else (
    python %*
)
exit /b %errorlevel%
