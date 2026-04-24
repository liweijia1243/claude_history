import tempfile
import unittest
from pathlib import Path

from providers.claude import ClaudeProvider


class ClaudeProviderModelTests(unittest.TestCase):
    def test_reconstructed_messages_include_normalized_metadata_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = ClaudeProvider(root=Path(tmp))
            conversation = provider._reconstruct_conversation(
                [
                    {
                        "type": "user",
                        "timestamp": "2026-04-24T10:00:00Z",
                        "uuid": "user-1",
                        "message": {"content": "hello"},
                    },
                    {
                        "type": "assistant",
                        "timestamp": "2026-04-24T10:00:01Z",
                        "uuid": "assistant-1",
                        "message": {
                            "model": "claude-sonnet",
                            "usage": {"input_tokens": 1, "output_tokens": 2},
                            "content": [
                                {"type": "text", "text": "hi"},
                                {
                                    "type": "tool_use",
                                    "id": "tool-1",
                                    "name": "Read",
                                    "input": {"file_path": "README.md"},
                                },
                            ],
                        },
                    },
                    {
                        "type": "user",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": "tool-1",
                                    "content": "contents",
                                    "is_error": False,
                                }
                            ]
                        },
                    },
                ]
            )

        self.assertEqual(conversation[0]["metadata"], {})
        self.assertEqual(conversation[0]["tool_uses"], [])
        self.assertEqual(conversation[0]["tool_results"], [])

        assistant = conversation[1]
        self.assertEqual(assistant["metadata"], {})
        self.assertEqual(assistant["tool_uses"][0]["metadata"], {})
        self.assertEqual(assistant["tool_results"][0]["metadata"], {})


if __name__ == "__main__":
    unittest.main()
