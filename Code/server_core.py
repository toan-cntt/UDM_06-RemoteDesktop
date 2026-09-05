import socket
import threading
import json
import time

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

# Chỉ import hàm verify_credentials, nhường quyền init cho Host GUI
from server.auth import verify_credentials

current_client_socket = None
current_server_socket = None

def start_server(ip="0.0.0.0", port=9999, on_connection_request=None, stop_event=None):   
    global current_client_socket
    global current_server_socket

    # =====================================================
    # 1. KHỞI TẠO LỖI SERVER
    # =====================================================
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    current_server_socket = server

    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((ip, port))
    server.listen(1)
    server.settimeout(1.0)
    print(f"[SERVER] Đang lắng nghe tại {ip}:{port}...")

    # =====================================================
    # 2. VÒNG LẶP TỔNG: LUÔN SẴN SÀNG ĐÓN CLIENT MỚI
    # =====================================================
    while True:
        if stop_event and stop_event.is_set():
            print("[SERVER] Nhận yêu cầu dừng server.")
            break

        # Chờ Client gõ cửa
        try:
            client_socket, client_address = server.accept()
            current_client_socket = client_socket
            print(f"[SERVER] Đã kết nối với {client_address}")
            client_socket.settimeout(1.0)
        except socket.timeout:
            continue
        except OSError:
            print("[SERVER] Socket server đã được đóng.")
            break

        # =====================================================
        # 3. VÒNG LẶP CON: XỬ LÝ RIÊNG CHO CLIENT NÀY
        # =====================================================
        client_connected = True
        while client_connected:
            if stop_event and stop_event.is_set():
                print("[SERVER] Nhận yêu cầu ngắt khẩn cấp từ giao diện.")
                client_connected = False
                break

            try:
                cmd, payload = receive_message(client_socket)
                if not cmd:
                    continue
                
                # --- LUỒNG XÁC THỰC ĐỘNG ---
                if cmd == CMD_AUTH_REQ:
                    auth_data = json.loads(payload.decode("utf-8"))
                    input_id = auth_data.get("id", "")
                    input_password = auth_data.get("password", "")
                    client_ip = auth_data.get("ip", client_address[0])
                    
                    print(f"[SERVER] Nhận yêu cầu xác thực từ IP: {client_ip} | ID: {input_id}")
                    
                    # Đối chiếu với ID/Pass đang hiển thị trên giao diện Host
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
                        client_connected = False  # Đuổi Client này, quay lại vòng lặp tổng để chờ Client khác
                        break 

                # --- LUỒNG ĐIỀU KHIỂN CHUỘT/PHÍM ---
                elif cmd in (CMD_MOUSE, CMD_KEY):
                    process_input_command(cmd, payload)

            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                print(f"[SERVER] Client đã mất kết nối: {e}")
                client_connected = False
                break
            except Exception as e:
                print(f"[SERVER] Lỗi phiên kết nối: {e}")
                client_connected = False
                break

        # Đóng riêng cửa của Client cũ, không đóng sập cả Server
        try:
            client_socket.shutdown(socket.SHUT_RDWR)
            client_socket.close()
        except:
            pass
        current_client_socket = None

    # Dọn dẹp triệt để khi Host bấm STOP
    try:
        server.close()
    except:
        pass
    current_server_socket = None
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