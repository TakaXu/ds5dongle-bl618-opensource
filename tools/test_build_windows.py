"""隔离模拟 make，检查构建失败不会被包装脚本误报成功。"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MAKE = r'''@echo off
echo %* %FORCE_FS%>>calls.txt
if "%1"=="clean" exit /b %CLEAN_RC%
if "%FAIL_FS%"=="1" if "%FORCE_FS%"=="1" exit /b 7
if "%FAIL_HS%"=="1" if "%FORCE_FS%"=="" exit /b 8
if "%MISSING%"=="1" exit /b 0
if not exist build\build_out mkdir build\build_out
for %%F in (ds5dongle_bl618_bl616.bin boot2_bl616_isp_release_v8.1.8.bin partition.bin) do echo test>build\build_out\%%F
exit /b 0
'''


@unittest.skipUnless(os.name == "nt", "仅检查 Windows 批处理")
class BuildTests(unittest.TestCase):
    def run_build(self, action="build", **overrides):
        # 临时目录与真实工程完全隔离，模拟命令不会接触设备。
        with tempfile.TemporaryDirectory(prefix="ds5-build-test-") as directory:
            root = Path(directory)
            shutil.copyfile(ROOT / "build_windows.bat", root / "build_windows.bat")
            sdk = root / "sdk"
            (sdk / "tools/make").mkdir(parents=True)
            (sdk / "project.build").touch()
            (sdk / "tools/make/make.cmd").write_text(MAKE, encoding="ascii")
            gcc = root / "gcc/bin"
            gcc.mkdir(parents=True)
            (gcc / "riscv64-unknown-elf-gcc.exe").touch()
            (root / "build").mkdir()
            env = os.environ.copy()
            env.update(BL_SDK_BASE=str(sdk), TOOLCHAIN_PATH=str(gcc.parent),
                       BOARD_TYPE="lctech616", USB_SPEED="fs", CLEAN_RC="0",
                       FAIL_FS="0", FAIL_HS="0", MISSING="0")
            env.update(overrides)
            result = subprocess.run(["cmd", "/d", "/c", "build_windows.bat", action],
                                    cwd=root, env=env, capture_output=True, text=True,
                                    errors="replace", timeout=20)
            calls = (root / "calls.txt").read_text() if (root / "calls.txt").exists() else ""
            files = [p.name for p in (root / "firmware/lctech616").glob("*.bin")]
            return result.returncode, result.stdout, calls, files

    def test_success_both(self):
        rc, output, calls, files = self.run_build("both")
        self.assertEqual(rc, 0, output)
        self.assertIn("Done.", output)
        self.assertIn("ds5dongle-lctech616.bin", files)
        self.assertIn("ds5dongle-lctech616-hs.bin", files)
        self.assertIn("clean", calls)

    def test_failures_never_succeed(self):
        for action, values in [("build", {"FAIL_FS": "1"}),
                               ("both", {"FAIL_FS": "1"}),
                               ("both", {"FAIL_HS": "1"}),
                               ("clean", {"CLEAN_RC": "9"}),
                               ("rebuild", {"CLEAN_RC": "9"}),
                               ("build", {"MISSING": "1"}),
                               ("build", {"BOARD_TYPE": "typo"}),
                               ("build", {"USB_SPEED": "typo"}),
                               ("typo", {})]:
            with self.subTest(action=action, values=values):
                rc, output, calls, files = self.run_build(action, **values)
                self.assertNotEqual(rc, 0, output)
                self.assertNotIn("Done.", output)
                if values.get("FAIL_FS") == "1":
                    self.assertEqual(len(calls.splitlines()), 1)
                if action == "rebuild":
                    self.assertEqual(calls.strip(), "clean")


if __name__ == "__main__":
    unittest.main(verbosity=2)
