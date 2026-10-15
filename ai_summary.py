"""AI tóm tắt hành vi người dùng.

Thiết kế 2 lớp:
 1) build_context(): gom KẾT QUẢ ĐÃ TÍNH (số liệu thật) thành JSON gọn -> AI chỉ 'diễn giải', không tự bịa số.
 2) summarize(): gọi LLM nếu có ANTHROPIC_API_KEY; nếu không thì dùng bản tóm tắt theo template (offline).
"""
import json, os
import pandas

def build_context(seg_profile: pd.DataFrame, funnel_df: pd.DataFrame,
                  top: pd.DataFrame, alerts: list) -> dict:
    worst = funnel_df.dropna().sort_values("drop_off_%", ascending=False).iloc[0]
    return {
        "segments": seg_profile.reset_index().to_dict("records"),
        "funnel": funnel_df.fillna(0).to_dict("records"),
        "biggest_dropoff": {"to_step": worst["step"], "drop_off_pct": float(worst["drop_off_%"])},
        "top_paths": top.head(5).to_dict("records"),
        "alerts": [{"date": str(a.date.date()), "metric": a.metric, "scope": a.scope,
                    "drop_pct": a.drop_pct, "severity": a.severity} for a in alerts[-5:]],
    }

PROMPT = """Bạn là chuyên gia product analytics. Dựa CHỈ trên JSON số liệu dưới đây, hãy:
1) Tóm tắt hành vi người dùng (<=5 câu, dễ hiểu cho người không chuyên).
2) Chỉ ra điểm nghẽn lớn nhất của funnel và nguyên nhân có thể.
3) Đề xuất 3 giả thuyết cải tiến + 1 brief thử nghiệm A/B (mục tiêu, biến, chỉ số).
4) Giải thích các cảnh báo gần nhất. Không được bịa số liệu ngoài JSON.

JSON:
{data}"""

def template_summary(ctx: dict) -> str:
    segs = sorted(ctx["segments"], key=lambda s: -s["users"])
    lines = ["[Bản tóm tắt offline - theo template, không gọi LLM]", ""]
    lines.append("Phân nhóm: " + "; ".join(f'{s["segment"]} chiếm {s["share_%"]}%' for s in segs) + ".")
    b = ctx["biggest_dropoff"]
    lines.append(f'Điểm nghẽn lớn nhất của funnel: bước "{b["to_step"]}" (mất {b["drop_off_pct"]}% so với bước trước).')
    if ctx["alerts"]:
        a = ctx["alerts"][-1]
        lines.append(f'Cảnh báo gần nhất: {a["severity"]} - {a["metric"]} ({a["scope"]}) giảm {a["drop_pct"]}% vào {a["date"]}.')
    lines += ["", "Giả thuyết gợi ý:",
              "  H1. Tối ưu nút thêm vào giỏ & thông tin sản phẩm để tăng chuyển đổi view -> cart.",
              "  H2. Gửi ưu đãi/nhắc giỏ hàng cho nhóm có tỉ lệ view -> cart thấp (segment lớn nhất).",
              "  H3. Điều tra bản phát hành/lỗi ở nền tảng đang có cảnh báo giảm.",
              "Brief A/B: đối tượng = segment đông nhất; biến = banner ưu đãi lần đầu; chỉ số chính = view->cart rate."]
    return "\n".join(lines)

def summarize(ctx: dict) -> str:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return template_summary(ctx)
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=key)
        msg = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"), max_tokens=1000,
            messages=[{"role": "user", "content": PROMPT.format(data=json.dumps(ctx, ensure_ascii=False))}])
        return msg.content[0].text
    except Exception as ex:                       # lỗi mạng/key -> vẫn có kết quả
        return template_summary(ctx) + f"\n\n(LLM lỗi: {ex})"
