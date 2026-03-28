import os

# SESAME API
SESAME_API_TOKEN = os.environ.get("SESAME_API_TOKEN", "")
SESAME_DEVICE_ID = os.environ.get("SESAME_DEVICE_ID", "")
SESAME_API_BASE = "https://api.candyhouse.co/public"

# LINE Messaging API
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "")

# Risk detection
RISK_NIGHT_START = int(os.environ.get("RISK_NIGHT_START", 2))   # 2:00 AM (JST)
RISK_NIGHT_END = int(os.environ.get("RISK_NIGHT_END", 5))       # 5:00 AM (JST)
RISK_RAPID_THRESHOLD_SEC = int(os.environ.get("RISK_RAPID_THRESHOLD_SEC", 300))  # 5 min
RISK_RAPID_COUNT = int(os.environ.get("RISK_RAPID_COUNT", 3))   # 3 unlocks in threshold
RISK_UNLOCK_TIMEOUT_MIN = int(os.environ.get("RISK_UNLOCK_TIMEOUT_MIN", 120))  # 2 hours
RISK_COOLDOWN_MIN = int(os.environ.get("RISK_COOLDOWN_MIN", 30))  # 30 min between alerts
RISK_ANOMALY_SIGMA = float(os.environ.get("RISK_ANOMALY_SIGMA", 2.0))  # 2σ threshold

# Polling
POLL_INTERVAL_SEC = int(os.environ.get("POLL_INTERVAL_SEC", 60))

# Database
DB_PATH = os.environ.get("DB_PATH", "sesame_guard.db")
