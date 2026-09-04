import socket
import threading
import json

# Giữ nguyên các import bắt buộc đã có từ đầu dự án
from common.protocol import (
    receive_message, 
    send_message, 
    CMD_MOUSE, 
    CMD_KEY,
    CMD_AUTH_REQ,
    CMD_AUTH_RES
)
from server.input_executor import process_input_command
from server.screen_stream import screen_stream

current_client_socket = None
current_server_socket = None

# =========================================================
# LÕI XÁC THỰC (Đưa trực tiếp vào file chính)
# =========================================================
def verify_credentials(input_id, input_pass, client_ip=None):
    """
    Kiểm tra tính hợp lệ của tài khoản kết nối.
    Tạm thời fix cứng ID: 123456, Pass: 1234 để test luồng.
    """
    if input_id == "123456" and input_pass == "1234":
        return True
    return False

# =========================================================
# LÕI ĐIỀU PHỐI MẠNG
# =========================================================
def start_server(ip="0.0.0.0", port=9999, on_connection_request=None, stop_event=None):   
    global current_client_socket
    global current_server_socket

    # 1. Khởi tạo Socket TCP lắng nghe kết nối
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    current_server_socket = server

    # Cho phép sử dụng lại port
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((ip, port))
    server.listen(1)
    
    # Timeout để server liên tục nhả luồng kiểm tra stop_event
    server.settimeout(1.0)
    print(f"[SERVER] Đang lắng nghe tại {ip}:{port}...")

    # 2. Vòng lặp chờ Client kết nối
    while True:
        if stop_event and stop_event.is_set():
            print("[SERVER] Nhận yêu cầu dừng server.")
            server.close()
            return

        try:
            client_socket, client_address = server.accept()
            current_client_socket = client_socket
            break
        except socket.timeout:
            continue
        except OSError:
            print("[SERVER] Socket server đã được đóng.")
            return

    print(f"[SERVER] Đã kết nối với {client_address}")
    client_socket.settimeout(1.0)

    # 3. Vòng lặp xử lý Gói tin & Xác thực
    while True:
        if stop_event and stop_event.is_set():
            print("[SERVER] Nhận yêu cầu ngắt khẩn cấp từ giao diện.")
            break

        try:
            cmd, payload = receive_message(client_socket)
            if not cmd:
                continue
            
            # --- LUỒNG XÁC THỰC ---
            if cmd == CMD_AUTH_REQ:
                auth_data = json.loads(payload.decode("utf-8"))
                input_id = auth_data.get("id", "")
                input_password = auth_data.get("password", "")
                client_ip = auth_data.get("ip", client_address[0])
                
                print(f"[SERVER] Nhận yêu cầu xác thực từ IP: {client_ip} | ID: {input_id}")
                
                is_valid = verify_credentials(input_id, input_password, client_ip=client_ip)
                
                if is_valid:
                    send_message(client_socket, CMD_AUTH_RES, bytearray([1]))
                    print("[SERVER] Xác thực THÀNH CÔNG. Bắt đầu truyền hình ảnh!")
                    
                    stream_thread = threading.Thread(
                        target=screen_stream,
                        args=(client_socket,),
                        kwargs={"stop_event": stop_event},
                        daemon=True
                    )
                    stream_thread.start()
                else:
                    send_message(client_socket, CMD_AUTH_RES, bytearray([0]))
                    print("[SERVER] Xác thực THẤT BẠI. Từ chối kết nối!")
                    break  # Sai pass thì văng vòng lặp, đóng kết nối

            # --- LUỒNG ĐIỀU KHIỂN CHUỘT/PHÍM ---
            elif cmd in (CMD_MOUSE, CMD_KEY):
                process_input_command(cmd, payload)

        except socket.timeout:
            continue
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"[SERVER] Client đã mất kết nối: {e}")
            break
        except Exception as e:
            print(f"[SERVER] Lỗi phiên kết nối: {e}")
            break

    # 4. Dọn dẹp tài nguyên
    try:
        client_socket.shutdown(socket.SHUT_RDWR)
        client_socket.close()
    except:
        pass
    try:
        server.close()
    except:
        pass
    print("[SERVER] Đã giải phóng socket.")   

def stop_server():
    global current_client_socket
    global current_server_socket
    print("[SERVER] Đang thực hiện STOP SERVER...")

    if current_client_socket:
        try:
            current_client_socket.shutdown(socket.SHUT_RDWR)
            current_client_socket.close()
        except:
            pass
        current_client_socket = None

    if current_server_socket:
        try:
            current_server_socket.close()
        except:
            pass
        current_server_socket = None

    print("[SERVER] Đã ngắt kết nối và giải phóng socket.")

if __name__ == "__main__":
    start_server()