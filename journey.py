"""PHẦN 2 - JOURNEY ANALYSIS: session hoá, đường đi phổ biến, ma trận chuyển bước, funnel."""
from collections import Counter
import pandas as pd
import config as C

def sessionize(events: pd.DataFrame, gap_minutes: int = C.SESSION_GAP_MINUTES) -> pd.DataFrame:
    """Gắn session_id: cùng user, khoảng lặng > gap => session mới."""
    e = events.sort_values(["user_id", "timestamp"]).copy()
    new_session = (e.groupby("user_id")["timestamp"].diff() > pd.Timedelta(minutes=gap_minutes))
    new_session = new_session.fillna(True)
    e["session_no"] = new_session.groupby(e["user_id"]).cumsum()
    e["session_id"] = e["user_id"].astype(str) + "-" + e["session_no"].astype(int).astype(str)
    return e

def session_paths(e: pd.DataFrame) -> pd.Series:
    """Mỗi session -> chuỗi event (đã nén lặp liên tiếp: view,view,view -> view)."""
    def compress(seq):
        out = []
        for x in seq:
            if not out or out[-1] != x:
                out.append(x)
        return tuple(out)
    return e.groupby("session_id")["event_name"].apply(lambda s: compress(s.tolist()))

def top_paths(paths: pd.Series, n: int = 8) -> pd.DataFrame:
    c = Counter(paths)
    df = pd.DataFrame(c.most_common(n), columns=["path", "sessions"])
    df["share_%"] = (df.sessions / len(paths) * 100).round(1)
    df["path"] = df["path"].apply(" → ".join)
    return df

def transition_matrix(paths: pd.Series) -> pd.DataFrame:
    """Xác suất chuyển từ event A sang event B (chuỗi Markov bậc 1)."""
    pairs = Counter()
    for p in paths:
        seq = list(p) + ["<END>"]
        for a, b in zip(seq[:-1], seq[1:]):
            pairs[(a, b)] += 1
    m = pd.Series(pairs).unstack(fill_value=0)
    return m.div(m.sum(axis=1), axis=0).round(3)

def funnel(e: pd.DataFrame, steps=C.FUNNEL_STEPS) -> pd.DataFrame:
    """Funnel theo session: session đạt bước i chỉ khi đã đạt các bước trước (theo thứ tự)."""
    reached = {s: 0 for s in steps}
    for _, grp in e.groupby("session_id")["event_name"]:
        seq = grp.tolist()
        pos = 0
        for i, step in enumerate(steps):
            try:
                pos = seq.index(step, pos) + 1
                reached[step] += 1
            except ValueError:
                break
    df = pd.DataFrame({"step": steps, "sessions": [reached[s] for s in steps]})
    df["conv_from_prev_%"] = (df.sessions / df.sessions.shift(1) * 100).round(1)
    df["conv_from_start_%"] = (df.sessions / df.sessions.iloc[0] * 100).round(1)
    df["drop_off_%"] = (100 - df["conv_from_prev_%"]).round(1)
    return df

def funnel_by_segment(e: pd.DataFrame, seg: pd.DataFrame) -> pd.DataFrame:
    """So sánh funnel giữa các segment -> chỗ giao nhau của Segmentation & Journey."""
    rows = {}
    e = e.merge(seg[["segment"]], left_on="user_id", right_index=True)
    for name, sub in e.groupby("segment"):
        f = funnel(sub)
        rows[name] = f.set_index("step")["conv_from_start_%"]
    return pd.DataFrame(rows).T[C.FUNNEL_STEPS[1:]]
