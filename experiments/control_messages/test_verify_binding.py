"""Regression checks for missing worker evidence and incorrect binding."""
import copy
from pathlib import Path
import tempfile
import unittest

import verify_binding
import json


class BindingVerificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = [json.loads(line) for line in
                       (verify_binding.RESULTS / "native.jsonl").read_text().splitlines()]

    def verify(self, records):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            (target / "native.jsonl").write_text(
                "".join(json.dumps(record) + "\n" for record in records))
            return verify_binding.check(target)

    def test_saved_results(self):
        result = self.verify(self.records)
        self.assertEqual(sum(x["observations"] for x in result.values()), 90)

    def test_missing_worker_is_rejected(self):
        records = copy.deepcopy(self.records)
        records[-1]["first_tuples"].pop()
        with self.assertRaisesRegex(ValueError, "worker observation"):
            self.verify(records)

    def test_duplicate_worker_is_rejected(self):
        records = copy.deepcopy(self.records)
        observations = records[-1]["first_tuples"]
        observations[1] = dict(observations[0])
        with self.assertRaisesRegex(ValueError, "worker observation"):
            self.verify(records)

    def test_stale_bound_value_is_rejected(self):
        records = copy.deepcopy(self.records)
        records[0]["first_tuples"][-1]["bound_K"] = 2
        with self.assertRaisesRegex(ValueError, "wrong K"):
            self.verify(records)

    def test_missing_run_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Missing runs"):
            self.verify(self.records[:-1])

    def test_wrong_filter_output_is_rejected(self):
        records = copy.deepcopy(self.records)
        records[0]["rows"].pop()
        with self.assertRaisesRegex(ValueError, "Wrong Filter output"):
            self.verify(records)


if __name__ == "__main__":
    unittest.main()
