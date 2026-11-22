import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
CREDITS = "credit_id,period_id,asset,amount,status\n"


class LedgerCliTest(unittest.TestCase):
    def run_ledger(self, credits, fills=None):
        return subprocess.run(
            [sys.executable, ROOT / "fee_ledger.py", "--fills",
             fills or ROOT / "examples/fills.csv", "--cashback", credits],
            capture_output=True, text=True, check=False,
        )

    def test_example_agrees_with_readme(self):
        result = self.run_ledger(ROOT / "examples/cashback.csv")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Net trading fee: 0.75 USDT", result.stdout)
        self.assertIn("Effective fee:   0.075%", result.stdout)
        self.assertIn(result.stdout.strip(), (ROOT / "README.md").read_text())

    def test_pending_credits_do_not_reduce_the_fee(self):
        with TemporaryDirectory() as work:
            file = Path(work) / "credits.csv"
            file.write_text(CREDITS + "credit,example-order,USDT,0.25,pending\n")
            result = self.run_ledger(file)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Pending credits: 0.25 USDT", result.stdout)
            self.assertIn("Net trading fee: 1.00 USDT", result.stdout)

    def test_reject_duplicate_or_unmatched_credits(self):
        cases = (
            ("x,other-period,USDT,0.25,posted\n", "has no matching fills"),
            ("x,example-order,USDT,0.25,posted\n" * 2, "duplicate credit_id"),
            ("x,example-order,BNB,0.25,posted\n", "credit asset must be USDT"),
        )
        with TemporaryDirectory() as work:
            file = Path(work) / "credits.csv"
            for rows, error in cases:
                with self.subTest(error=error):
                    file.write_text(CREDITS + rows)
                    result = self.run_ledger(file)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, "")
                    self.assertIn(error, result.stderr)

    def test_no_cashback(self):
        with TemporaryDirectory() as work:
            file = Path(work) / "credits.csv"
            file.write_text(CREDITS)
            result = self.run_ledger(file)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Effective fee:   0.1%", result.stdout)


if __name__ == "__main__":
    unittest.main()
