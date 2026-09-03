import socket
import threading
import json

from common.protocol import (
    receive_message, 
    send_message, 
    CMD_REQ_CONNECT, 
    CMD_RES_CONNECT, 
    CMD_MOUSE, 
    CMD_KEY,
    CMD_AUTH_REQ,    # Lệnh do TV1 định nghĩa thêm
    CMD_AUTH_RES     # Lệnh do TV1 định nghĩa thêm
)
from server.input_executor import process_input_command
from server.screen_stream import screen_stream 

# =========================================================
# LÕI XÁC THỰC CỦA TV3
# =========================================================
def verify_credentials(input_id, input_pass):
    """
    TV3: Hàm kiểm tra tính hợp lệ của tài khoản kết nối.
    Hiện tại đang fix cứng ID: 123456, Pass: 1234 để test luồng.
    Sau này sẽ lấy biến trực tiếp từ giao diện của TV5.
    """
    if input_id == "123456" and input_pass == "1234":
        return True
    return False

# =========================================================
# LÕI ĐIỀU PHỐI MẠNG CỦA TV1 (TRƯỞNG NHÓM)
# =========================================================
def start_server(ip="0.0.0.0", port=9999, on_connection_request=None):
    # 1. Khởi tạo Socket TCP lắng nghe kết nối
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Bổ sung cờ SO_REUSEADDR để tránh lỗi WinError 10048 khi khởi động lại server liên tục
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    server.bind((ip, port))
    server.listen(1)
    print(f"[SERVER] Đang lắng nghe tại {ip}:{port}...")

    # 2. Chấp nhận kết nối từ Client
    client_socket, client_address = server.accept()
    print(f"[SERVER] Đã kết nối với {client_address}")

    # 3. Chờ gói tin Xác thực từ Client
    cmd, payload = receive_message(client_socket)
    
    if cmd == CMD_AUTH_REQ:
        # 3.1. Bóc tách JSON do TV6 gửi từ Client
        try:
            auth_data = json.loads(payload.decode('utf-8'))
            input_id = auth_data.get("id", "")
            input_pass = auth_data.get("password", "")
            client_ip = auth_data.get("ip", client_address[0])
            print(f"[SERVER] Nhận yêu cầu xác thực từ IP: {client_ip} | ID: {input_id}")
        except Exception as e:
            print(f"[SERVER] Lỗi giải mã gói tin xác thực: {e}")
            client_socket.close()
            server.close()
            return

        # 3.2. Gọi module của TV3 để đối chiếu
        is_valid = verify_credentials(input_id, input_pass)
        
        if is_valid:
            # 3.3. Nếu đúng ID/Pass -> Phản hồi mã 1
            send_message(client_socket, CMD_AUTH_RES, bytearray([1]))
            print("[SERVER] Xác thực THÀNH CÔNG. Bắt đầu truyền hình ảnh!")
            
            # Kích hoạt luồng truyền hình ảnh của TV2 (chạy ngầm để không đơ mạng)
            stream_thread = threading.Thread(
                target=screen_stream,
                args=(client_socket,),
                daemon=True
            )
            stream_thread.start()

            # Vòng lặp nhận và xử lý lệnh điều khiển (chuột/phím)
            while True:
                try:
                    msg_cmd, msg_payload = receive_message(client_socket)
                    if not msg_cmd:
                        break
                    
                    if msg_cmd in (CMD_MOUSE, CMD_KEY):
                        process_input_command(msg_cmd, msg_payload)
                        
                except Exception as e:
                    print(f"[SERVER] Lỗi phiên kết nối: {e}")
                    break
        else:
            # 3.4. Nếu sai ID/Pass -> Phản hồi mã 0 và ngắt kết nối ngay
            send_message(client_socket, CMD_AUTH_RES, bytearray([0]))
            print("[SERVER] Xác thực THẤT BẠI. Từ chối kết nối!")
            
    else:
        print("[SERVER] Gói tin đầu tiên không phải là lệnh xác thực. Hủy kết nối!")
        
    # 4. Dọn dẹp tài nguyên khi kết thúc
    client_socket.close()
    server.close()
    print("[SERVER] Đã đóng Server.")

if __name__ == "__main__":
    start_server()