import unittest

from server import plan_payload


class ServerContractTests(unittest.TestCase):
    def test_plan_rejects_rooted_windows_paths(self):
        for path in ("/absolute.pdf", r"\absolute.pdf"):
            with self.subTest(path=path):
                status, payload = plan_payload({
                    "input": {"path": path, "bytes": 1},
                    "goal": "inspect",
                })
                self.assertEqual(status, 400)
                self.assertEqual(payload["code"], "INVALID_PATH")


if __name__ == "__main__":
    unittest.main()
