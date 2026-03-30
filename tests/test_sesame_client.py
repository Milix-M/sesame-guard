"""Tests for sesame_client module (SESAME Biz API)."""

from unittest.mock import patch, MagicMock

import pytest

from sesame_client import SesameBizClient


@pytest.fixture
def client():
    return SesameBizClient(api_key="test_key", secret_key="aabbccdd")


class TestSesameBizClient:
    def test_init(self, client):
        assert client.api_key == "test_key"
        assert client.secret_key == "aabbccdd"
        assert client._headers["x-api-key"] == "test_key"

    def test_get_sesames_raises(self, client):
        with pytest.raises(NotImplementedError):
            client.get_sesames()

    @patch("sesame_client.requests.get")
    def test_get_status_locked(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "batteryPercentage": 85,
            "batteryVoltage": 5.8,
            "position": 11,
            "CHSesame2Status": "locked",
            "timestamp": 1598523693,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_status("device-123")
        assert result["locked"] is True
        assert result["battery"] == 85
        assert result["status_raw"] == "locked"

    @patch("sesame_client.requests.get")
    def test_get_status_unlocked(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "batteryPercentage": 50,
            "batteryVoltage": 5.5,
            "position": 256,
            "CHSesame2Status": "unlocked",
            "timestamp": 1598523700,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_status("device-123")
        assert result["locked"] is False
        assert result["battery"] == 50

    @patch("sesame_client.requests.get")
    def test_get_history(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"type": 2, "timeStamp": 1597492862.0, "historyTag": "test", "recordID": 255, "parameter": None},
            {"type": 11, "timeStamp": 1597492864.0, "historyTag": None, "recordID": 256, "parameter": None},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_history("device-123", page=0, limit=50)
        assert len(result) == 2
        assert result[0]["type"] == 2

    @patch("sesame_client.requests.get")
    def test_get_unlock_history(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"type": 2, "timeStamp": 1597492900.0, "historyTag": "key1", "recordID": 300, "parameter": None},
            {"type": 11, "timeStamp": 1597492890.0, "historyTag": None, "recordID": 299, "parameter": None},
            {"type": 2, "timeStamp": 1597492862.0, "historyTag": "key2", "recordID": 255, "parameter": None},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = client.get_unlock_history("device-123", since_timestamp=1597492870.0)
        # Only type=2 (unlock) and after timestamp
        assert len(result) == 1
        assert result[0]["historyTag"] == "key1"

    def test_send_command_no_secret_key(self):
        client_no_secret = SesameBizClient(api_key="test")
        with pytest.raises(ValueError, match="secret_key"):
            client_no_secret.send_command("device-123")

    @patch("sesame_client.requests.get")
    def test_auth_header(self, mock_get, client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"CHSesame2Status": "locked", "batteryPercentage": 100, "batteryVoltage": 5.8, "position": 11, "timestamp": 0}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        client.get_status("device-123")
        call_kwargs = mock_get.call_args
        assert call_kwargs.kwargs["headers"]["x-api-key"] == "test_key"
