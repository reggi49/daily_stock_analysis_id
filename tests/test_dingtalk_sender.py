import unittest
import json
from unittest.mock import patch, MagicMock
from src.notification_sender.dingtalk_sender import DingtalkSender
from src.config import Config

class TestDingtalkSender(unittest.TestCase):
    def setUp(self):
        self.config = Config()
        self.config.dingtalk_webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=test_token"
        self.config.dingtalk_secret = "test_secret"
        self.sender = DingtalkSender(self.config)

    @patch("src.notification_sender.dingtalk_sender.requests.post")
    def test_send_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_post.return_value = mock_response

        result = self.sender.send_to_dingtalk("Test content", "Test Title")
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        called_url = mock_post.call_args[0][0]
        self.assertIn("timestamp=", called_url)
        self.assertIn("sign=", called_url)

    @patch("src.notification_sender.dingtalk_sender.requests.post")
    def test_send_chunked_long_multibyte_message_payload_size(self, mock_post):
        """Test long multi-byte text and long titles exceeding the 20KB limit, verifying the actually-sent JSON payload byte size strictly respects the limit"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_post.return_value = mock_response

        # Generate extra-long multi-byte content (each CJK char is 3 bytes, generating roughly 30,000 bytes of text)
        long_multibyte_content = "StockReview" * 2500
        # Generate an extremely long title
        long_title = "This is an extremely long title used to test DingTalk robot edge cases with maximum length boundaries" * 10

        result = self.sender.send_to_dingtalk(long_multibyte_content, long_title)
        
        self.assertTrue(result)
        # Should be split into at least 2 requests
        self.assertGreaterEqual(mock_post.call_count, 2)
        
        # Verify the actually-serialized JSON byte size of each request never exceeds DingTalk's 20000-byte limit
        for call in mock_post.call_args_list:
            payload = call.kwargs['json']
            # Simulate the JSON serialization used in actual network transmission (no spaces, UTF-8 encoding)
            payload_bytes = len(json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
            
            # Assert: the entire JSON request body actually sent is <= 20000 bytes
            self.assertLessEqual(payload_bytes, 20000, f"Payload byte size {payload_bytes} exceeds DingTalk 20KB limit!")
            
            # Ensure the title is successfully truncated without losing pagination info
            self.assertLessEqual(len(payload['markdown']['title']), 120)

    @patch("src.notification_sender.dingtalk_sender.requests.post")
    def test_send_api_error(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"errcode": 310000, "errmsg": "invalid token"}
        mock_post.return_value = mock_response

        result = self.sender.send_to_dingtalk("Test content")
        self.assertFalse(result)

    @patch("src.notification_sender.dingtalk_sender.requests.post")
    def test_send_exception(self, mock_post):
        mock_post.side_effect = Exception("Network Error")
        result = self.sender.send_to_dingtalk("Test content")
        self.assertFalse(result)