# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Nguyễn Hoàng Cường 
> **Mã Sinh Viên / Mã Học viên:** 2A202602473  
> **Chủ đề Lựa chọn:** Trợ lý Tra cứu & Tư vấn Tài chính Cá nhân (Financial Advisory ReAct Agent)

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- |:--------------:| :--- |
| **1. Multi-step Reasoning** |      4/ 5      | Bài toán có yêu cầu chia nhỏ nhiều bước suy luận nối tiếp nhau không? |
| **2. Tool Interaction** |     3 / 5      | Hệ thống có cần kết nối với MCP Server / Cơ sở dữ liệu bên ngoài không? |
| **3. Dynamic Decision** |     4 / 5      | Bước tiếp theo có phụ thuộc vào kết quả quan sát bước trước không? |
| **4. Long Horizon Goal** |     4 / 5      | Hệ thống có phải giữ mục tiêu xuyên suốt qua nhiều lượt xử lý không? |
| **TỔNG ĐIỂM AGENTIC FIT** |   **15/ 20**   | *Nếu tổng điểm > 12/20: Bài toán rất phù hợp triển khai Agentic System.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

### Tool 1 — `financial_profile_query`

Tra cứu dữ liệu tài chính cá nhân của khách hàng theo `customer_id`.

### Tool 2 — `create_financial_plan`

Tạo kế hoạch tài chính gồm `customer_id`, `goal`, `monthly_saving_target`, `recommendation`.

---
> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán 1 đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật:
## 3. TEST CASES

- **TC01:** Câu hỏi tài chính chung, không gọi Tool.
- **TC02:** Tra cứu KH001 bằng `financial_profile_query`.
- **TC03:** Tạo kế hoạch trực tiếp cho KH002 bằng `create_financial_plan`.
- **TC04:** Multi-step `financial_profile_query -> create_financial_plan -> Final Answer`.
- **TC05:** KH999 trả `NOT_FOUND`, không hallucination.

---

```json

 financial_profile_query(KH001)
    ↓
Observation: monthly_free_cashflow
    ↓
create_financial_plan(...)
    ↓
Observation: SUCCESS + plan_id
    ↓
Final Answer

```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI
- [x] Không còn TODO trong test cases.
- [x] MCP response có `jsonrpc: 2.0`.
- [x] Có Anti-Hallucination khi NOT_FOUND.
- [x] `.env` đã nằm trong `.gitignore`.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
