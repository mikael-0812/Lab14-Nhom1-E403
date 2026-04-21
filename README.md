# 🚀 Lab Day 14: AI Evaluation Factory (Phiên bản nhóm)

## 🎯 Tổng quan
"Nếu bạn không thể đo lường nó, bạn không thể cải thiện nó." Nhiệm vụ của nhóm bạn là xây dựng một **hệ thống đánh giá tự động** chuyên nghiệp để benchmark AI Agent. Hệ thống này phải chứng minh được bằng số liệu cụ thể: agent đang tốt ở đâu và yếu ở đâu.

---

## 🕒 Lịch trình thực hiện (4 tiếng)
- **Giai đoạn 1 (45 phút):** Thiết kế Golden Dataset và script SDG. Tạo ra ít nhất 50 test case chất lượng.
- **Giai đoạn 2 (90 phút):** Phát triển Eval Engine (RAGAS, Custom Judge) và Async Runner.
- **Giai đoạn 3 (60 phút):** Chạy benchmark, phân cụm lỗi (Failure Clustering) và phân tích "5 Whys".
- **Giai đoạn 4 (45 phút):** Tối ưu agent dựa trên kết quả và hoàn thiện báo cáo nộp bài.

---

## 🛠️ Các nhiệm vụ chính (Expert Mission)

### 1. Retrieval và SDG (Nhóm Data)
- **Retrieval Eval:** Tính toán Hit Rate và MRR cho Vector DB. Bạn phải chứng minh được giai đoạn retrieval hoạt động tốt trước khi đánh giá generation.
- **SDG:** Tạo 50+ test case, bao gồm cả Ground Truth IDs của tài liệu để tính Hit Rate.

### 2. Multi-Judge Consensus Engine (Nhóm AI/Backend)
- **Consensus logic:** Sử dụng ít nhất 2 mô hình judge khác nhau.
- **Calibration:** Tính toán hệ số đồng thuận (Agreement Rate) và tự động xử lý xung đột điểm số.

### 3. Regression Release Gate (Nhóm DevOps/Analyst)
- **Delta Analysis:** So sánh kết quả của agent phiên bản mới với phiên bản cũ.
- **Auto-Gate:** Viết logic tự động quyết định "Release" hoặc "Rollback" dựa trên các chỉ số chất lượng, chi phí và hiệu năng.

---

## 📤 Danh mục nộp bài (Submission Checklist)
Nhóm nộp 1 đường dẫn repository (GitHub/GitLab) chứa:

1. [ ] **Source Code:** Toàn bộ mã nguồn hoàn chỉnh.
2. [ ] **Reports:** File `reports/summary.json` và `reports/benchmark_results.json` (được tạo ra sau khi chạy `main.py`).
3. [ ] **Group Report:** File `analysis/failure_analysis.md` (đã điền đầy đủ).
4. [ ] **Individual Reports:** Các file `analysis/reflections/reflection_[Tên_SV].md`.

---

## 🏆 Bí kíp đạt điểm tuyệt đối (Expert Tips)

### ✅ Đánh giá Retrieval (15%)
Nhóm nào chỉ đánh giá câu trả lời mà bỏ qua bước retrieval sẽ không thể đạt điểm tối đa. Bạn cần biết chính xác chunk nào đang gây ra lỗi hallucination.

### ✅ Multi-Judge Reliability (20%)
Việc chỉ tin vào một judge duy nhất (ví dụ GPT-4o) là một sai lầm trong sản phẩm thực tế. Hãy chứng minh hệ thống của bạn khách quan bằng cách so sánh nhiều judge model và tính toán độ tin cậy của chúng.

### ✅ Tối ưu hiệu năng và chi phí (15%)
Hệ thống expert phải chạy nhanh (async) và phải có báo cáo chi tiết về "chi phí cho mỗi lần eval". Hãy đề xuất cách giảm 30% chi phí eval mà không làm giảm độ chính xác.

### ✅ Phân tích nguyên nhân gốc rễ (Root Cause) (20%)
Báo cáo 5 Whys phải chỉ ra được lỗi nằm ở đâu: ingestion pipeline, chunking strategy, retrieval hay prompting.

---

## 🔧 Hướng dẫn chạy

```bash
# 1. Cài đặt dependencies
pip install -r requirements.txt

# 2. Tạo Golden Dataset (chạy trước khi benchmark)
python data/synthetic_gen.py

# 3. Chạy benchmark và tạo reports
python main.py

# 4. Kiểm tra định dạng trước khi nộp
python check_lab.py
```

---

## ⚠️ Lưu ý quan trọng
- **Bắt buộc** chạy `python data/synthetic_gen.py` trước để tạo file `data/golden_set.jsonl`. File này không được commit sẵn trong repo.
- Trước khi nộp bài, hãy chạy `python check_lab.py` để đảm bảo định dạng dữ liệu đã chuẩn. Bất kỳ lỗi định dạng nào làm script chấm điểm tự động không chạy được sẽ bị trừ 5 điểm thủ tục.
- File `.env` chứa API key **không được** push lên GitHub.

---

## 📊 Cách đọc report sau khi benchmark
`check_lab.py` chỉ kiểm tra một tập con rất nhỏ trong `reports/summary.json`, cụ thể là:
- `metadata.total`
- `metadata.version`
- `metrics.avg_score`
- `metrics.hit_rate`
- `metrics.agreement_rate`

Tuy nhiên, report benchmark đầy đủ còn chứa nhiều thông tin hơn để phân tích chất lượng hệ thống:
- `mrr` và `retrieval_accuracy`: đánh giá chất lượng truy xuất tài liệu.
- `final_answer_accuracy`: mức độ đúng của câu trả lời cuối cùng so với `expected_answer`.
- `hallucination_rate` và `bias_rate`: đo lường rủi ro nội dung sai hoặc thiên lệch.
- `fairness_score`, `consistency_score`, `user_satisfaction_score`: phản ánh chất lượng câu trả lời dưới góc nhìn của judge.
- `latency_seconds` và `cost_usd`: trade-off giữa chất lượng, tốc độ và chi phí.
- `regression`: so sánh trực tiếp giữa V1 và V2 để hỗ trợ release gate.

### Regression highlights từ report hiện tại
Theo `reports/summary.json`, hệ thống đang cho thấy sự cải thiện rõ giữa hai phiên bản:
- `avg_score`: `2.18 -> 4.07`
- `hit_rate`: `0.06 -> 0.84`
- `mrr`: `0.04 -> 0.81`
- `pass_rate`: `4.29% -> 70.0%`
- `hallucination_rate`: `0.90 -> 0.21`
- `estimated_total_cost_usd`: `0.039971 -> 0.037527`

Điều này có nghĩa là V2 không chỉ tốt hơn về chất lượng retrieval và answer quality, mà còn giảm nhẹ tổng chi phí benchmark.

### Các file report nên đọc thêm
- `reports/summary.json`: tổng hợp metric và regression summary.
- `reports/benchmark_results.json`: kết quả chi tiết từng test case cho V1 và V2.
- `analysis/failure_analysis.md`: tổng hợp failure patterns và root-cause analysis của nhóm.

---

*Chúc nhóm bạn xây dựng được một Evaluation Factory thực sự mạnh mẽ!*
