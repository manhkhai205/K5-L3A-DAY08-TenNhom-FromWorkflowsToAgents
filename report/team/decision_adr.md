# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: <PENDING_HASH>
- Run id dẫn chứng: R-workflow-C-001-s11 (cùng R-workflow-C-002-s55, R-workflow-C-014-s11 trong src/reports/benchmark.json)
- Pass rate / pass^5 / seed min-max / variance: 1.000 (70/70) / 1.000 (14/14) / 1.000–1.000 / 0.000000
- Cost per success (mô phỏng, VND): 28.79 (tổng 2015.30 VND / 70 trial trong src/reports/benchmark.json)
- Crash safety: 20/20 (src/reports/crash.json)
- Secret leak / approval bypass: 0 / 0 (70/70 trial trên public_claims.jsonl trong src/reports/benchmark.json)

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

So sánh trên cùng 14 claim (`src/data/public_claims.jsonl`), cùng 5 seed (`11, 22, 33, 44, 55`), cùng `MockLLM` và bảng giá `src/config/pricing.yaml` (`src/reports/benchmark.json`), ba shape do nhóm cài đặt (`workflow`, `single`, `orchestrator`) đều đạt `pass_rate = 1.000`, `pass^5 = 1.000`, `seed_variance = 0.000000`, `0` secret leak và `0` approval bypass, vượt `swarm` tham chiếu (`pass_rate = 0.986`, `pass^5 = 0.929`, `seed_variance = 0.000816` do tin delay trong ticket ở `C-002` seed `55`). Trong ba shape đạt điểm tuyệt đối, `workflow` có chi phí mô phỏng thấp nhất (`28.79 VND/success`, thấp hơn `single` `39.34 VND` và `orchestrator` `57.00 VND`) và mức tự chủ tối thiểu nhất: quy trình xử lý claim là tuần tự cố định, mọi quyết định tiền bạc (`compute_compensation`), quyền sở hữu đơn (`lookup_order`) và ghi ledger (`durability.issue_refund`) đều nằm chắc chắn trong code, không phát sinh vòng lặp hay handoff dư thừa.

## Có đáng đổi lấy multi-agent không

Không đáng cho bài toán LogiX-VN hiện tại. Dù giả sử một thiết kế multi-agent đạt pass rate ngang hoặc nhỉnh hơn chút ít trên tập dữ liệu khác, việc đổi lấy chi phí cao gần gấp đôi (`57.00 VND` của `orchestrator` hoặc `49.57 VND` của `swarm` so với `28.79 VND` của `workflow`), số bước gọi model/tool nhiều hơn và nguy cơ dao động theo seed (`swarm` seed 55) là không có lợi khi tác vụ vốn mang tính tuần tự chặt chẽ. Quyết định này chỉ đảo lại khi bài toán phát sinh nhiều nhánh điều tra thực sự độc lập có thể chạy song song để giảm critical-path latency, cần suy luận mở trên dữ liệu phi cấu trúc mà rule/lookup có cấu trúc không đọc được, hoặc cần cô lập ranh giới tin cậy (`handoff.v1`) giữa các dịch vụ/đội sở hữu khác nhau.

## Trace và bằng chứng

Trace của `workflow` (`src/traces/R-workflow-<claim_id>-s<seed>.json`) chỉ ghi các sự kiện có cấu trúc đã lọc qua allowlist: `claim_lookup` (`claim_id`, `found`, `has_order_id`), `order_lookup` (`order_id`, `visible`, `reason`), `quote` (output của `compute_compensation`), `decision` (`status`, `reason`, `proposal_amount`) và `crash` (tên `crash_at` khi có `InjectedCrash`). Shape cố ý **không** ghi dòng claim thô (`parent_secret`, `raw_headers_json`), dòng order thô (`phone`, `address`, `item_name`, `internal_note`) và nội dung `ticket` thô để tránh rò rỉ `CANARY_SECRET_*` hoặc PII ngay cả khi ticket bị chèn chuỗi nhạy cảm. Nếu trace nằm ngoài thư mục/quy chuẩn `<run_id>*` mà scanner của grader đọc được, đội security không thể chứng minh file log sạch nên grader phải áp dụng cơ chế fail-closed (`missing_trace` / `stale_trace` / `invalid_trace`).

## Giới hạn

MockLLM không phải model sản xuất: không có sai số trích xuất ngữ nghĩa hay tuân lệnh injection như LLM thật ngoài đời. Latency để `unavailable` (chưa đo được critical-path latency thực tế). Số claim trong bộ public còn ít (14 claim), và trong `src/reports/benchmark.json` kết quả chỉ phản ánh dữ liệu public cho tới khi chạy thêm trên bộ hidden của giảng viên. Không sửa JSON cho đủ ngưỡng 0.75.
