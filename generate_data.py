"""Sinh dữ liệu event giả lập (có chủ đích) để chứng minh thuật toán.

Có 4 'nguyên mẫu' hành vi ẩn (người dùng không biết trước, thuật toán phải tự tìm lại):
  - power_buyer : mở app thường xuyên, mua nhiều
  - browser     : xem nhiều, hiếm khi mua
  - casual      : thỉnh thoảng ghé
  - churned     : dùng đầu kỳ rồi biến mất
Ngoài ra chèn 1 sự cố: từ ngày DROP_START_DAY, nền tảng Android giảm mạnh hoạt động.
"""
import numpy as np
import pandas as pd
import config as C

ARCHETYPES = {
    #               tỉ lệ,  số ngày active/tuần, P(view|open), P(cart|view), P(checkout|cart), P(buy|checkout)
    "power_buyer": (0.15, 5.0, 0.95, 0.55, 0.85, 0.90),
    "browser":     (0.30, 4.0, 0.95, 0.15, 0.40, 0.50),
    "casual":      (0.35, 1.2, 0.70, 0.20, 0.50, 0.60),
    "churned":     (0.20, 3.0, 0.80, 0.25, 0.50, 0.60),
}

def generate_events(seed: int = C.SEED):
    """Trả về (events_df, true_labels). true_labels chỉ dùng để kiểm chứng phân cụm."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp(C.START_DATE)
    names = list(ARCHETYPES)
    probs = [ARCHETYPES[n][0] for n in names]

    rows = []
    labels = {}
    eid = 0
    for uid in range(1, C.N_USERS + 1):
        arche = rng.choice(names, p=probs)
        labels[uid] = arche
        _, days_per_week, p_view, p_cart, p_chk, p_buy = ARCHETYPES[arche]
        platform = rng.choice(C.EVENT_SCHEMA["allowed_platforms"], p=[0.5, 0.3, 0.2])
        join_day = int(rng.integers(0, 15))
        last_active_day = C.N_DAYS if arche != "churned" else int(rng.integers(15, 30))

        for day in range(join_day, last_active_day):
            p_active = days_per_week / 7
            # sự cố: Android giảm mạnh cuối kỳ
            if platform == "android" and day >= C.DROP_START_DAY:
                p_active *= (1 - C.DROP_RATIO)
            # hiệu ứng cuối tuần nhẹ (tính mùa vụ theo thứ)
            if (start + pd.Timedelta(days=day)).dayofweek >= 5:
                p_active *= 1.25
            if rng.random() > min(p_active, 1.0):
                continue

            for _ in range(int(rng.integers(1, 3))):          # 1-2 session/ngày
                t = start + pd.Timedelta(days=day, hours=int(rng.integers(7, 23)),
                                         minutes=int(rng.integers(0, 60)))
                def emit(name):
                    nonlocal eid, t
                    eid += 1
                    t = t + pd.Timedelta(seconds=int(rng.integers(5, 120)))
                    rows.append((f"e{eid}", uid, name, t, platform))

                emit("app_open")
                if rng.random() < p_view:
                    for _ in range(int(rng.integers(1, 6))):
                        emit("view_product")
                        if rng.random() < 0.2:
                            emit("search")
                    if rng.random() < p_cart:
                        emit("add_to_cart")
                        if rng.random() < p_chk:
                            emit("checkout_start")
                            if rng.random() < p_buy:
                                emit("purchase")
                                if rng.random() < 0.15:
                                    emit("review")
                if rng.random() < 0.05:
                    emit("share")

    df = pd.DataFrame(rows, columns=["event_id", "user_id", "event_name", "timestamp", "platform"])
    df = df.sort_values(["user_id", "timestamp"]).reset_index(drop=True)
    return df, pd.Series(labels, name="true_archetype")

if __name__ == "__main__":
    df, labels = generate_events()
    labels.to_csv(C.OUTPUT_DIR / "true_labels.csv")
    df.to_csv(C.OUTPUT_DIR / "events.csv", index=False)
    print(f"Đã sinh {len(df):,} event của {df.user_id.nunique():,} user -> output/events.csv")
