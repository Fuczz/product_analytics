"""Cấu hình chung cho toàn bộ pipeline."""
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

SEED = 42
N_USERS = 1500
START_DATE = "2026-08-01"
N_DAYS = 60                 # 60 ngày dữ liệu
DROP_START_DAY = 52         # từ ngày này engagement bị giảm bất thường (giả lập sự cố)
DROP_RATIO = 0.55           # giảm ~55% hoạt động của nhóm Android

# Event schema (đây cũng là "SDK/event schema mẫu" của đề tài)
EVENT_SCHEMA = {
    "required": ["event_id", "user_id", "event_name", "timestamp", "platform"],
    "allowed_events": [
        "app_open", "view_product", "search", "add_to_cart",
        "checkout_start", "purchase", "share", "review",
    ],
    "allowed_platforms": ["android", "ios", "web"],
}

SESSION_GAP_MINUTES = 30    # im lặng > 30' => bắt đầu session mới
FUNNEL_STEPS = ["app_open", "view_product", "add_to_cart", "checkout_start", "purchase"]
N_CLUSTERS = 3   # chọn theo silhouette (k=3 cao nhất trên dữ liệu demo)
