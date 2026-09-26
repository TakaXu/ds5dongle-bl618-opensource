"""检查锁定的构建依赖，输出版本差异；不会下载、修改或刷写。"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    lock = json.loads((ROOT / "tools/build-dependencies.lock.json").read_text(encoding="utf-8"))
    errors = []
    for item in lock["repositories"]:
        path = ROOT / item["path"]
        result = subprocess.run(["git", "-c", f"safe.directory={path.as_posix()}",
                                 "-C", str(path), "rev-parse", "HEAD"],
                                capture_output=True, text=True)
        if result.returncode or result.stdout.strip() != item["commit"]:
            errors.append(f"{item['path']}: 缺失或提交不匹配")
        else:
            dirty = subprocess.run(["git", "-c", f"safe.directory={path.as_posix()}",
                                    "-C", str(path), "status", "--porcelain", "--untracked-files=no"],
                                   capture_output=True, text=True)
            if dirty.returncode or dirty.stdout.strip():
                errors.append(f"{item['path']}: 存在跟踪文件修改或无法检查")
    for item in lock["files"]:
        path = ROOT / item["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            errors.append(f"{item['path']}: 文件缺失或哈希不匹配")
    print(json.dumps({"passed": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
