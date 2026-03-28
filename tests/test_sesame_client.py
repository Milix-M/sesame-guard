"""Tests for sesame_client module."""

from unittest.mock import patch, MagicMock

import pytest

from sesame_client import get_sesames, get_sesame_status


class TestGetSesames:
    @patch("sesame_client.requests.get")
    def test_returns_device_list(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"device_id": "abc-123", "serial": "S1", "nickname": "Front door"}
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_sesames("test_token")
        assert len(result) == 1
        assert result[0]["nickname"] == "Front door"
        mock_get.assert_called_once()

    @patch("sesame_client.requests.get")
    def test_passes_auth_header(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        get_sesames("my_token_123")
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["headers"]["Authorization"] == "my_token_123"


class TestGetSesameStatus:
    @patch("sesame_client.requests.get")
    def test_returns_status(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"locked": True, "battery": 85, "responsive": True}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_sesame_status("token", "device-123")
        assert result["locked"] is True
        assert result["battery"] == 85

    @patch("sesame_client.requests.get")
    def test_unlocked_status(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"locked": False, "battery": 50, "responsive": True}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = get_sesame_status("token", "device-123")
        assert result["locked"] is False
