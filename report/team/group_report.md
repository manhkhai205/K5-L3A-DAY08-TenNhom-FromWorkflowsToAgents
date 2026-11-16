# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm:
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`):

## 2. Mục tiêu và cách tiếp cận

Nhóm hiểu bài toán thế nào, chia việc ra sao, thứ tự làm bốn shape.

...

## 3. Giải pháp

Cả ba shape do nhóm triển khai dùng chung chữ ký `run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult`, luôn đóng kết nối SQLite trong khối `finally` và trả kết quả thông qua `lab8.shapes.common.finish(...)` để đồng bộ ledger, audit và `Trace contract v1`:

- **Shape A (`src/lab8/shapes/workflow.py`):** Thực hiện chuỗi bước xác định trong Python: đọc claim qua `get_claim_view` (không dùng `SELECT *`) → kiểm tra `unknown_claim` (`failed`) và thiếu `order_id` (`needs_info`) → gọi `lookup_order(conn, order_id, principal_id)` để lọc quyền sở hữu principal và allowlist `ORDER_FIELDS` (nếu `visible=False` → `escalated`) → tính quote từ `compute_compensation(conn, order_view["order"])` (bỏ qua mọi con số delay hay điều khoản giả trong ticket). `MockLLM.complete(..., purpose="draft")` chỉ dùng mô phỏng soạn thông báo; khi `proposal > 0` mới gọi `durability.issue_refund(conn, claim_id, proposal, crash_at=crash_at)` với **full quote**. Trace ghi các event `claim_lookup`, `order_lookup`, `quote`, `decision` và `crash` (nếu có).
- **Shape B (`src/lab8/shapes/single.py`):** Bọc vòng lặp ReAct giới hạn `MAX_REACT_STEPS = 8` qua `lab8.runtime.run_react(..., worker=True)`. Tại mỗi bước, `decide` gọi `MockLLM.complete(..., purpose="react")` và chỉ chọn các tool đọc (`get_claim_view` → `lookup_order` → `lookup_refund_history` → `compute_compensation`); mọi write tool (`issue_refund`, `append_audit`) đều bị `runtime.dispatch(..., worker=True)` từ chối bằng `ToolRejected`. Sau khi vòng ReAct trả về quote `> 0`, chính shape (host wrapper) gọi `durability.issue_refund` với full quote. Trace ghi `react_step`, `quote`, `decision`, `crash`.
- **Shape C (`src/lab8/shapes/orchestrator.py`):** Sau khi đọc `get_claim_view` và xử lý sớm `unknown_claim` / `missing_order_id`, orchestrator gọi `MockLLM.complete(..., purpose="plan")` rồi đóng gói gói tin `handoff.v1` qua `lab8.handoff.make_handoff(...)` với `facts={}` và danh sách `allowed_tools` chỉ gồm tool đọc (`lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation`). `make_handoff` và `sanitize` lọc nghiêm ngặt theo `ALLOWED_FIELDS` / `FACT_KEYS`, từ chối write tool và chặn mọi chuỗi `CANARY_SECRET_*`, `parent_secret`, `raw_headers`. Sau đó `run_readonly_investigators` thực thi các tool đọc với `worker=True`. Orchestrator kiểm tra `order_view["visible"]`, lấy full quote từ `compute_compensation` và gọi `durability.issue_refund(..., crash_at=crash_at)`. Trace chỉ ghi `handoff` đã qua `sanitize`, kết quả allowlist từ `investigator`, `quote`, `host_gate` và `crash` — tuyệt đối không ghi raw parent context, `parent_secret`, `raw_headers_json`, số điện thoại, địa chỉ, tên hàng hay `internal_note`.
- **Ranh giới code / model ([docs/architecture.md](../../docs/architecture.md)):** Toàn bộ kiểm tra principal, policy hiệu lực (`is_current=1`, `effective_date <= 2026-11-15`), tính số tiền hoàn, kiểm tra `approval_id` khớp `claim_id`, trần hoàn tiền theo đơn (`order_refunded_vnd` được đọc lại trong transaction `BEGIN IMMEDIATE`), idempotency key `refund:{claim_id}`, và audit `refund_committed` / `policy_denied` do **code và host** đảm nhiệm; model không chọn số tiền và không gọi ghi ledger. Mọi nhánh đều không bắt `InjectedCrash` (chỉ flush trace rồi `raise` lại).

## 4. Kết quả

Bảng so sánh 4 shape trên bộ public (từ `src/reports/benchmark.json`): pass rate, pass^5, seed min–max, variance, cost/success, mean/p95 steps. Kèm crash safety (`src/reports/crash.json`) và, nếu có, kết quả tự kiểm trên `student_drop/`.

...

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

1. **Phân biệt bộ test cổng host mặc định và ma trận `student`:** File `src/pytest.ini` mặc định loại bỏ marker `student` khi chạy `python -m pytest -q`. Để chạy đủ 248 test của 4 shape trên T01–T14 × 5 seed cùng T11/T12, nhóm phải dùng cờ `python -m pytest -q -m student -o addopts=` (hoặc `-k orchestrator` để kiểm riêng từng shape).
2. **Tránh trừ trùng tiền hoàn ở T13/T14 và lỗi `crash did not fire` ở T12:** Khi cài đặt `orchestrator.py`, dù đã cấp `lookup_refund_history` cho investigator nhưng không được tự trừ số tiền đã hoàn trước đó; nếu tự trừ trước khi gọi `durability.issue_refund`, host sẽ trừ thêm một lần nữa trong `policy.authorize`. Đồng thời, ở nhánh gọi `issue_refund`, bắt buộc truyền `crash_at=crash_at` và chỉ ghi trace trước khi `raise` lại `InjectedCrash` để `lab8.crash_test` đạt `20/20` (`src/reports/crash.json`).
3. **Tuân thủ `Trace contract v1` và tránh khóa file SQLite trên Windows:** Nếu quên ghi trace ở nhánh return sớm (`unknown_claim`, `needs_info`, `escalated`, `denied`), grader fail-closed với `missing_trace`; nếu quên đóng `conn.close()` trước khi trả về, Windows báo lỗi giữ lock file `.sqlite`. Nhóm thống nhất dùng cấu trúc `try ... finally: conn.close()` và trả về qua `lab8.shapes.common.finish(...)` trên mọi nhánh.
4. **Phối hợp song song 2 thành viên không xung đột Git:** Nhóm lập ma trận sở hữu file trong `report/team/WORKPLAN.md`, tách 2 nhánh `feat/khai-workflow-single` và `feat/ducanh-orchestrator`, merge tuần tự về `main` (`89429b6`, `f439010`) rồi mới cập nhật báo cáo tuần tự, giữ nguyên 100% các file thước đo và dữ liệu gốc.

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md`.

## 7. Hạn chế và hướng cải thiện

- **Giới hạn của môi trường mô phỏng:** `MockLLM` (`src/lab8/mock_llm.py`) sinh chuỗi cố định theo `seed` và tính chi phí giả lập theo `src/config/pricing.yaml`, không phản ánh lỗi suy luận ngữ nghĩa, trích xuất nhầm hay prompt injection phức tạp của LLM thật ngoài đời; giá trị `latency` luôn là `unavailable` nên chưa đo được thời gian phản hồi thực tế.
- **Giới hạn dữ liệu và phạm vi kết luận:** Bộ public (`src/data/public_claims.jsonl`) chỉ có 14 claim và toàn bộ logic tính tiền nằm trong code (`compute_compensation`), nên hiện tại không quan sát thấy suy giảm accuracy khi nâng từ `workflow` lên `orchestrator` (`pass_rate = 1.000` ở cả ba shape trong `src/reports/ablation_r1.json`). Tuy nhiên, chi phí mô phỏng của `orchestrator` (`57.00 VND`) cao gần gấp đôi `workflow` (`28.79 VND`). Kết luận ưu tiên `workflow` sẽ đảo ngược nếu bài toán thực tế có nhiều bước đọc độc lập thực sự song song được để rút ngắn critical-path latency, hoặc cần cách ly ngữ cảnh đa tenant với hợp đồng `handoff.v1` nghiêm ngặt giữa các service tách rời.
- **Hướng cải thiện:** Thử nghiệm mô hình độ trễ và chạy song song các investigator độc lập (`lookup_order`, `lookup_policy`) trên các SQLite connection tách biệt, mở rộng tập test đối kháng (homoglyph, nhiều claim cạnh tranh trên cùng đơn hàng), và đánh giá thêm trên tập hidden 40 claim × 5 seed khi có `student_drop/`.

## 8. Tài liệu tham khảo

...
