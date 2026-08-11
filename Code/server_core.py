import socket
import threading
from common.protocol import (
    receive_message, 
    send_message, 
    CMD_REQ_CONNECT, 
    CMD_RES_CONNECT, 
    CMD_MOUSE, 
    CMD_KEY
)
from server.input_executor import process_input_command
from server.screen_stream import screen_stream  # Hàm chụp & truyền ảnh chuẩn của TV2

def start_server(ip="0.0.0.0", port=9999, on_connection_request=None):
    # 1. Khởi tạo Socket TCP lắng nghe kết nối[cite: 5]
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((ip, port))
    server.listen(1)
    print(f"[SERVER] Đang lắng nghe tại {ip}:{port}...")

    # 2. Chấp nhận kết nối từ Client[cite: 5]
    client_socket, client_address = server.accept()
    print(f"[SERVER] Đã kết nối với {client_address}")

    # 3. Chờ lệnh xin phép kết nối từ Client[cite: 5]
    cmd, payload = receive_message(client_socket)
    
    if cmd == CMD_REQ_CONNECT:
        print("[SERVER] Có người muốn xem màn hình!")
        
        # Gọi Callback lên GUI của TV5 để bật Pop-up[cite: 5]
        if on_connection_request:
            result = on_connection_request(client_address[0])
        else:
            result = False  # Không có GUI thì mặc định TỪ CHỐI[cite: 5]

        if result:
            # GUI CHẤP NHẬN: Phản hồi về Client[cite: 5]
            send_message(
                client_socket,
                CMD_RES_CONNECT,
                bytearray([1])
            )
            print("[SERVER] Đã cho phép. Bắt đầu phiên!")

            # =========================================================
            # MODULE TV2: KÍCH HOẠT TRUYỀN HÌNH ẢNH (THREAD RIÊNG)
            # =========================================================
            stream_thread = threading.Thread(
                target=screen_stream,
                args=(client_socket,),
                daemon=True
            )
            stream_thread.start()
            print("[SERVER] Luồng truyền hình ảnh TV2 đã được kích hoạt thành công!")
            # =========================================================

            # =========================================================
            # MODULE TV3: VÒNG LẶP NHẬN & THỰC THI LỆNH ĐIỀU KHIỂN
            # =========================================================
            while True:
                try:
                    msg_cmd, msg_payload = receive_message(client_socket)
                    if not msg_cmd:
                        break
                    
                    # Truyền dữ liệu phím/chuột cho TV3 xử lý[cite: 5]
                    if msg_cmd in (CMD_MOUSE, CMD_KEY):
                        process_input_command(msg_cmd, msg_payload)
                        
                except Exception as e:
                    print(f"[SERVER] Lỗi phiên kết nối: {e}")
                    break

        else:
            # GUI TỪ CHỐI: Phản hồi mã 0[cite: 5]
            send_message(
                client_socket,
                CMD_RES_CONNECT,
                bytearray([0])
            )
            print("[SERVER] Đã từ chối kết nối!")

    client_socket.close()
    server.close()

if __name__ == "__main__":
    start_server()