"""Chạy toàn bộ pipeline: sinh data -> validate -> segmentation -> journey -> alert -> AI summary."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import config as C
from generate_data import generate_events
from validation import validate_events
import segmentation as S
import journey as J
import alerting as A
import ai_summary as AI

pd.set_option("display.width", 200); pd.set_option("display.max_columns", 20)

def banner(t): print("\n" + "=" * 8 + f" {t} " + "=" * 8)

def main():
    banner("0. THU THẬP & VALIDATE EVENT")
    raw, true = generate_events()
    # chèn vài event bẩn để chứng minh validation
    dirty = pd.concat([raw, pd.DataFrame([
        {"event_id": "bad1", "user_id": 1, "event_name": "hack_event", "timestamp": "2026-08-02", "platform": "web"},
        {"event_id": "bad2", "user_id": 2, "event_name": "purchase", "timestamp": "not-a-date", "platform": "web"},
        {"event_id": raw.event_id.iloc[0], "user_id": 3, "event_name": "purchase", "timestamp": "2026-08-02", "platform": "ios"},
    ])], ignore_index=True)
    events, errors = validate_events(dirty)
    print(f"Tổng: {len(dirty):,} | hợp lệ: {len(events):,} | bị loại: {len(errors)}")
    print(errors[["event_id", "event_name", "error"]].to_string(index=False))

    banner("1. SEGMENTATION")
    feats = S.build_features(events)
    seg, sil = S.segment_users(feats)
    seg = S.name_segments(seg)
    print("Silhouette theo k:", {k: round(v, 3) for k, v in sil.items()})
    prof = S.profile(seg)
    print(prof)
    # kiểm chứng với nhãn thật (chỉ có trong dữ liệu giả lập)
    check = pd.crosstab(seg.segment, true.reindex(seg.index))
    print("\nĐối chiếu cụm tìm được vs nhóm ẩn thật (dữ liệu giả lập):\n", check)

    banner("2. JOURNEY ANALYSIS")
    e = J.sessionize(events)
    paths = J.session_paths(e)
    print(f"Số session: {len(paths):,}\n")
    print("Top đường đi:\n", J.top_paths(paths).to_string(index=False))
    fun = J.funnel(e)
    print("\nFunnel:\n", fun.to_string(index=False))
    print("\nFunnel theo segment (% session đạt từng bước, tính từ app_open):\n", J.funnel_by_segment(e, seg))
    tm = J.transition_matrix(paths)
    print("\nMa trận chuyển bước (xác suất):\n", tm)

    banner("3. CẢNH BÁO ENGAGEMENT GIẢM BẤT THƯỜNG")
    alerts = A.run_alerts(events)
    for a in alerts:
        print(f"[{a.severity}] {a.date.date()} | {a.metric:6s} | {a.scope:20s} | "
              f"{a.value:.0f} vs baseline {a.baseline:.0f} (-{a.drop_pct}%, z={a.z})")
    if not alerts:
        print("Không có cảnh báo.")

    banner("4. AI TÓM TẮT")
    ctx = AI.build_context(prof, fun, J.top_paths(paths), alerts)
    print(AI.summarize(ctx))

    # --- biểu đồ minh chứng ---
    fig, ax = plt.subplots(1, 3, figsize=(17, 4.5))
    prof["users"].plot.barh(ax=ax[0], color="#4C78A8"); ax[0].set_title("Segmentation: số user/segment")
    ax[1].bar(fun.step, fun.sessions, color="#59A14F"); ax[1].set_title("Funnel (session)")
    ax[1].tick_params(axis="x", rotation=25)
    d = A.daily_metrics(events, by="platform")["dau"].unstack()
    d.plot(ax=ax[2]); ax[2].set_title("DAU theo platform (sự cố ở cuối kỳ)")
    for a in alerts:
        if a.metric == "dau" and a.scope == "toàn hệ thống":
            ax[2].axvline(a.date, color="red", ls="--", alpha=.6)
    plt.tight_layout(); plt.savefig(C.OUTPUT_DIR / "dashboard.png", dpi=130)
    seg.to_csv(C.OUTPUT_DIR / "user_segments.csv")
    print(f"\nĐã lưu: output/dashboard.png, output/user_segments.csv")

if __name__ == "__main__":
    main()
