import tempfile
import unittest
from pathlib import Path

from providers.codex import CodexProvider
from providers.models import make_message, make_tool_result, make_tool_use


class ProviderModelTests(unittest.TestCase):
    def test_make_message_includes_stable_defaults(self):
        message = make_message(role="assistant", content="hello", timestamp="2026-04-24T10:00:00Z")

        self.assertEqual(message["role"], "assistant")
        self.assertEqual(message["content"], "hello")
        self.assertEqual(message["thinking"], "")
        self.assertEqual(message["tool_uses"], [])
        self.assertEqual(message["tool_results"], [])
        self.assertEqual(message["model"], "")
        self.assertEqual(message["usage"], {})
        self.assertEqual(message["timestamp"], "2026-04-24T10:00:00Z")
        self.assertEqual(message["uuid"], "")
        self.assertEqual(message["metadata"], {})

    def test_tool_helpers_include_metadata(self):
        tool = make_tool_use("call-1", "exec_command", {"command": ["pwd"]}, {"provider": "codex"})
        result = make_tool_result("call-1", "ok", False, {"exit_code": 0})

        self.assertEqual(tool["id"], "call-1")
        self.assertEqual(tool["name"], "exec_command")
        self.assertEqual(tool["input"], {"command": ["pwd"]})
        self.assertEqual(tool["metadata"], {"provider": "codex"})
        self.assertEqual(result["tool_use_id"], "call-1")
        self.assertEqual(result["content"], "ok")
        self.assertFalse(result["is_error"])
        self.assertEqual(result["metadata"], {"exit_code": 0})


class CodexProviderAvailabilityTests(unittest.TestCase):
    def test_provider_unavailable_without_state_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = CodexProvider(root=Path(tmp))
            self.assertFalse(provider.available())


if __name__ == "__main__":
    unittest.main()
