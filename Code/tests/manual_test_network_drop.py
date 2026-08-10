"""
tests/manual_test_network_drop.py
-------------------------------------------------------------------
Kịch bản test THỦ CÔNG: "Rớt mạng giữa chừng" (TC-07 trong Test Plan).

Script này KHÔNG mock gì cả — nó dùng đúng server_core.py / kết nối
TCP thật, để bạn tự chạy trên máy, quan sát Server có bị crash hay
không khi Client đột ngột mất kết nối, rồi CHỤP ẢNH màn hình
Terminal/Console làm bằng chứng bỏ vào thư mục /Extra.

-------------------------------------------------------------------
CÁCH CHẠY (2 cửa sổ Terminal, đứng tại thư mục Code/):
-------------------------------------------------------------------
Cửa sổ 1 (Server):
    python server_core.py

Cửa sổ 2 (script test này, đóng vai Client):
    python tests/manual_test_network_drop.py

Script sẽ:
    1. Kết nối tới Server (giống client_core.py bình thường).
    2. Gửi CMD_REQ_CONNECT, chờ Server đồng ý.
    3. Gửi vài gói CMD_MOUSE/CMD_KEY giả để mô phỏng đang điều khiển.
    4. ĐỘT NGỘT rút dây mạng: gọi socket.close() theo kiểu "rude" -
       set SO_LINGER về 0 để hệ điều hành gửi gói RST thay vì FIN,
       giống hệt việc rút cáp mạng / tắt nguồn máy Client giữa chừng
       (không có bắt tay đóng kết nối 4-way handshake bình thường).

Việc CẦN QUAN SÁT & CHỤP ẢNH lại ở cửa sổ Server:
    - Server KHÔNG được crash / văng traceback không xử lý.
    - Server nên in ra log lỗi (vd "[SERVER] Lỗi: ...") rồi thoát
      vòng lặp nhận lệnh một cách "sạch sẽ", đóng socket, đóng
      chương trình bình thường (hoặc quay lại chờ kết nối mới, tuỳ
      bản server_core.py mà TV1 hoàn thiện).

Ghi kết quả thực tế vào cột "Kết quả thực tế" trong file Excel
Test_Plan.xlsx (TC-07), kèm ảnh chụp màn hình Terminal vào /Extra.
"""

import json
import socket
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.protocol import (
    send_message,
    receive_message,
    CMD_REQ_CONNECT,
    CMD_RES_CONNECT,
    CMD_MOUSE,
)


def main(ip="127.0.0.1", port=9999):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print(f"[TEST] Đang kết nối tới {ip}:{port} ...")
    client.connect((ip, port))
    print("[TEST] Đã kết nối TCP.")

    send_message(client, CMD_REQ_CONNECT)
    cmd, payload = receive_message(client)

    if cmd != CMD_RES_CONNECT or not payload or payload[0] != 1:
        print("[TEST] Server không đồng ý kết nối, dừng test.")
        client.close()
        return

    print("[TEST] Server đã đồng ý. Giả lập gửi vài lệnh điều khiển...")
    for i in range(3):
        move_payload = json.dumps({"action": "move", "x": 0.1 * i, "y": 0.1 * i}).encode()
        send_message(client, CMD_MOUSE, move_payload)
        time.sleep(0.3)

    print("[TEST] Chuẩn bị RÚT DÂY MẠNG đột ngột trong 3 giây...")
    time.sleep(3)

    # Ép hệ điều hành gửi gói RST thay vì bắt tay đóng bình thường (FIN)
    # -> mô phỏng chính xác việc mất kết nối vật lý / tắt máy đột ngột.
    import struct
    l_onoff, l_linger = 1, 0
    client.setsockopt(
        socket.SOL_SOCKET, socket.SO_LINGER,
        struct.pack("ii", l_onoff, l_linger)
    )
    client.close()

    print("[TEST] Đã ngắt kết nối kiểu 'rớt mạng'. Hãy kiểm tra cửa sổ Server ngay bây giờ")
    print("[TEST] và chụp ảnh màn hình lại làm bằng chứng cho thư mục /Extra.")


if __name__ == "__main__":
    main()
