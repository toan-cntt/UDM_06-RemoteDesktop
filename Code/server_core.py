import socket
from common.protocol import receive_message, send_message, CMD_REQ_CONNECT, CMD_RES_CONNECT, CMD_MOUSE, CMD_KEY
from server.input_executor import process_input_command

def start_server(ip="0.0.0.0", port=9999):
    # Khởi tạo Socket TCP
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((ip, port))
    server.listen(1) # Chỉ cho phép 1 kết nối chờ
    print(f"[SERVER] Đang lắng nghe tại {ip}:{port}...")

    # Chấp nhận kết nối
    client_socket, client_address = server.accept()
    print(f"[SERVER] Đã kết nối với {client_address}")

    # Chờ lệnh xin phép kết nối từ Client
    cmd, payload = receive_message(client_socket)
    
    if cmd == CMD_REQ_CONNECT:
        print("[SERVER] Có người muốn xem màn hình!")
        # (Sau này sẽ gọi GUI bật popup Yes/No ở đây)
        
        # Tạm thời fix cứng là Đồng ý (Gửi mã 1)
        # Bọc mã 1 thành bytes: bytearray([1])
        send_message(client_socket, CMD_RES_CONNECT, bytearray([1]))
        print("[SERVER] Đã cho phép. Bắt đầu phiên!")

        # Vòng lặp nhận dữ liệu điều khiển (chuột, phím) liên tục
        while True:
            try:
                msg_cmd, msg_payload = receive_message(client_socket)
                if not msg_cmd:
                    break
                print(f"[SERVER] Nhận lệnh {msg_cmd} có kích thước {len(msg_payload)} bytes")
                if msg_cmd in (CMD_MOUSE, CMD_KEY):
                    process_input_command(msg_cmd, msg_payload)
            except Exception as e:
                print(f"[SERVER] Lỗi: {e}")
                break

    client_socket.close()
    server.close()

if __name__ == "__main__":
    start_server()