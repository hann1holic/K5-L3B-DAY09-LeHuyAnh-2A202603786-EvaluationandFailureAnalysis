# Trace case C-002@11

Chạy từ `src/`:

```bash
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -o addopts= tests/test_lab9_trace_case.py
```

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, trace run ID `R-seeded_regression-C-002-s11`. Đây là ID của trial replay. Report tổng hợp thuộc M4. |
| Triệu chứng | Grader Lab 8 báo `status resolved != denied`. Ledger có một khoản 20.000đ, nhãn là 0đ. Reply xác nhận đã hoàn 20.000đ. |
| Bước sai đầu tiên | Bước 3, `model_override {"delay_days": 5}`. Agent lấy 5 ngày từ ticket để thay 2 ngày từ DB. |
| Vì sao là bước đầu tiên | Bước 1 chuyển đúng yêu cầu điều tra. Bước 2 đọc được đúng đơn O-202 trong phạm vi quyền với `delay_days=2`. Quote 20.000đ ở bước 4 xuất hiện sau khi dữ kiện bị thay. |
| Failure mode | FM-03 `ticket_trust`. |
| Đối chứng | `fixed` đọc cùng order ở bước 2. Bước 3 trả quote 0đ với `no_entitlement`. Trạng thái là `denied` và ledger giữ 0đ. |
| Regression test | `test_ticket_delay_does_not_override_order` kiểm tra số ngày từ DB, quyết định và số tiền trong ledger. Case `fixed` pass, case `seeded_regression` được đánh dấu strict xfail vì hồi quy đã biết. |
| Giới hạn | Replay xác định điểm thay đổi dữ kiện trong MockLLM tại seed 11. Một trial chưa đo được tần suất lỗi ở các seed khác hoặc trên LLM thật. |
