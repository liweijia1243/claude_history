import unittest
from unittest.mock import patch

from fastapi import HTTPException

import server


class UnavailableProvider:
    def available(self):
        return False

    def get_stats(self):
        return {"total_commands": 0}

    def get_history(self, page, limit, search, project):
        return {"items": [], "page": page, "limit": limit}

    def list_projects(self):
        return []

    def get_plans(self):
        return []

    def get_recent_sessions(self, limit):
        return [{"limit": limit}]


class LegacyClaudeRouteTests(unittest.TestCase):
    def test_legacy_routes_delegate_to_unavailable_claude_provider(self):
        provider = UnavailableProvider()

        with patch("server.get_provider", return_value=provider):
            self.assertEqual(server.get_stats(), {"total_commands": 0})
            self.assertEqual(
                server.get_history(page=2, limit=10, search=None, project=None),
                {"items": [], "page": 2, "limit": 10},
            )
            self.assertEqual(server.get_projects(), [])
            self.assertEqual(server.get_plans(), [])
            self.assertEqual(server.get_recent_sessions(limit=3), [{"limit": 3}])

    def test_explicit_source_provider_lookup_still_rejects_unavailable_provider(self):
        provider = UnavailableProvider()

        with patch("server.get_provider", return_value=provider):
            with self.assertRaises(HTTPException) as context:
                server.provider_or_404("claude")

        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.detail, "Source not found/unavailable")


if __name__ == "__main__":
    unittest.main()
