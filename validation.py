"""Validation event theo schema (đề tài yêu cầu 'validation event')."""
import pandas as pd
import config as C

def validate_events(df: pd.DataFrame):
    """Trả về (df_hợp_lệ, df_lỗi). Lỗi kèm lý do để báo cáo chất lượng dữ liệu."""
    S = C.EVENT_SCHEMA
    missing_cols = [c for c in S["required"] if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Thiếu cột bắt buộc: {missing_cols}")

    reason = pd.Series("", index=df.index)
    reason[df[S["required"]].isna().any(axis=1)] += "thiếu_giá_trị;"
    reason[~df["event_name"].isin(S["allowed_events"])] += "event_lạ;"
    reason[~df["platform"].isin(S["allowed_platforms"])] += "platform_lạ;"
    reason[df.duplicated("event_id", keep="first")] += "trùng_event_id;"
    ts = pd.to_datetime(df["timestamp"], errors="coerce")
    reason[ts.isna()] += "timestamp_sai;"
    reason[ts > pd.Timestamp.now() + pd.Timedelta(days=1)] += "timestamp_tương_lai;"

    bad = reason != ""
    good = df[~bad].copy()
    good["timestamp"] = pd.to_datetime(good["timestamp"])
    errors = df[bad].assign(error=reason[bad])
    return good, errors
