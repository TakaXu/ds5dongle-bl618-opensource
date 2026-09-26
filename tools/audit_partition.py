"""只读检查分区布局；通过不代表设备已满足 OTA 恢复条件。需要 Python 3.11+。"""
import argparse
import json
from pathlib import Path
import tomllib


def audit(data, flash_size):
    regions, errors = [], []
    if flash_size <= 0:
        raise ValueError("Flash 容量必须大于零")
    for slot in (0, 1):
        start = data["pt_table"][f"address{slot}"]
        regions.append((f"PT[{slot}]", start, start + 4096))
    for entry in data["pt_entry"]:
        if entry.get("device", 0) != 0:
            errors.append(f"{entry['name']}: 不支持的存储设备")
            continue
        for slot in (0, 1):
            start, size = entry[f"address{slot}"], entry[f"size{slot}"]
            if size < 0:
                errors.append(f"{entry['name']}[{slot}]: 负容量")
            elif size:
                regions.append((f"{entry['name']}[{slot}]", start, start + size))
    for name, start, end in regions:
        if start < 0 or end > flash_size:
            errors.append(f"{name}: 超出 Flash 范围")
        if start % 4096 or end % 4096:
            errors.append(f"{name}: 未按 4 KiB 擦除边界对齐")
    for i, (name, start, end) in enumerate(regions):
        for other, left, right in regions[i + 1:]:
            if max(start, left) < min(end, right):
                errors.append(f"{name} 与 {other} 重叠")
    fw = [e for e in data["pt_entry"] if e["name"] == "FW"]
    if len(fw) != 1 or any(fw[0][f"size{s}"] <= 4096 for s in (0, 1)):
        errors.append("需要唯一且具备两个有效槽位的 FW 分区")
    return {"flash_size_assumed": flash_size, "regions": regions,
            "errors": errors, "layout_checks_passed": not errors,
            "hardware_verified": False, "ota_ready": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("partition", type=Path)
    parser.add_argument("--flash-size", type=lambda value: int(value, 0), required=True)
    args = parser.parse_args()
    with args.partition.open("rb") as stream:
        report = audit(tomllib.load(stream), args.flash_size)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["layout_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
