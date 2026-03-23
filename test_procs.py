import unittest

from monitor import Monitor


class ProcessTests(unittest.TestCase):
    def test_mock_process_list_honors_limit_and_shape(self):
        procs = Monitor(mock=True).get_process_list(limit=5)

        self.assertEqual(len(procs), 5)
        for proc in procs:
            self.assertIn("pid", proc)
            self.assertIn("name", proc)
            self.assertIn("cpu", proc)
            self.assertIn("mem", proc)

    def test_real_process_list_returns_no_more_than_limit(self):
        procs = Monitor().get_process_list(limit=3)

        self.assertLessEqual(len(procs), 3)
        for proc in procs:
            self.assertTrue("error" in proc or {"pid", "name", "cpu", "mem"} <= proc.keys())


if __name__ == "__main__":
    unittest.main()
