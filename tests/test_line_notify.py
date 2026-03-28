"""Tests for line_notify module."""

from unittest.mock import patch, MagicMock

import pytest

from line_notify import send_message, send_risk_alert, send_timeout_alert


class TestSendMessage:
    @patch("line_notify.requests.post")
    def test_sends_push_message(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        send_message("Hello")
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["messages"][0]["text"] == "Hello"


class TestSendRiskAlert:
    @patch("line_notify.requests.post")
    def test_format_single_reason(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        send_risk_alert("2026-03-28 02:15:00 JST", ["深夜帯の解錠"], battery=85)
        payload = mock_post.call_args.kwargs["json"]
        text = payload["messages"][0]["text"]
        assert "🚨" in text
        assert "深夜帯の解錠" in text
        assert "85%" in text

    @patch("line_notify.requests.post")
    def test_format_multiple_reasons(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        send_risk_alert("2026-03-28 02:15:00 JST", ["理由A", "理由B"])
        text = mock_post.call_args.kwargs["json"]["messages"][0]["text"]
        assert "理由A" in text
        assert "理由B" in text

    @patch("line_notify.requests.post")
    def test_no_battery(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        send_risk_alert("2026-03-28 02:15:00 JST", ["理由"], battery=None)
        text = mock_post.call_args.kwargs["json"]["messages"][0]["text"]
        assert "バッテリー" not in text


class TestSendTimeoutAlert:
    @patch("line_notify.requests.post")
    def test_format_timeout(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        send_timeout_alert(elapsed_min=150, battery=60)
        text = mock_post.call_args.kwargs["json"]["messages"][0]["text"]
        assert "150分" in text
        assert "60%" in text
        assert "⚠️" in text
