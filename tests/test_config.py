"""Tests for config module defaults."""

import os
from unittest.mock import patch

import pytest


class TestConfigDefaults:
    def test_default_values(self):
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to pick up clean env
            import importlib
            import config
            importlib.reload(config)

            assert config.RISK_NIGHT_START == 2
            assert config.RISK_NIGHT_END == 5
            assert config.RISK_RAPID_THRESHOLD_SEC == 300
            assert config.RISK_RAPID_COUNT == 3
            assert config.RISK_UNLOCK_TIMEOUT_MIN == 120
            assert config.RISK_COOLDOWN_MIN == 30
            assert config.RISK_ANOMALY_SIGMA == 2.0
            assert config.POLL_INTERVAL_SEC == 60

    def test_env_override(self):
        env = {
            "RISK_NIGHT_START": "1",
            "RISK_COOLDOWN_MIN": "60",
            "RISK_ANOMALY_SIGMA": "2.5",
        }
        with patch.dict(os.environ, env, clear=False):
            import importlib
            import config
            importlib.reload(config)

            assert config.RISK_NIGHT_START == 1
            assert config.RISK_COOLDOWN_MIN == 60
            assert config.RISK_ANOMALY_SIGMA == 2.5
