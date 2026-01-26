import os
import unittest
from unittest.mock import MagicMock, patch
from saga.adapters.sglang_adapter import SGLangAdapter


class TestSGLangAdapter(unittest.TestCase):
    def test_adapter_payload(self):
        adapter = SGLangAdapter("http://example.com")
        payload = adapter.build_payload("hi")
        self.assertEqual(payload["messages"][0]["content"], "hi")

    @patch.dict(os.environ, {"SGLANG_TIMEOUT": "123"})
    def test_timeout_config(self):
        adapter = SGLangAdapter("http://example.com")
        self.assertEqual(adapter.timeout, 123)

    def test_default_timeout(self):
        # Ensure default is 60 or 300 depending on env, but code defaults to 60 if env missing
        # We need to make sure env is clear for this test
        with patch.dict(os.environ, {}, clear=True):
             adapter = SGLangAdapter("http://example.com")
             self.assertEqual(adapter.timeout, 60)

    @patch("urllib.request.urlopen")
    def test_call_timeout(self, mock_urlopen):
        # Mock context manager
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        adapter = SGLangAdapter("http://example.com")
        adapter.timeout = 42 
        
        adapter.call("test prompt")
        
        # Verify urlopen called with timeout=42
        args, kwargs = mock_urlopen.call_args
        self.assertEqual(kwargs["timeout"], 42)
