# Judge audit

Dữ liệu replay công khai gồm 100 mẫu mỗi tiêu chí. FAIL là lớp dương. Ngưỡng dùng judge là κ ≥ 0,6, precision ≥ 0,8 và recall ≥ 0,7.

| Tiêu chí | n | κ | Precision | Recall | TP / FP / FN / TN | Tỉ lệ lỗi quan sát → hiệu chỉnh | Quyết định |
|---|---:|---:|---:|---:|---|---|---|
| tone_ok | 100 | 0,757 | 0,857 | 0,800 | 24 / 4 / 6 / 66 | 28% → 30% | Qua calibration, dùng để đánh giá giọng văn. |
| helpful | 100 | 0,375 | 1,000 | 0,300 | 9 / 0 / 21 / 70 | 9% → 30% | Loại khỏi gate vì bỏ sót 21 trong 30 lỗi. |

## Audit bất đồng

| Case | Judge | Người | Đối chiếu và sửa rubric |
|---|---|---|---|
| H-008 | PASS | FAIL | Đồng ý nhãn người. Cụm “rồi nha” và “anh check” quá suồng sã cho thông báo giao dịch. Thêm ví dụ fail với cả câu để judge xét mức độ trang trọng. |
| H-017 | PASS | FAIL | Đồng ý nhãn người với chuẩn CS của LogiX. Gọi “bạn ơi” đi cùng “rồi nha” làm câu thiếu trang trọng. Rubric nên ưu tiên cách xưng hô trung tính “anh/chị” khi thiếu ngữ cảnh. |
| H-029 | PASS | FAIL | Đồng ý nhãn người. “Không cần nhắn thêm” ra lệnh dù câu mở đầu lịch sự. Rubric cần đọc đến câu cuối và chấm lời hướng dẫn mang tính áp đặt là fail. |
| H-042 | FAIL | PASS | Đồng ý nhãn người. Câu lịch sự, nêu kết quả và thời gian nhận tiền. Rubric cho phép câu ngắn và chỉ yêu cầu xin lỗi nếu ngữ cảnh cần. |
| H-051 | FAIL | PASS | Đồng ý nhãn người theo quy ước của bộ dữ liệu. Từ “refund” được chấp nhận trong một câu tiếng Việt lịch sự. Bổ sung các từ nghiệp vụ được phép. |
| HL-015 | PASS | FAIL | Đồng ý nhãn người. Reply ghi 55.000đ, ledger ghi 40.000đ. Kiểm tra số tiền bằng code trước khi đánh giá helpfulness và cho judge xem kết quả giao dịch nếu chấm nội dung. |

Rogan–Gladen hiệu chỉnh tỉ lệ lỗi tổng thể từ độ nhạy và độ đặc hiệu đo được. Hiệu chỉnh 9% → 30% của helpful vẫn để nguyên 21 ca bỏ sót ở mức từng reply. Các đề xuất sửa rubric cần được đo lại trên tập held-out có nhãn người mới trước khi áp dụng.
