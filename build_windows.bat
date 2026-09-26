@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem 本地依赖优先，保留环境变量覆盖与旧版同级 SDK 路径。
if "%BL_SDK_BASE%"=="" (
    if exist "%~dp0bouffalo_sdk_ds5\project.build" (
        set "BL_SDK_BASE=%~dp0bouffalo_sdk_ds5"
    ) else (
        set "BL_SDK_BASE=%~dp0..\bouffalo_sdk"
    )
)
if "%TOOLCHAIN_PATH%"=="" (
    if exist "%~dp0.tools\toolchain_gcc_t-head_windows\bin\riscv64-unknown-elf-gcc.exe" (
        set "TOOLCHAIN_PATH=%~dp0.tools\toolchain_gcc_t-head_windows"
    ) else (
        set "TOOLCHAIN_PATH=%USERPROFILE%\Desktop\toolchain_gcc_t-head_windows"
    )
)
if "%BOARD_TYPE%"=="" set "BOARD_TYPE=lctech616"
if "%USB_SPEED%"=="" set "USB_SPEED=fs"
if "%NUMBER_OF_PROCESSORS%"=="" set "NUMBER_OF_PROCESSORS=8"
set "ACTION=%~1"
if "%ACTION%"=="" set "ACTION=build"

rem 参数写错时明确拒绝，避免把错误板型悄悄编译成默认板型。
if /i not "%BOARD_TYPE%"=="lctech616" if /i not "%BOARD_TYPE%"=="aim61" if /i not "%BOARD_TYPE%"=="m0sdock" (
    echo [ERROR] Unsupported BOARD_TYPE: %BOARD_TYPE%
    exit /b 2
)
if /i not "%USB_SPEED%"=="fs" if /i not "%USB_SPEED%"=="hs" (
    echo [ERROR] Unsupported USB_SPEED: %USB_SPEED%
    exit /b 2
)
if /i not "%ACTION%"=="build" if /i not "%ACTION%"=="rebuild" if /i not "%ACTION%"=="both" if /i not "%ACTION%"=="clean" if /i not "%ACTION%"=="flash" (
    echo [ERROR] Usage: build_windows.bat [build^|rebuild^|both^|clean^|flash [COMx]]
    exit /b 2
)
if not exist "%BL_SDK_BASE%\project.build" (
    echo [ERROR] SDK not found: "%BL_SDK_BASE%"
    exit /b 1
)
if not exist "%TOOLCHAIN_PATH%\bin\riscv64-unknown-elf-gcc.exe" (
    echo [ERROR] Toolchain not found: "%TOOLCHAIN_PATH%"
    exit /b 1
)
set "PATH=%~dp0tools\windows;%TOOLCHAIN_PATH%\bin;%BL_SDK_BASE%\tools\make;%BL_SDK_BASE%\tools\cmake\bin;%BL_SDK_BASE%\tools\ninja;%PATH%"

if /i "%ACTION%"=="clean" (
    call make clean
    if errorlevel 1 goto :failed
    goto :done
)
if /i "%ACTION%"=="flash" (
    set "COMX=%~2"
    if "!COMX!"=="" set "COMX=COM5"
    call make flash COMX=!COMX!
    if errorlevel 1 goto :failed
    goto :done
)
if /i "%ACTION%"=="rebuild" if exist build (
    call make clean
    if errorlevel 1 goto :failed
)
if /i "%ACTION%"=="both" (
    set "USB_SPEED=fs"
    call :build_one
    if errorlevel 1 goto :failed
    set "USB_SPEED=hs"
    call :build_one
    if errorlevel 1 goto :failed
) else (
    call :build_one
    if errorlevel 1 goto :failed
)
goto :done

:build_one
    rem 每次清空板型及 USB 标记，避免 FS/HS 连续构建继承上次参数。
    set "BOARD_LCTECH_616="
    set "BOARD_M0S_DOCK="
    if /i "%BOARD_TYPE%"=="lctech616" set "BOARD_LCTECH_616=1"
    if /i "%BOARD_TYPE%"=="m0sdock" set "BOARD_M0S_DOCK=1"
    set "FORCE_FS="
    set "SPEED_SUFFIX="
    if /i "%USB_SPEED%"=="fs" (set "FORCE_FS=1") else (set "SPEED_SUFFIX=-hs")
    set "BUILD_KEY=%BOARD_TYPE%-%USB_SPEED%"
    set "BOARD_STAMP=build\.board_type"
    if exist "%BOARD_STAMP%" (
        set "PREV_KEY="
        set /p PREV_KEY=<"%BOARD_STAMP%"
        if /i not "!PREV_KEY!"=="%BUILD_KEY%" (
            echo [build] Target changed: !PREV_KEY! to %BUILD_KEY%
            call make clean
            if errorlevel 1 goto :failed
        )
    )
    echo [build] Target: %BUILD_KEY%
    call make -j%NUMBER_OF_PROCESSORS%
    if errorlevel 1 goto :failed
    rem 完整产物检查通过后才复制，失败不能输出 Done 或更新构建标记。
    for %%F in (ds5dongle_bl618_bl616.bin boot2_bl616_isp_release_v8.1.8.bin partition.bin) do (
        if not exist "build\build_out\%%F" (
            echo [ERROR] Missing artifact: build\build_out\%%F
            exit /b 1
        )
    )
    set "OUT_DIR=firmware\%BOARD_TYPE%"
    if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"
    if errorlevel 1 goto :failed
    copy /y "build\build_out\ds5dongle_bl618_bl616.bin" "%OUT_DIR%\ds5dongle-%BOARD_TYPE%%SPEED_SUFFIX%.bin" >nul
    if errorlevel 1 goto :failed
    copy /y "build\build_out\boot2_bl616_isp_release_v8.1.8.bin" "%OUT_DIR%\" >nul
    if errorlevel 1 goto :failed
    copy /y "build\build_out\partition.bin" "%OUT_DIR%\" >nul
    if errorlevel 1 goto :failed
    >"%BOARD_STAMP%" echo %BUILD_KEY%
    if errorlevel 1 goto :failed
    echo [build] Output: %OUT_DIR%\ds5dongle-%BOARD_TYPE%%SPEED_SUFFIX%.bin
    exit /b 0

:done
echo [build] Done.
exit /b 0

:failed
exit /b 1
