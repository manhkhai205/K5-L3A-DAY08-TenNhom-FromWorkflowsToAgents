# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: Nhóm K5-L3A-DAY08 (Nguyễn Viết Mạnh Khải & Vũ Đức Anh)
- Thành viên: xem [TEAM.md](../../TEAM.md)
- Commit chốt (trùng `report/team/decision_adr.md`): `e2e13e7`

## 2. Mục tiêu và cách tiếp cận

- **Bài toán:** Cài đặt cùng một quy trình xử lý claim hoàn phí vận chuyển/hư hỏng hàng hóa của LogiX-VN trên 3 kiến trúc có mức tự chủ tăng dần — **Shape A (`workflow`)**, **Shape B (`single` ReAct)**, **Shape C (`orchestrator` + read-only investigators)** — đặt bên cạnh **Shape D (`swarm` tham chiếu)** để đo đạc và chọn ra kiến trúc **ít tự chủ nhất nhưng vẫn đạt chuẩn nghiệp vụ, độ bền crash và an toàn bảo mật**.
- **Nguyên tắc ranh giới:** Code/host kiểm soát toàn bộ logic tiền (`compute_compensation`), quyền truy cập theo `principal_id`, kiểm tra `approval_id`, trần hoàn tiền theo đơn, idempotency `refund:{claim_id}` và transaction SQLite (`durability.issue_refund`); model (`MockLLM`) chỉ đọc/lập kế hoạch/soạn câu chữ và không có quyền ghi ledger hay quyết định số tiền.
- **Cách chia việc & thứ tự thực hiện:** Hai thành viên dùng ma trận sở hữu file tách biệt trong [WORKPLAN.md](WORKPLAN.md). Khải triển khai `workflow.py`, `single.py` và `test_student_workflow_single.py` trên nhánh `feat/khai-workflow-single`; Đức Anh triển khai `orchestrator.py` và `test_student_orchestrator_security.py` trên nhánh `feat/ducanh-orchestrator`; sau khi merge về `main` mới chạy `crash_test`, `ablation_r1`, `benchmark` và hoàn thiện tài liệu tuần tự.

## 3. Giải pháp

Cả ba shape do nhóm triển khai dùng chung chữ ký `run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult`, luôn đóng kết nối SQLite trong khối `finally` và trả kết quả thông qua `lab8.shapes.common.finish(...)` để đồng bộ ledger, audit và `Trace contract v1`:

- **Shape A (`src/lab8/shapes/workflow.py`):** Thực hiện chuỗi bước xác định trong Python: đọc claim qua `get_claim_view` (không dùng `SELECT *`) → kiểm tra `unknown_claim` (`failed`) và thiếu `order_id` (`needs_info`) → gọi `lookup_order(conn, order_id, principal_id)` để lọc quyền sở hữu principal và allowlist `ORDER_FIELDS` (nếu `visible=False` → `escalated`) → tính quote từ `compute_compensation(conn, order_view["order"])` (bỏ qua mọi con số delay hay điều khoản giả trong ticket). `MockLLM.complete(..., purpose="draft")` chỉ dùng mô phỏng soạn thông báo; khi `proposal > 0` mới gọi `durability.issue_refund(conn, claim_id, proposal, crash_at=crash_at)` với **full quote**. Trace ghi các event `claim_lookup`, `order_lookup`, `quote`, `decision` và `crash` (nếu có).
- **Shape B (`src/lab8/shapes/single.py`):** Bọc vòng lặp ReAct giới hạn `MAX_REACT_STEPS = 8` qua `lab8.runtime.run_react(..., worker=True)`. Tại mỗi bước, `decide` gọi `MockLLM.complete(..., purpose="react")` và chỉ chọn các tool đọc (`get_claim_view` → `lookup_order` → `lookup_refund_history` → `compute_compensation`); mọi write tool (`issue_refund`, `append_audit`) đều bị `runtime.dispatch(..., worker=True)` từ chối bằng `ToolRejected`. Sau khi vòng ReAct trả về quote `> 0`, chính shape (host wrapper) gọi `durability.issue_refund` với full quote. Trace ghi `react_step`, `quote`, `decision`, `crash`.
- **Shape C (`src/lab8/shapes/orchestrator.py`):** Sau khi đọc `get_claim_view` và xử lý sớm `unknown_claim` / `missing_order_id`, orchestrator gọi `MockLLM.complete(..., purpose="plan")` rồi đóng gói gói tin `handoff.v1` qua `lab8.handoff.make_handoff(...)` với `facts={}` và danh sách `allowed_tools` chỉ gồm tool đọc (`lookup_order`, `lookup_policy`, `lookup_refund_history`, `compute_compensation`). `make_handoff` và `sanitize` lọc nghiêm ngặt theo `ALLOWED_FIELDS` / `FACT_KEYS`, từ chối write tool và chặn mọi chuỗi `CANARY_SECRET_*`, `parent_secret`, `raw_headers`. Sau đó `run_readonly_investigators` thực thi các tool đọc với `worker=True`. Orchestrator kiểm tra `order_view["visible"]`, lấy full quote từ `compute_compensation` và gọi `durability.issue_refund(..., crash_at=crash_at)`. Trace chỉ ghi `handoff` đã qua `sanitize`, kết quả allowlist từ `investigator`, `quote`, `host_gate` và `crash` — tuyệt đối không ghi raw parent context, `parent_secret`, `raw_headers_json`, số điện thoại, địa chỉ, tên hàng hay `internal_note`.
- **Ranh giới code / model ([docs/architecture.md](../../docs/architecture.md)):** Toàn bộ kiểm tra principal, policy hiệu lực (`is_current=1`, `effective_date <= 2026-11-15`), tính số tiền hoàn, kiểm tra `approval_id` khớp `claim_id`, trần hoàn tiền theo đơn (`order_refunded_vnd` được đọc lại trong transaction `BEGIN IMMEDIATE`), idempotency key `refund:{claim_id}`, và audit `refund_committed` / `policy_denied` do **code và host** đảm nhiệm; model không chọn số tiền và không gọi ghi ledger. Mọi nhánh đều không bắt `InjectedCrash` (chỉ flush trace rồi `raise` lại).

## 4. Kết quả

Bảng so sánh 4 shape trên bộ public (`src/data/public_claims.jsonl`, 14 claim × 5 seed `11,22,33,44,55` = 70 trial/shape, tổng 280 trial; số liệu lấy từ `src/reports/benchmark.json`):

| Shape | Pass rate | Pass^5 | Seed min–max | Seed variance | Cost / success (VND, mô phỏng) | Mean / p95 steps | Mean model / tool calls |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| `workflow` | **1.000** (70/70) | **1.000** (14/14) | 1.000–1.000 | 0.000000 | **28.79** | 3.79 / 4.0 | 1.00 / 2.79 |
| `single` | 1.000 (70/70) | 1.000 (14/14) | 1.000–1.000 | 0.000000 | 39.34 | 6.29 / 7.0 | 5.64 / 3.64 |
| `orchestrator` | 1.000 (70/70) | 1.000 (14/14) | 1.000–1.000 | 0.000000 | 57.00 | 3.43 / 4.0 | 1.93 / 5.57 |
| `swarm` | 0.986 (69/70) | 0.929 (13/14) | 0.929–1.000 | 0.000816 | 49.57 | 2.80 / 3.0 | 3.00 / 4.66 |

- **Quan sát chính:** `swarm` fail 1 trial (`C-002` tại `seed=55`, lỗi `status resolved != denied`) do tin số ngày trễ trong ticket thay vì cột `delay_days` trong bảng `orders`. Ba shape của nhóm (`workflow`, `single`, `orchestrator`) đều đạt `1.000` pass rate, `0` secret leak và `0` approval bypass; trong đó `workflow` tiết kiệm chi phí nhất (`28.79 VND/success`, thấp hơn `single` 26.8%, thấp hơn `orchestrator` 49.5%).
- **Crash safety (`src/reports/crash.json`):** `20/20` kịch bản pass (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`, `amount_conflict_on_retry`, `retry_without_approval`, `swarm_after_effect_before_checkpoint`), cùng toàn bộ các test crash/idempotency của `workflow`, `single`, `orchestrator` trong ma trận student (`248 passed`) và cổng host (`71 passed`).
- **Tự kiểm trên `student_drop/`:** Chưa có thư mục `student_drop/` trong repo bài làm tại thời điểm chạy kiểm thử.

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

1. Tài liệu bài lab nội bộ: `README.md`, `docs/business_rules.md`, `docs/contracts.md`, `docs/architecture.md`, `docs/metrics.md`.
2. Kim và cộng sự (Google Research, Google DeepMind, MIT), *Towards a Science of Scaling Agent Systems*, 2025/2026, https://arxiv.org/abs/2512.08296.
3. Cemri và cộng sự (MAST, NeurIPS 2025), *Why Do Multi-Agent LLM Systems Fail?*
4. *Rethinking Evaluation of MAS Efficiency* (EMNLP 2026) và *AgentArch* (AACL 2026), trích từ slide lý thuyết N8.
