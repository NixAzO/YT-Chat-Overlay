# YouTube Live Chat Overlay

Ứng dụng hiển thị khung chat livestream YouTube lên màn hình với nền trong suốt, hỗ trợ đọc tin nhắn (TTS) và dịch thuật.

## Tính năng

- Hiển thị chat YouTube trên màn hình (Overlay) với nền trong suốt.
- Đọc tin nhắn tự động bằng giọng chị Google (TTS).
- Dịch tin nhắn tự động (Anh sang Việt hoặc Việt sang Anh).
- Tự động chuyển đổi từ lóng (slang) thành câu hoàn chỉnh trước khi dịch.
- Nổi bật tin nhắn của Hội viên (Member) và Super Chat.
- Bộ lọc từ cấm (Blacklist).
- Tự động tìm link livestream từ link kênh.
- Tùy chỉnh giao diện: cỡ chữ, độ mờ, màu sắc, tốc độ hiển thị.

## Cách cài đặt

1. Cài đặt Python 3.x trên máy tính của bạn (nếu muốn chạy bằng source code).
2. Tải thư mục này về máy.
3. Mở Terminal (Cmd/PowerShell) tại thư mục vừa tải.
4. Cài đặt các thư viện cần thiết bằng lệnh (nếu chạy bằng source code):
   pip install -r requirements.txt

## Cách sử dụng

1. Cách đơn giản nhất: Chạy file `YouTubeChatOverlay.exe`.
   
2. Hoặc chạy bằng Python (nếu muốn chỉnh sửa code):
   python youtube_chat_overlay.py

3. Một cửa sổ sẽ hiện ra yêu cầu nhập Link.
   - Bạn có thể nhập Link Video Livestream trực tiếp.
   - Hoặc nhập Link Kênh (Channel) YouTube, ứng dụng sẽ tự tìm livestream đang phát.

4. Sau khi kết nối thành công, khung chat sẽ hiện ra.
   - Kéo thả ở nút "::" để di chuyển khung chat.
   - Nhấn nút bánh răng để mở Cài đặt (Settings).
   - Nhấn nút "-" để ẩn xuống khay hệ thống.

## Cấu hình nâng cao

- File `slang.json`: Chứa danh sách các từ lóng (slang) cần thay thế. Bạn có thể mở bằng Notepad để thêm/sửa.
- File `blacklist.txt`: Chứa danh sách các từ cấm. Tin nhắn chứa từ này sẽ bị ẩn.
