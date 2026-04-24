import unittest

from providers import get_provider, list_sources


class ProviderRegistryTests(unittest.TestCase):
    def test_list_sources_contains_claude_and_codex(self):
        source_ids = {source["id"] for source in list_sources()}

        self.assertIn("claude", source_ids)
        self.assertIn("codex", source_ids)

    def test_get_provider_returns_registered_providers(self):
        self.assertEqual(get_provider("claude").id, "claude")
        self.assertEqual(get_provider("codex").id, "codex")
        self.assertIsNone(get_provider("missing"))


if __name__ == "__main__":
    unittest.main()
