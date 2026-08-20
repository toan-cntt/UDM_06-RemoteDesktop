# UDM 06 - Remote Desktop

## 1. Thông tin nhóm

| STT | Họ và tên | MSSV |
| --- | --- | --- |
| 1 | Trần Tấn Toàn | 060206001984 |
| 2 | Trần Hà Đức Huỳnh | 075206023506 |
| 3 | Nguyễn Đăng Triều | 082206000518 |
| 4 | Lê Ly Na | 051305008114 |
| 5 | Phan Minh Thu | 087306015281 |
| 6 | Lương Thành Đạt | 056206003075 |

**Môn:** Lập trình mạng  
**Mã lớp:** 012012301303  
**Đề tài:** UDM_06 - Remote Desktop

---

## 2. Giới thiệu

Đề tài xây dựng ứng dụng **Remote Desktop** cho phép Client kết nối đến Host thông qua giao thức TCP Socket, xem màn hình máy tính từ xa và thực hiện điều khiển máy tính sau khi Host chấp nhận yêu cầu kết nối.

Ứng dụng gồm hai thành phần chính:

- **Host:** khởi động Server, chờ Client kết nối, xác nhận yêu cầu điều khiển và truyền hình ảnh màn hình.
- **Client:** nhập địa chỉ IP và Port, gửi yêu cầu kết nối, nhận và hiển thị màn hình Host theo thời gian thực.

### Các chức năng chính

- Kết nối Client - Host thông qua TCP Socket.
- Host lắng nghe kết nối trên Port được cấu hình.
- Client gửi yêu cầu kết nối đến Host.
- Host hiển thị hộp thoại xác nhận yêu cầu kết nối.
- Host cho phép hoặc từ chối Client.
- Chụp và truyền hình ảnh màn hình Host theo thời gian thực.
- Client giải mã JPEG và hiển thị trên giao diện Remote Viewer.
- Truyền lệnh chuột và bàn phím từ Client đến Host.
- Host thực thi thao tác điều khiển sau khi được cấp quyền.
- Cho phép ngắt kết nối và dừng phiên Remote Desktop.

---

## 3. Công nghệ sử dụng

- Python 3.12
- PyQt5
- TCP Socket
- Threading
- Pillow (PIL)
- MSS
- pynput
- JPEG Screen Streaming

---

## 4. Cấu trúc project

```text
UDM_06-RemoteDesktop/
│
├── Code/
│   ├── client/
│   │   ├── client_gui.py
│   │   └── input_listener.py
│   │
│   ├── common/
│   │   └── protocol.py
│   │
│   ├── server/
│   │   ├── core.py
│   │   ├── input_executor.py
│   │   └── screen_stream.py
│   │
│   ├── client_core.py
│   ├── server_core.py
│   ├── host_gui.py
│   └── test_input_listener.py
│
├── DOCX/
├── EXTRA/
├── PPTX/
├── README.md
└── .gitignore
```

---

## 5. Hướng dẫn cài đặt

### 5.1. Yêu cầu môi trường

- Windows
- Python 3.12
- Git

Kiểm tra Python:

```bash
py -3.12 --version
```

### 5.2. Cài đặt thư viện

Mở Terminal tại thư mục `Code` và chạy:

```bash
py -3.12 -m pip install PyQt5 Pillow mss pynput
```

---

## 6. Hướng dẫn chạy ứng dụng

### 6.1. Khởi động Host

Mở Terminal tại:

```text
UDM_06-RemoteDesktop\Code
```

Chạy:

```bash
py -3.12 host_gui.py
```

Giao diện **REMOTE DESKTOP - HOST** sẽ xuất hiện.

Nhấn:

```text
START HOST
```

Host sẽ bắt đầu lắng nghe Client trên Port:

```text
9999
```

---

### 6.2. Khởi động Client

Mở một Terminal khác tại:

```text
UDM_06-RemoteDesktop\Code
```

Chạy:

```bash
py -3.12 -m client.client_gui
```

Giao diện **Remote Desktop Client** sẽ xuất hiện.

Nhập:

```text
IP: 127.0.0.1
Port: 9999
```

Sau đó nhấn:

```text
Kết nối
```

---

## 7. Quy trình kết nối

```text
Client
   │
   │ TCP Connection
   ▼
Host Server
   │
   │ Connection Request
   ▼
Host GUI
   │
   ├── TỪ CHỐI ──► Client bị từ chối
   │
   └── CHẤP NHẬN
          │
          ▼
   Remote Control Active
          │
          ├── Screen Streaming
          │
          └── Mouse / Keyboard Control
                    │
                    ▼
                  Client
```

---

## 8. Screen Streaming

Sau khi Host chấp nhận Client:

1. Host chụp màn hình bằng MSS.
2. Hình ảnh được xử lý bằng Pillow.
3. Hình ảnh được mã hóa thành JPEG.
4. Dữ liệu JPEG được truyền qua TCP Socket.
5. Client nhận dữ liệu.
6. Client giải mã JPEG.
7. Client cập nhật hình ảnh lên Remote Viewer.

Luồng truyền màn hình được thực hiện trên Thread riêng để không làm giao diện bị treo.

---

## 9. Remote Control

Sau khi Host cấp quyền điều khiển, Client có thể gửi:

- Sự kiện chuột.
- Sự kiện bàn phím.

Host nhận command thông qua TCP Socket và chuyển đến module xử lý input để thực thi trên máy Host.

---

## 10. Phân công thành viên

### Thành viên 1 - Trần Tấn Toàn

- Xây dựng Core Network.
- Thiết kế giao tiếp TCP Socket.
- Xây dựng protocol giao tiếp giữa Client và Server.
- Tích hợp các module vào luồng chính.

### Thành viên 2 - Trần Hà Đức Huỳnh

- Xây dựng chức năng thực thi input trên Host.
- Xử lý sự kiện chuột và bàn phím.
- Kiểm thử chức năng điều khiển từ xa.

### Thành viên 3 - Nguyễn Đăng Triều

- Xây dựng chức năng nhận input từ Client.
- Xử lý Mouse / Keyboard event.
- Kiểm thử Input Listener.

### Thành viên 4 - Lê Ly Na

- Xây dựng chức năng chụp màn hình.
- Xây dựng Screen Streaming.
- Xử lý truyền hình ảnh qua Socket.

### Thành viên 5 - Phan Minh Thu

- Xây dựng giao diện Host.
- Xử lý trạng thái kết nối.
- Xử lý yêu cầu cho phép / từ chối kết nối.
- Tích hợp Host GUI với Server.

### Thành viên 6 - Lương Thành Đạt

- Xây dựng giao diện Client.
- Xây dựng Remote Viewer.
- Nhận và hiển thị hình ảnh màn hình từ Host.
- Xử lý luồng cập nhật giao diện.
- Chuẩn bị tài liệu, README và nội dung trình bày.

---

## 11. Kiểm thử

Ứng dụng được kiểm thử với Client và Host chạy trên cùng máy:

```text
IP: 127.0.0.1
Port: 9999
```

Các chức năng kiểm thử:

- Khởi động Host.
- Client kết nối đến Host.
- Host nhận yêu cầu kết nối.
- Host chấp nhận / từ chối Client.
- Truyền hình ảnh màn hình.
- Hiển thị Remote Screen trên Client.
- Gửi thao tác chuột.
- Gửi thao tác bàn phím.
- Ngắt kết nối Client.
- Khởi động lại Host.

---

## 12. Tài liệu

Các tài liệu của đề tài được lưu trong:

```text
DOCX/
EXTRA/
PPTX/
```

Bao gồm:

- Báo cáo Word.
- Slide thuyết trình.
- Các tài liệu và file liên quan đến đề tài.

---

## 13. Video Demo

Video demo ứng dụng Remote Desktop:

> Thêm link video demo của nhóm tại đây.

---

## 14. Lưu ý

Host phải được khởi động trước Client.

Khi kiểm thử trên cùng máy:

```text
Host IP: 127.0.0.1
Client kết nối đến: 127.0.0.1
Port: 9999
```

Nếu kiểm thử giữa hai máy trong cùng mạng LAN, Client cần sử dụng địa chỉ IP LAN của máy Host thay vì `127.0.0.1`.