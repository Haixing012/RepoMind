import unittest


class SmokeTests(unittest.TestCase):
    def test_import_main(self):
        import app.main  # noqa: F401


if __name__ == "__main__":
    unittest.main()
