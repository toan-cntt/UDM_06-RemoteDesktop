import socket
import threading

from common.protocol import receive_message, CMD_SCREEN
from server.screen_stream import send_screen

HOST = "127.0.0.1"
PORT = 9998

def receiver(server_socket):
    # Chờ kết nối từ bên gửi
    conn, address = server_socket.accept()

    print("[TEST] Đã nhận kết nối từ:", address)

    # Nhận một message
    cmd, payload = receive_message(conn)

    if cmd == CMD_SCREEN:
        print("[TEST] Nhận được ảnh màn hình!")
        print("[TEST] Kích thước ảnh:", len(payload), "bytes")
    else:
        print("[TEST] Sai mã lệnh:", cmd)

    conn.close()

# Tạo TCP server để test
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(1)

print("[TEST] Server đang chờ kết nối...")

# Chạy receiver ở thread riêng
thread = threading.Thread(
    target=receiver,
    args=(server_socket,)
)

thread.start()

# Tạo TCP client
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))

print("[TEST] Client đã kết nối!")

# Chụp màn hình và gửi 1 frame
import mss

# Khởi tạo đối tượng chụp màn hình và truyền vào hàm
with mss.MSS() as sct:
    send_screen(sct, client_socket, quality=70)

print("[TEST] Đã gửi ảnh!")

client_socket.close()
thread.join()
server_socket.close()

print("[TEST] Hoàn thành!")