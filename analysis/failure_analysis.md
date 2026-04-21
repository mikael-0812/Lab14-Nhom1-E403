# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark
- **Tổng số cases:** 70
- **Kết quả V1:** 3 pass / 67 fail / 0 error
- **Kết quả V2:** 49 pass / 21 fail / 0 error
- **Tỉ lệ pass:**
  - V1: **4.29%**
  - V2: **70.00%**
- **Retrieval Metrics trung bình (V2):**
  - Hit Rate: **0.84**
  - Retrieval Accuracy: **0.84**
  - MRR: **0.81**
- **Điểm LLM-Judge trung bình:**
  - V1: **2.18 / 5.0**
  - V2: **4.07 / 5.0**
- **Agreement Rate trung bình:**
  - V1: **0.94**
  - V2: **0.94**
- **Hallucination Rate:**
  - V1: **0.90**
  - V2: **0.21**
- **Manual Review Rate:**
  - V1: **0.90**
  - V2: **0.27**
- **Kết luận tổng quan:** Phiên bản V2 cải thiện mạnh so với V1 trên hầu hết các chỉ số, đặc biệt ở pass rate, retrieval quality và hallucination rate. Tuy nhiên, V2 vẫn còn **21 case fail**, cho thấy hệ thống chưa thật sự ổn định ở các câu hỏi yêu cầu trả lời chính xác, ngắn gọn và bám sát tài liệu.

## 2. Phân nhóm lỗi (Failure Clustering)

| Nhóm lỗi | Mức độ ghi nhận | Nguyên nhân dự kiến |
|----------|------------------|---------------------|
| Retrieval miss / wrong context | Rất nhiều ở V1, còn xuất hiện ở V2 | Retriever không lấy được đúng tài liệu liên quan, làm hit_rate và retrieval_accuracy giảm |
| Unsupported fallback answer | Xuất hiện nhiều | Agent trả lời kiểu “tài liệu không cung cấp thông tin” dù ground truth thực tế có tồn tại |
| Hallucination do suy diễn thêm | Còn xuất hiện ở V2 | Agent thêm email, hotline, stakeholder, quy trình chung hoặc thông tin suy diễn ngoài tài liệu |
| Over-explaining instead of exact answer | Xuất hiện nhiều | Câu hỏi cần đáp án ngắn nhưng agent trả lời dài, làm lệch expected answer |
| Partial correctness with extra detail | Xuất hiện ở một số case | Agent nêu đúng ý chính nhưng thêm chi tiết không được hỗ trợ nên bị judge strict phạt |
| Judge disagreement | Có nhưng không quá nhiều | Một số câu gần đúng khiến balanced judge và strict judge cho điểm khác nhau |

### Nhận xét
- V2 đã cải thiện lớn từ `avg_hit_rate = 0.06` lên `0.84`, nhưng chưa đạt mức ổn định hoàn toàn.  
- `hallucination_rate = 0.21` ở V2 vẫn còn khá cao, nghĩa là cứ khoảng 5 câu thì còn hơn 1 câu bị đánh dấu có yếu tố bịa/suy diễn.  
- `manual_review_rate = 0.27` cho thấy vẫn còn nhiều ca cần người kiểm tra lại thủ công.

## 3. Phân tích 5 Whys

### Case #1: “Thời gian phản hồi ban đầu cho ticket P2 là bao lâu?”
- **System Output:** Agent trả lời rằng tài liệu không có thông tin cụ thể, khuyên tham khảo chính sách nội bộ.
- **Expected Answer:** `2 giờ.`
- **V1 result:** fail, `final_score = 1.4`, `hallucination = 1`, retrieval metrics đều bằng 0.

#### 5 Whys
1. **Symptom:** Agent không trả lời đúng con số đơn giản dù câu hỏi có đáp án rõ ràng.
2. **Why 1:** Retriever không lấy được đúng context liên quan đến SLA ticket P2.
3. **Why 2:** Khi thiếu context đúng, agent chuyển sang chế độ fallback “không có thông tin”.
4. **Why 3:** Prompt hiện tại chưa buộc agent phải ưu tiên trả lời ngắn theo evidence đã retrieve, mà cho phép diễn giải chung.
5. **Why 4:** Pipeline chưa có bước xác thực “câu trả lời có bám expected evidence hay không”.
6. **Root Cause:** **Retriever miss + fallback generation pattern** làm agent né trả lời trực tiếp và sinh ra câu trả lời an toàn nhưng sai.

---

### Case #2: “Quy trình thông báo cho ticket P1 cần làm gì?”
- **System Output:** Agent mô tả cả quy trình phản hồi, escalation, stakeholder updates...
- **Expected Answer:** `Gửi thông báo tới Slack #incident-p1 và email incident@company.internal ngay lập tức.`
- **V1 result:** fail, `final_score = 2.23`, có `hallucination_flagged` và `verdict_mismatch`.

#### 5 Whys
1. **Symptom:** Agent trả lời dài và có vẻ hợp lý nhưng vẫn bị đánh fail.
2. **Why 1:** Agent không bám đúng chi tiết được hỏi, mà trả lời theo hiểu biết tổng quát về incident handling.
3. **Why 2:** Prompt sinh đáp án chưa ép model trích xuất đúng “hành động cần làm” mà cho phép mở rộng thành “quy trình”.
4. **Why 3:** Context retrieval có thể chưa nhấn trúng đoạn chứa Slack channel và email cần thông báo.
5. **Why 4:** Agent có xu hướng ưu tiên câu trả lời đầy đủ, giải thích nhiều hơn mức cần thiết.
6. **Root Cause:** **Answer style mismatch**: agent over-explain thay vì trả lời chính xác theo span cần trích xuất.

---

### Case #3: “Làm thế nào để cấp quyền tạm thời trong trường hợp khẩn cấp?”
- **System Output:** Agent mô tả quy trình chung: gửi yêu cầu khẩn cấp, phê duyệt, cấp quyền, theo dõi thu hồi.
- **Expected Answer:** `On-call IT Admin có thể cấp quyền tạm thời (max 24 giờ) sau khi được Tech Lead phê duyệt bằng lời.`
- **V1/V2 pattern:** đây là kiểu case partial, có disagreement giữa judges; ở một case tương tự `agreement_rate = 0.35`, `final_score = 2.45`.

#### 5 Whys
1. **Symptom:** Agent trả lời gần đúng nhưng thiếu các chi tiết định danh quan trọng.
2. **Why 1:** Agent biết câu hỏi thuộc emergency access flow nhưng không giữ được cụm thông tin then chốt.
3. **Why 2:** Retrieval có thể lấy đúng document nhưng chunk chưa tối ưu cho việc trích xuất câu trả lời ngắn và đầy đủ.
4. **Why 3:** Prompt không nhấn mạnh việc phải giữ nguyên actor + condition + duration.
5. **Why 4:** Judge strict phạt mạnh các câu trả lời thiếu “Tech Lead”, “max 24 giờ”, hoặc “phê duyệt bằng lời”.
6. **Root Cause:** **Loss of key entities during answer compression**: agent nắm đúng ngữ cảnh nhưng làm mất các chi tiết bắt buộc trong câu trả lời cuối.

## 4. Mẫu lỗi điển hình quan sát từ benchmark

### 4.1. Mẫu lỗi Retrieval thất bại
Nhiều case fail ở V1 có:
- `hit_rate = 0.0`
- `retrieval_accuracy = 0.0`
- `mrr = 0.0`
- `ndcg = 0.0`

Điều này cho thấy nguyên nhân gốc ở nhiều ca là **retriever không lấy trúng tài liệu đúng**, khiến toàn bộ phần answer generation bị lệch theo.

### 4.2. Mẫu lỗi Hallucination
Một số câu agent tự thêm:
- email / hotline không đúng ngữ cảnh
- lời khuyên “liên hệ HR”, “liên hệ IT”, “tham khảo tài liệu nội bộ khác”
- mô tả chung chung về quy trình thay vì trả lời trực tiếp

Những chi tiết này không có trong expected answer nên bị judge đánh `hallucination_flag = 1`.

### 4.3. Mẫu lỗi Partial Correct
Có các câu agent:
- đúng ý chính
- nhưng sai mốc thời gian, sai actor, hoặc thêm chi tiết không có trong tài liệu

Ví dụ:
- trả lời đúng “CISO” nhưng thêm “trong vòng 24 giờ”
- trả lời gần đúng về thời gian làm việc nhưng sai `8:30` thay vì `8:00`

Các case này thường bị đánh `partial` hoặc bị kéo điểm xuống bởi strict judge.

## 5. Kế hoạch cải tiến (Action Plan)

### 5.1. Cải thiện Retrieval
- [ ] Tăng chất lượng embedding / retrieval config để giảm các case `hit_rate = 0.0`.
- [ ] Xem lại top-k và reranking nhằm tăng coverage cho đúng tài liệu thay vì chỉ trả về 2 chunk không liên quan.
- [ ] Kiểm tra lại chunking strategy để các fact ngắn như thời gian, email, SLA, actor không bị tách rời khỏi ngữ cảnh.

### 5.2. Cải thiện Answer Generation
- [ ] Cập nhật system prompt theo nguyên tắc: **“Trả lời ngắn, đúng fact, không thêm suy diễn ngoài context.”**
- [ ] Với câu hỏi factoid, ưu tiên **exact answer mode** thay vì explanatory mode.
- [ ] Bổ sung prompt rule: nếu tìm thấy câu trả lời cụ thể trong context, không được trả lời kiểu “tài liệu không đề cập”.

### 5.3. Cải thiện Hallucination Control
- [ ] Thêm bước kiểm tra hậu xử lý để phát hiện các cụm suy diễn như: “bạn có thể liên hệ…”, “tham khảo thêm tài liệu…”, “thông thường…”.
- [ ] Nếu answer chứa chi tiết không nằm trong retrieved context thì giảm confidence hoặc yêu cầu regenerate.
- [ ] Tách rõ chế độ “QA fact extraction” và “open-ended support answer” để tránh agent trả lời lan man.

### 5.4. Cải thiện Độ ổn định đánh giá
- [ ] Phân tích riêng các case có `low_judge_agreement` để xác định chênh lệch đến từ prompt judge hay từ câu trả lời mập mờ.
- [ ] Đánh dấu nhóm “near-correct but overlong” để tối ưu prompt answering thay vì chỉ tối ưu retrieval.

## 6. Kết luận
Phiên bản V2 đã cải thiện đáng kể so với V1:
- Pass Rate tăng từ **4.29%** lên **70.00%**
- Avg Judge Score tăng từ **2.18** lên **4.07**
- Hit Rate tăng từ **0.06** lên **0.84**
- Hallucination Rate giảm từ **0.90** xuống **0.21**
- Cost cũng giảm nhẹ từ **0.039971 USD** xuống **0.037527 USD**

Tuy vậy, hệ thống vẫn chưa đủ mạnh để coi là hoàn toàn ổn định, vì:
1. Vẫn còn **21 case fail**
2. Hallucination vẫn còn tương đối cao
3. Nhiều lỗi đến từ việc agent trả lời dài, sai trọng tâm, hoặc fallback sai kiểu
4. Retrieval chưa đủ ổn định cho toàn bộ tập benchmark

=> Hướng ưu tiên tiếp theo là:
- **nâng chất lượng retrieval**
- **ép answer bám exact evidence**
- **giảm over-explaining và unsupported details**