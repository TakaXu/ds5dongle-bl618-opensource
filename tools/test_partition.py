"""覆盖布局边界与现有 mfg 重叠，防止将危险布局当成 OTA 就绪。"""
import copy
from pathlib import Path
import tomllib
import unittest
from audit_partition import audit


class PartitionTests(unittest.TestCase):
    def setUp(self):
        with (Path(__file__).resolve().parents[1] / "firmware/lctech616/partition_cfg_4M_nosec.toml").open("rb") as stream:
            self.data = tomllib.load(stream)

    def test_existing_overlap(self):
        result = audit(self.data, 0x400000)
        self.assertEqual(result["errors"], ["FW[1] 与 mfg[0] 重叠"])
        self.assertFalse(result["ota_ready"])

    def test_boundary_and_overflow(self):
        data = copy.deepcopy(self.data)
        data["pt_entry"] = [e for e in data["pt_entry"] if e["name"] != "mfg"]
        self.assertTrue(audit(data, 0x400000)["layout_checks_passed"])
        self.assertFalse(audit(data, 0x3fffff)["layout_checks_passed"])
        self.assertFalse(audit(data, 0x400000)["ota_ready"])

    def test_partition_table_overlap(self):
        self.data["pt_table"]["address1"] = 0x10000
        self.assertIn("PT[1] 与 FW[0] 重叠", audit(self.data, 0x400000)["errors"])

    def test_missing_second_slot(self):
        next(e for e in self.data["pt_entry"] if e["name"] == "FW")["size1"] = 0
        self.assertFalse(audit(self.data, 0x400000)["layout_checks_passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
