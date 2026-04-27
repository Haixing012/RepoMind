import unittest
from pathlib import Path

from app.services.git_service import normalize_github_url
from app.services.repository_intelligence import build_tree, search_code


class RepositoryIntelligenceTests(unittest.TestCase):
    def setUp(self):
        self.project_root = Path(__file__).resolve().parents[2]

    def test_normalize_github_url(self):
        self.assertEqual(
            normalize_github_url("git@github.com:OpenAI/openai-python.git"),
            "https://github.com/openai/openai-python",
        )

    def test_build_tree(self):
        tree = build_tree(self.project_root / "frontend")
        self.assertIn("src", tree)
        self.assertIn("package.json", tree)

    def test_search_code(self):
        hits = search_code(self.project_root / "backend", "normalize_github_url")
        self.assertTrue(any(hit["path"] == "app/services/git_service.py" for hit in hits))


if __name__ == "__main__":
    unittest.main()
