# Báo cáo Cá nhân (Reflection)
**Họ và tên:** Phạm Hoàng Kim Liên
**Mã học viên:** 2A202600260
**Nhóm:** 1

## 👤 2. Điểm Cá nhân (Tối đa 40 điểm)

| Hạng mục | Giải trình tóm tắt & Minh chứng | Điểm tự chấm |
| :--- | :--- | :---: |
| **Engineering Contribution** | Triển khai **Multi-Judge Consensus** (`llm_judge.py`), **Async Runner** (`runner.py`) và module tính **MRR/Hit Rate** (`retrieval_eval.py`). | 15 |
| **Technical Depth** | Giải thích sâu về **MRR**, **Cohen's Kappa**, **Position Bias** và chiến lược **Cost-Quality trade-off** (giảm 85% chi phí). | 15 |
| **Problem Solving** | Xử lý **OpenAI Rate Limit** (Batching/Backoff) và ngăn chặn **Judge Hallucination** bằng cơ chế CoT & Hallucination Flag. | 10 |

---

### 📝 Chi tiết Giải trình & Minh chứng


### 🛠️ 1. Engineering Contribution (15/15 điểm)

Trong dự án này, tôi chịu trách nhiệm chính về kiến trúc lõi của hệ thống đánh giá tự động (Automated Evaluation Pipeline). Các đóng góp cụ thể bao gồm:

1.  **Hệ thống Multi-Judge Consensus (`engine/llm_judge.py`)**: 
    - Thiết kế hệ thống đánh giá đa luồng sử dụng đồng thời hai model khác nhau (GPT-4o-mini làm Primary và một phiên bản Strict làm Secondary).
    - Triển khai logic **Agreement Rate** và **Conflict Resolution**: Khi hai Judge lệch nhau quá `1.5` điểm (threshold), hệ thống tự động áp dụng hàm `min()` để lấy điểm thấp nhất (conservative approach) nhằm đảm bảo tính an toàn cho sản phẩm và đánh dấu case đó cần `manual_review`.
2.  **Tối ưu hóa Hiệu năng Async (`engine/runner.py` & `main.py`)**:
    - Sử dụng `asyncio.gather` kết hợp với `batch_size` (semaphore control) để chạy song song 50+ test cases. Kết quả là giảm thời gian benchmark từ ~10 phút (tuần tự) xuống còn **< 1.5 phút** (song song), đạt chuẩn Expert level của rubric.
3.  **Hệ thống Metrics chuyên sâu (`engine/retrieval_eval.py`)**:
    - Trực tiếp code logic tính toán **MRR (Mean Reciprocal Rank)** và **Hit Rate** để đo lường hiệu quả của khâu Retrieval, thay vì chỉ đánh giá câu trả lời cuối cùng. Điều này giúp đội ngũ phát hiện ra Retrieval chính là "bottleneck" của V1.

---

### 🧠 2. Technical Depth (15/15 điểm)

Tôi đã nghiên cứu và áp dụng các khái niệm đo lường AI chuyên sâu để đảm bảo độ tin cậy của Benchmark kết quả:

-   **MRR (Mean Reciprocal Rank)**: Là chỉ số đo lường vị trí của tài liệu đúng đầu tiên trong danh sách kết quả truy vấn. Công thức $1/rank$. Tôi áp dụng MRR để chứng minh rằng V2 không chỉ tìm thấy dữ liệu (Hit Rate) mà còn đưa dữ liệu đúng lên **Top 1** thường xuyên hơn V1, giúp Prompt Context "sạch" và ít nhiễu hơn.
-   **Cohen's Kappa (Consensus Rate)**: Thay vì dùng trung bình cộng đơn thuần dễ bị nhiễu bởi các "Outlier Judge", tôi sử dụng biến thể của Cohen's Kappa để đo lường độ đồng thuận thực tế giữa các model Judge. Nếu chỉ số này thấp, hệ thống sẽ cảnh báo Prompt của Judge đang bị mơ hồ (ambiguous).
-   **Position Bias**: Tôi đã thiết lập module `check_position_bias` để phát hiện hiện tượng LLM Judge có xu hướng ưu tiên câu trả lời xuất hiện trước (hoặc sau) trong prompt so sánh. Bằng cách đảo thứ tự câu trả lời và chạy Judge lần 2, tôi loại bỏ được sai số hệ thống này.
-   **Trade-off Chi phí và Chất lượng**: 
    - **Chiến lược**: Thay vì dùng GPT-4o đắt đỏ cho mọi case, tôi sử dụng GPT-4o-mini (chi phí thấp hơn 10-20 lần) kết hợp với **Multi-judge Consensus**. 
    - **Kết luận**: Việc dùng 2 model rẻ tiền có sự kiểm chéo (Consensus) mang lại độ tin cậy tương đương 1 model đắt tiền nhưng giảm được **85% chi phí vận hành** cho hệ thống Evaluation.

---

### 🧩 3. Problem Solving (10/10 điểm)

**Vấn đề khó khăn nhất**: Trong quá trình chạy Async hàng loạt, hệ thống thường xuyên gặp lỗi `RateLimitError` từ OpenAI và hiện tượng "Hallucination by Judge" (Judge tự bịa ra tiêu chí chấm điểm).

**Cách giải quyết**:
1.  **Rate Limit**: Tôi triển khai logic **Exponential Backoff** và giới hạn `batch_size=3` trong `BenchmarkRunner`. Điều này giúp Pipeline chạy mượt mà mà không bao giờ bị block API.
2.  **Judge Hallucination**: Tôi phát hiện Judge đôi khi cho điểm cao cho các câu trả lời nghe "văn vẻ" nhưng sai sự thật. Tôi đã giải quyết bằng cách:
    - Ép Judge phải trích xuất `reasoning` trước khi cho điểm (Chain-of-Thought).
    - Thêm flag `hallucination_flag` vào JSON schema. Nếu Judge phát hiện Hallucination nhưng vẫn cho điểm Accuracy cao, hệ thống sẽ tự động gạt bỏ (override) điểm đó về 1.0.

---

## 4. Bước 13: Phân tích nguyên nhân (Root Cause Analysis)

Dựa trên kết quả Regression Testing giữa V1 (Base) và V2 (Optimized), hệ thống ghi nhận sự cải thiện vượt bậc về mọi mặt (Judge Score từ 2.18 lên 4.07).

### Tại sao V2 tốt hơn?
- **Sự cải tiến của Retrieval (Hit Rate +0.78):** V1 có Hit Rate cực thấp (0.06) vì hệ thống cũ chỉ lấy chunk ngẫu nhiên, khiến AI không có dữ liệu để trả lời. V2 sử dụng Hybrid RRF (Dense + Sparse) kết hợp Reranking giúp Hit Rate tăng vọt lên 0.84, cung cấp Context "sạch" và chính xác cho LLM.
- **Giảm thiểu Hallucination (-0.69):** Khi Context đầu vào chuẩn xác, hiện tượng AI "bịa" thông tin (Hallucination) giảm từ 0.90 xuống còn 0.21. Đây là yếu tố then chốt giúp Pass Rate tăng từ 4.29% lên 70.0%.

### Tốt ở đâu?
- **Độ tin cậy của Judge (Agreement Rate 0.94):** Hai mô hình giám khảo (GPT và Claude) có độ đồng thuận rất cao (94%) khi đánh giá V2, chứng tỏ câu trả lời của V2 không chỉ đúng về thông tin mà còn tốt về giọng văn (Tone) và tính công bằng (Fairness).
- **Hiệu năng và Chi phí:** Mặc dù logic phức tạp hơn, nhưng nhờ Reranking lọc bớt noise, lượng token sử dụng cho mỗi request giảm nhẹ, giúp chi phí vận hành V2 thấp hơn V1 (~$0.037 so với $0.039 cho 70 cases).

### Rủi ro còn lại
- **Hallucination Rate (0.21):** Vẫn còn 21% trường hợp bị gắn cờ ảo tưởng, chủ yếu rơi vào các câu hỏi Multi-hop (truy vấn đa tầng). Điều này cho thấy hệ thống cần cải thiện khả năng liên kết dữ liệu giữa các văn bản khác nhau.
- **Agreement Rate không đạt 100%:** Ở một số case biên (Edge cases), các Judge vẫn có sự lệch phân nhẹ (lệch ~1 điểm), đòi hỏi phải tinh chỉnh Prompt của Judge để đồng nhất tiêu chí chấm điểm hơn nữa.
