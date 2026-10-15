# Product Analytics + AI Summary (phần Segmentation / Journey / Alerting)

## Chạy
    pip install -r requirements.txt
    python main.py            # chạy toàn bộ, in kết quả + lưu output/dashboard.png
    # (tuỳ chọn) AI thật: set ANTHROPIC_API_KEY rồi chạy lại

## Luồng xử lý (activity diagram)
```mermaid
flowchart TD
    A[SDK/App gửi event] --> B[validation.py: kiểm tra schema]
    B -->|lỗi| B2[(Bảng event lỗi)]
    B -->|hợp lệ| C[(Event store)]
    C --> D[segmentation.py: feature -> chuẩn hoá -> KMeans -> đặt tên segment]
    C --> E[journey.py: session hoá -> path -> transition -> funnel]
    C --> F[alerting.py: metric theo ngày -> baseline cùng thứ -> robust z-score]
    D --> G[funnel theo segment]
    E --> G
    D --> H[ai_summary.py: build_context]
    E --> H
    F --> H
    H --> I[LLM / template tóm tắt + giả thuyết + brief A/B]
    F --> J[Gửi cảnh báo Slack/Email]
    G --> K[Dashboard theo vai trò]
    I --> K
```

## Mô hình lớp / ERD
```mermaid
erDiagram
    USER ||--o{ EVENT : generates
    USER ||--o{ SESSION : has
    SESSION ||--o{ EVENT : contains
    USER }o--|| SEGMENT : belongs_to
    SEGMENT ||--o{ SEGMENT_SNAPSHOT : versioned_by
    METRIC_DAILY ||--o{ ALERT : triggers
    ALERT }o--o| SEGMENT : scoped_to
    INSIGHT_REPORT }o--o{ ALERT : explains
    INSIGHT_REPORT }o--o{ SEGMENT : summarizes
    USER { int user_id PK
           string platform
           datetime first_seen }
    EVENT { string event_id PK
            int user_id FK
            string session_id FK
            string event_name
            datetime timestamp }
    SESSION { string session_id PK
              int user_id FK
              datetime started_at
              datetime ended_at }
    SEGMENT { int segment_id PK
              string name
              string rule_or_model_version }
    METRIC_DAILY { date date
                   string scope
                   float dau
                   float events }
    ALERT { int alert_id PK
            date date
            string metric
            string scope
            float drop_pct
            string severity }
    INSIGHT_REPORT { int report_id PK
                     text ai_summary
                     datetime created_at }
```
