"""PHẦN 1 - SEGMENTATION: phân nhóm người dùng bằng RFM + hành vi + K-Means."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
import config as C

def build_features(events: pd.DataFrame) -> pd.DataFrame:
    """Mỗi user -> 1 dòng đặc trưng (feature engineering)."""
    now = events["timestamp"].max()
    g = events.groupby("user_id")
    f = pd.DataFrame({
        "recency_days": (now - g["timestamp"].max()).dt.total_seconds() / 86400,   # R
        "active_days": g["timestamp"].apply(lambda s: s.dt.date.nunique()),         # F
        "total_events": g.size(),
    })
    cnt = events.pivot_table(index="user_id", columns="event_name", values="event_id",
                             aggfunc="count", fill_value=0)
    for col in ["view_product", "add_to_cart", "purchase"]:
        f[col] = cnt.get(col, 0)
    f["purchases"] = f.pop("purchase")                                               # M (proxy)
    f["view_to_cart_rate"] = f["add_to_cart"] / f["view_product"].replace(0, np.nan)
    f["view_to_cart_rate"] = f["view_to_cart_rate"].fillna(0)
    f["tenure_days"] = (now - g["timestamp"].min()).dt.total_seconds() / 86400
    return f

CLUSTER_FEATURES = ["recency_days", "active_days", "view_product", "purchases", "view_to_cart_rate"]

def choose_k(X: np.ndarray, k_range=range(2, 8)) -> dict:
    """Chọn k bằng silhouette score (đánh giá chất lượng cụm)."""
    return {k: silhouette_score(X, KMeans(k, n_init=10, random_state=C.SEED).fit_predict(X))
            for k in k_range}

def segment_users(features: pd.DataFrame, k: int = C.N_CLUSTERS):
    X = StandardScaler().fit_transform(np.log1p(features[CLUSTER_FEATURES]))
    km = KMeans(k, n_init=10, random_state=C.SEED).fit(X)
    out = features.copy()
    out["cluster"] = km.labels_
    return out, choose_k(X)

def name_segments(seg: pd.DataFrame) -> pd.DataFrame:
    """Gán tên dễ hiểu bằng luật trên trung bình từng cụm (giúp AI & người không chuyên đọc được)."""
    prof = seg.groupby("cluster")[CLUSTER_FEATURES].mean()
    names = {}
    for c, r in prof.iterrows():
        if r.recency_days > 20:
            names[c] = "Đã rời bỏ / ngủ đông (churned)"
        elif r.purchases >= prof.purchases.quantile(0.75) and r.active_days >= prof.active_days.median():
            names[c] = "Khách trung thành mua nhiều (power buyer)"
        elif r.view_product >= prof.view_product.median() and r.purchases < prof.purchases.median():
            names[c] = "Người xem nhiều, ít mua (browser)"
        else:
            names[c] = "Người dùng thỉnh thoảng (casual)"
    seg["segment"] = seg["cluster"].map(names)
    return seg

def profile(seg: pd.DataFrame) -> pd.DataFrame:
    p = seg.groupby("segment").agg(
        users=("cluster", "size"),
        recency_days=("recency_days", "mean"),
        active_days=("active_days", "mean"),
        views=("view_product", "mean"),
        purchases=("purchases", "mean"),
    ).round(2)
    p["share_%"] = (p.users / p.users.sum() * 100).round(1)
    return p.sort_values("users", ascending=False)
