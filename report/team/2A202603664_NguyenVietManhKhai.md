# Báo cáo cá nhân — 2A202603664_NguyenVietManhKhai

## 1. Thông tin thành viên

- Họ tên: Nguyễn Viết Mạnh Khải
- MSSV: 2A202603664
- Email: manhkhai205@gmail.com
- GitHub: manhkhai205

## 2. Phần việc phụ trách

- Thiết kế kế hoạch phân công và quy trình làm việc song song không xung đột tại `report/team/WORKPLAN.md` và cập nhật `TEAM.md`.
- Thiết kế và cài đặt **Shape A (`workflow`)** trong `src/lab8/shapes/workflow.py` và **Shape B (`single`)** trong `src/lab8/shapes/single.py` theo chuẩn `RunResult`, `durability.issue_refund` và `Trace contract v1`.
- Viết bộ test riêng tại `src/tests/test_student_workflow_single.py` (13 test cases).
- Chạy benchmark so sánh 4 shape × 5 seed (`src/reports/benchmark.json`), viết `report/team/decision_adr.md`, và hoàn thiện các mục **1, 2, 4, 8** trong `report/team/group_report.md` cùng cổng kiểm tra `lab8.check_submission`.

## 3. Đóng góp cụ thể

- **Commit chính:**
  - `34cc930` (`docs: update team member details and add work plan to avoid conflicts`): thiết lập ma trận sở hữu file và quy trình nhánh tách biệt cho 2 thành viên.
  - `ea8bc67` (`feat(shapes): implement workflow and single ReAct shapes with tests`), merge vào `main` qua PR #1 (`89429b6`).
- **Quyết định kỹ thuật trong `workflow.py` và `single.py`:**
  - Cả hai shape đọc claim bằng `get_claim_view` (không dùng `SELECT *`), xử lý sớm `unknown_claim` (`failed`), thiếu `order_id` (`needs_info`), và kiểm quyền sở hữu order qua `lookup_order` (`escalated` nếu `visible=False`).
  - Quote bồi thường luôn tính bằng code thông qua `compute_compensation` trên order row có cấu trúc; bỏ qua hoàn toàn các con số delay giả hoặc điều khoản cũ (`SHIP-LATE-OLD`) trong nội dung ticket.
  - Khi `proposal > 0`, truyền **full quote** vào `durability.issue_refund(conn, claim_id, proposal, crash_at=crash_at)` để host tự kiểm `approval_id`, tự trừ phần đã hoàn của đơn (T13, T14) và ghi `policy_denied` khi bị từ chối; không bắt `InjectedCrash` (chỉ ghi event `crash` vào trace, gọi `trace.write()` rồi `raise`).
  - Trong `single.py`, dùng `lab8.runtime.run_react(..., max_steps=8, worker=True)` để ép vòng lặp ReAct chỉ gọi read tools (`get_claim_view`, `lookup_order`, `lookup_refund_history`, `compute_compensation`), đếm đầy đủ số lần gọi `MockLLM` vào `Budget`, và giữ thao tác ghi refund duy nhất ở code bên ngoài vòng lặp.
  - Trace chỉ ghi metadata và payload đã qua allowlist (không ghi `parent_secret`, `raw_headers_json`, SĐT, địa chỉ, tên hàng, ghi chú nội bộ hay raw ticket), trả về qua `lab8.shapes.common.finish(...)` trên mọi nhánh.
- **Test đã thêm (`src/tests/test_student_workflow_single.py` — 13 tests):**
  1. `test_ticket_injection_and_old_clause_are_ignored` (parametrize `workflow`, `single`): xác minh prompt injection ("ignore policy", "trễ 9 ngày", `SHIP-LATE-OLD`) bị bỏ qua, trả `denied`, `proposal_amount=0`, và không lộ `CANARY_SECRET_*` trong trace/result.
  2. `test_per_order_cap_keeps_full_proposal_amount` (parametrize `workflow`, `single`): xác minh T14 (`C-014`) giữ `proposal_amount=150000` (full quote) trong khi host chỉ ghi phần chênh `120000` vào ledger.
  3. `test_approval_mismatch_writes_policy_denied_and_no_refund` (parametrize `workflow`, `single`): xác minh khi `approval_id` thuộc claim khác, shape trả `denied`, `proposal_amount=35000`, không ghi ledger và host ghi audit `policy_denied` (`approval_claim_mismatch`).
  4. `test_crash_propagation_and_idempotent_resume` (parametrize `workflow`, `single` × 3 điểm crash `before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`): xác minh `InjectedCrash` được lan truyền và lần chạy resume giữ đúng 1 dòng ledger, 1 audit `refund_committed`.
  5. `test_single_react_budget_bound_and_write_tool_blocked`: xác minh `single` dùng `1 <= model_calls <= 8`, `tool_calls <= 8`, và `dispatch(..., worker=True)` chặn `issue_refund` bằng `ToolRejected`.

## 4. Bằng chứng

- **Commit trên `main`:** `34cc930`, `ea8bc67`, `89429b6`.
- **Kết quả kiểm thử trong `src/`:**
  - `python -m pytest -q`: **71 passed, 248 deselected** (bao gồm 54 test cổng host + 13 test của Khải + 4 test của Đức Anh).
  - `python -m pytest -q -m student -o addopts=`: **248 passed, 71 deselected** (`workflow` 62/62, `single` 62/62, `orchestrator` 62/62, `swarm` 62/62).
  - `python -m pytest -q tests/test_student_workflow_single.py`: **13 passed**.
- **Kết quả benchmark 4 shape × 5 seed (`src/reports/benchmark.json`):**
  - Run id đại diện: `R-workflow-C-001-s11`, `R-single-C-001-s11`, `R-orchestrator-C-001-s11`, `R-swarm-C-001-s11`.
  - `workflow`: `pass_rate = 1.000`, `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost_per_success_vnd = 28.79`, `mean_steps = 3.79`.
  - `single`: `pass_rate = 1.000`, `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost_per_success_vnd = 39.34`, `mean_steps = 6.29`.
- **Kiểm tra format nộp bài:** `python -m lab8.check_submission` → **0 FAIL**.

## 5. Công cụ AI đã dùng

- **Công cụ:** Trợ lý AI lập trình Antigravity (model Gemini).
- **Mục đích sử dụng:** Đọc rà toàn bộ đề bài/contract để chia việc không xung đột, hỗ trợ viết khung `workflow.py`, `single.py` và 13 unit test trong `test_student_workflow_single.py`, kiểm tra lại các nhánh ADR từ số liệu `src/reports/benchmark.json`.
- **Cách tự kiểm tra kết quả (theo [RULES.md](../../RULES.md)):**
  - Đối chiếu trực tiếp từng điều kiện trong `docs/business_rules.md` và `docs/contracts.md` với code của `workflow.py` và `single.py`, kiểm tra không chạm vào bất kỳ file thước đo/dữ liệu gốc nào (`git diff --name-only`).
  - Chạy trực tiếp `python -m pytest -q`, `python -m pytest -q -m student -o addopts=`, `python -m lab8.benchmark`, và `python -m lab8.check_submission` trong `src/`, đồng thời đọc trực tiếp `src/reports/benchmark.json` để đảm bảo mọi số liệu trong ADR và báo cáo khớp 100% đầu ra thực tế.

## 6. Tự đánh giá

- Hoàn thành đầy đủ Shape A (`workflow`), Shape B (`single`), bộ 13 test riêng, benchmark 4 shape, `decision_adr.md`, các phần được phân công trong `group_report.md` và kiểm tra sạch `check_submission` (`0 FAIL`).
- Phối hợp nhịp nhàng với thành viên còn lại theo `report/team/WORKPLAN.md`, không phát sinh xung đột file khi merge.
