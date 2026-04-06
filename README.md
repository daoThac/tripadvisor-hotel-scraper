# TripAdvisor Hotel Scraper (Hue Province)

Dự án này chứa đoạn mã tự động (bot) chuyên dùng để trích xuất thông tin khách sạn và các bình luận đánh giá trực tiếp từ TripAdvisor, khu vực Thừa Thiên Huế.

## Yêu cầu cài đặt
Sử dụng Python 3.9+ và chạy lệnh sau để cài thư viện:
```bash
pip install -r requirements.txt
playwright install
```

## Cách sử dụng
Mở Terminal và khởi chạy công cụ crawler:
```bash
python hotel_scraper.py
```
> **Lưu ý:** Bot sẽ tự động thực hiện 2 quy trình tuần tự:
> - **Bước 1:** Quét và lọc thông minh hàng ngàn khách sạn, lưu lại thông tin gốc vào `hotels_hue_summary.csv`. Quá trình quét đi kèm màng lọc URL loại bỏ hoàn toàn các khách sạn rác ngoài vùng lãnh thổ Huế.
> - **Bước 2:** Truy cập từng khách sạn, lấy đánh giá từ tháng 1 năm 2025 trở đi và lưu dồn vào `hotels_hue_reviews_jan2025.csv`.

Dự án này đã được tối ưu để hoạt động xuyên suốt bằng công nghệ ngầm của Playwright. Cấu trúc lưu nối tiếp cho phép hệ thống "nhớ" tiến độ — nếu mất mạng, chạy lại lệnh một lần nữa và bot sẽ tự lấy dữ liệu tiếp tục từ chỗ bị đứt mà không bị ghi đè.
