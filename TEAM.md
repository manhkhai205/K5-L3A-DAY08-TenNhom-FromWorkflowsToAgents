# Team

## Thông tin nhóm

- Tên nhóm:
- Lớp: L3A
- Repo nhóm: `K5-L3A-DAY08-TenNhom-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: `https://github.com/manhkhai205/K5-L3A-DAY08-TenNhom-FromWorkflowsToAgents`, nhánh `main`

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Nguyễn Viết Mạnh Khải | 2A202603664 | manhkhai205@gmail.com | manhkhai205 | Workflow + Single ReAct + Benchmark & ADR |
|   2 | Vũ Đức Anh | 2A202603573 | vuducanh039@gmail.com | ducanh005 | Orchestrator + Security/Handoff + Crash & Research Card |

Xem chi tiết phân công và quy tắc tránh xung đột Git tại [report/team/WORKPLAN.md](report/team/WORKPLAN.md).

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Nguyễn Viết Mạnh Khải (2A202603664) | Workflow + Single ReAct + Benchmark & ADR | `ea8bc67` | `src/tests/test_student_workflow_single.py` (13 tests: ticket injection/old clause, per-order cap full proposal, approval mismatch, 3 crash points & idempotent resume, single max_steps=8 & write-tool block) |
| Vũ Đức Anh (2A202603573) | Orchestrator + Security/Handoff + Crash & Research Card | `0ed16f2` | `src/tests/test_student_orchestrator_security.py` (4 tests: anti-leak, handoff allowlist, approval mismatch, crash resume) |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## MSSV_HoTen

### Phần việc phụ trách

-

### Đóng góp cụ thể

-

### Bằng chứng

-
