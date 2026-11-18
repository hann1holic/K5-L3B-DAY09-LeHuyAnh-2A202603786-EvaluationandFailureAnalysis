# Eval card — LogiX-VN refund agent

## Core · eval set v1

Eval set `c3b7dbf0523a` gồm 14 claim public Lab 8, chạy với seed 11, 22, 33, 44 và 55. Nhãn chuẩn nằm ở `src/data/eval/labels_v1.json`. Báo cáo dùng MockLLM, Python 3.13.2 và metric spec 1.0. Grader và báo cáo đi cùng bản mã của bài nộp.

| Metric | Gate v1 | Baseline swarm | fixed | seeded_regression |
|---|---|---:|---:|---:|
| approval_bypass | ≤ 0 | 0 | 0 | 0 |
| secret_leak | ≤ 0 | 0 | 0 | 0 |
| refund_amount_correct | ≥ 0,95 và CI | 0,9857 | 1,0000 | 0,8571 |
| pass_rate | ≥ 0,85 và CI | 0,9857 | 1,0000 | 0,7143 |
| reply_ledger_correct | 1,00 | 1,0000 | 1,0000 | 0,7857 |
| db_fact_kept | Theo dõi, sàn 0,95 | 0,9857 | 1,0000 | 0,9286 |
| proposal_amount_correct | Theo dõi, sàn 0,95 | 0,9857 | 1,0000 | 0,7857 |
| pass_5 | Theo dõi, sàn 0,80 | 0,9286 | 1,0000 | 0,7143 |
| cost_per_success | Cảnh báo nếu tăng trên 10% | 49,5670 | 48,7157 | 81,2020 |

| Báo cáo do script sinh | Run ID | Δ pass_rate so với swarm và CI 95% | Gate |
|---|---|---|---|
| `baseline_v1.json` | `E-swarm-20261118-c3b7` | 0,000 [0,000; 0,000] | exit 0 |
| `eval_fixed.json` | `E-fixed-20261118-c3b7` | +0,014 [0,000; +0,043] | exit 0 |
| `eval_seeded_regression.json` | `E-seeded_regression-20261118-c3b7` | −0,271 [−0,500; −0,057] | exit 1 |

CI dùng paired bootstrap percentile trên cùng item sau khi lấy trung bình theo seed, với 1.000 lần lấy mẫu lại. `lab9.mutation --detect` giải thích 100% trial sai của `seeded_regression` và báo nhầm 0% trên `fixed`. Baseline `swarm` thiếu event reply nên metric FM-08 ghi qua đối với các trial đó. Các biến thể có reply được kiểm bằng số tiền đã ghi trong ledger.

Judge tone qua calibration (κ 0,757, precision 0,857, recall 0,800). Helpful bị loại vì recall 0,300 và κ 0,375. Tiền và approval do code chấm. Xem [audit](judge_audit.md) và [trace case C-002@11](trace_case.md), nơi bước 3 ghi đè số ngày của DB.

## Advanced và Expert · eval set v2

Eval set `b23656a90464` có 28 claim × 5 seed, gồm 14 claim public và 14 claim adversarial. Metric spec 2.0 giữ gate FM-08 và thêm các slice cùng `pass_hat_5`.

| Replay | Run ID | pass_rate | pass_hat_5 | Kết quả |
|---|---|---:|---:|---|
| swarm | `E-swarm-20261118-b236` | 0,9786 | 0,8929 | Qua khi đối chiếu chính nó |
| slice_regression | `E-slice_regression-20261118-b236` | 0,9357 | 0,8929 | Chặn riêng ở `money_movement` |
| flaky_regression | `E-flaky_regression-20261118-b236` | 0,9143 | 0,5714 | Chặn ở `pass_hat_5`, CI của pass_rate và `money_movement` |

- `money_movement` có sàn 0,95. `slice_regression` đạt 0,85 trên lát cắt này. Pass rate toàn bộ 0,9357 vẫn trên sàn 0,85 và CI của Δ toàn bộ [−0,121; +0,029] chứa 0.
- `adversarial` có sàn 0,90 và chặn khi CI xét riêng lát cắt nằm hoàn toàn dưới 0. Tiêu chí này giữ độ nhạy với các lỗi tập trung vào mẫu adversarial. `seeded_regression` cũng bị chặn ở lát cắt này.
- A/A của swarm trên seed 11/22/33/44/55 và 66/77/88/99/110 cho Δ = 0 trên mọi metric báo cáo. Cả hai bộ đều cho `pass_hat_5` = 0,8929. Sàn 0,80 thấp hơn cả hai lần đo và chặn được `flaky_regression` ở 0,5714. Cần đo nhiều cặp A/A với LLM thật để ước lượng nhiễu trước khi áp dụng sàn.
- Với 5 seed, bug hiếm xuất hiện khoảng 1/3 seed có thể lọt hoặc cho tín hiệu thiếu ổn định. `pass@k` đo có ít nhất một lần pass, còn `pass^k` đo cả k lần đều pass. `flaky_regression` đạt `pass_at_5` = 1,0000 dù `pass_hat_5` chỉ là 0,5714.

## Bằng chứng cho PR

```text
v1 seeded_regression: exit 1 — blocked: refund_amount_correct, pass_rate, reply_ledger_correct
v2 fixed: merge
v2 honest_refactor: merge
v2 seeded_regression: block
v2 slice_regression: block (slice:money_movement/pass_rate)
v2 flaky_regression: block (pass_rate, pass_hat_5, slice:money_movement/pass_rate)
mutation score 3/3 · false alarms 0
A/A: Δ +0.0000 cho mọi metric trên hai bộ seed
evaluator_errors_as_nan: exit 1 — blocked: integrity
dropped_failing_rows: exit 1 — blocked: integrity
cherry_picked_seeds: exit 1 — blocked: integrity
loosened_spec: exit 1 — blocked: integrity
```

## Phạm vi và giới hạn

Lê Huy Anh giữ gate bài Lab 9. Pilot chỉ chạy offline trên các claim mô phỏng. Core có 14 item và v2 có 28 item, nên CI có thể rộng và hồi quy nhỏ dễ lọt. Judge replay dựa trên CSV công khai. Cần dữ liệu có nhãn held-out và đo trên LLM thật trước khi dùng cho giao dịch thực. Khi đổi item, nhãn hoặc cách chia slice, tăng eval-set version và chạy lại baseline. Thay đổi ngưỡng trong cùng phiên bản theo ratchet.
