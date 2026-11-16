# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R1 · Scaling |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Kim và cộng sự (Google Research, Google DeepMind, MIT), *Towards a Science of Scaling Agent Systems*, 2025/2026, https://arxiv.org/abs/2512.08296, bài nghiên cứu thực nghiệm trên benchmark agentic |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Trên các tác vụ suy luận tuần tự chặt chẽ, các biến thể multi-agent làm giảm hiệu năng 39–70% so với single-agent; multi-agent chỉ có lợi rõ khi tác vụ tách song song được và hệ số khuếch đại lỗi thấp |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Kết luận đo trên các LLM thực tế qua PlanCraft, BrowseComp-Plus, Workbench và Finance-Agent dưới ngân sách token cố định; khi baseline single-agent vượt ~45% thì hiệu quả biên của multi-agent giảm dần hoặc âm |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Vì quy trình xử lý claim LogiX-VN chủ yếu tuần tự (`get_claim_view` → `lookup_order` → `compute_compensation` → `issue_refund`) và tiền do code tính, chuyển từ `workflow` / `single` sang `orchestrator` (thêm bước lập kế hoạch và investigator) sẽ giữ nguyên `pass_rate = 1.000` nhưng làm `cost_per_success_vnd` tăng khoảng 40–100% do thêm model call lập kế hoạch và tool call đọc |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Giữ cố định: `MockLLM`, tập read/write tools (`lab8.tools`, `durability.issue_refund`), seeds `11,22,33,44,55`, corpus `data/public_claims.jsonl` (14 claims), bảng giá `config/pricing.yaml`, evaluator `lab8.metrics.trial_pass`. Biến duy nhất thay đổi: topology xử lý (`workflow` vs `single` vs `orchestrator`) |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Overhead phối hợp dư thừa (thêm bước lập kế hoạch, handoff và `lookup_policy` / `lookup_refund_history` không làm tăng độ chính xác). Đo bằng `pass_rate`, `pass_5`, `seed_variance`, `cost_per_success_vnd`, `mean_steps`, `mean_model_calls`, `mean_tool_calls` và chi phí chênh lệch trong `reports/ablation_r1.json` |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes workflow,single,orchestrator --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/ablation_r1.json` (chạy trong `src/`)
- Run id / file report: `src/reports/ablation_r1.json` (210 trial; ví dụ đại diện: `R-workflow-C-001-s11`, `R-single-C-001-s11`, `R-orchestrator-C-001-s11`)
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: Đúng với hypothesis. Trên 70 trial mỗi shape (14 claim × 5 seed), `workflow` đạt `pass_rate = 1.000`, `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost_per_success = 28.79 VND`, `mean_steps = 3.79` (`mean_model_calls = 1.00`, `mean_tool_calls = 2.79`); `single` đạt `pass_rate = 1.000`, `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost_per_success = 39.34 VND`, `mean_steps = 6.29` (`mean_model_calls = 5.64`, `mean_tool_calls = 3.64`); `orchestrator` đạt `pass_rate = 1.000`, `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost_per_success = 57.00 VND` (+98.0% so với `workflow`, +44.9% so với `single`), `mean_steps = 3.43` (`mean_model_calls = 1.93`, `mean_tool_calls = 5.57`). Khác với mức giảm 39–70% accuracy ở LLM thật vì logic tính tiền của LogiX-VN nằm trong code (`compute_compensation`), nhưng hoàn toàn nhất quán với kết luận của nguồn rằng thêm tầng multi-agent cho tác vụ tuần tự khi baseline đã cao không đem lại cải thiện độ chính xác mà chỉ đội chi phí.
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`; bộ `public_claims.jsonl` chỉ gồm 14 claim tổng hợp và toàn bộ nhánh quyết định tiền/chính sách đều cố định bằng code.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
