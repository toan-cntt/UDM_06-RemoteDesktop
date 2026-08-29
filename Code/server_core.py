import socket
import threading
from common.protocol import (
    receive_message, 
    send_message, 
    CMD_REQ_CONNECT, 
    CMD_RES_CONNECT, 
    CMD_MOUSE, 
    CMD_KEY,
    CMD_AUTH_REQ,
    CMD_AUTH_RES
)
from server.input_executor import process_input_command
from server.auth import verify_credentials
from server.screen_stream import screen_stream  # Hàm chụp & truyền ảnh chuẩn của TV2
current_client_socket = None
current_server_socket = None

def start_server(ip="0.0.0.0", port=9999, on_connection_request=None, stop_event=None):   
    # 1. Khởi tạo Socket TCP lắng nghe kết nối
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    global current_client_socket
    global current_server_socket

    current_server_socket = server

    # Cho phép sử dụng lại port sau khi server được đóng
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server.bind((ip, port))
    server.listen(1)

    # Timeout để server có thể kiểm tra stop_event
    server.settimeout(1.0)

    print(f"[SERVER] Đang lắng nghe tại {ip}:{port}...")

    # 2. Chấp nhận kết nối từ Client[cite: 5]
    while True:
       if stop_event and stop_event.is_set():
           print("[SERVER] Nhận yêu cầu dừng server.")
           server.close()
           return

       try:
           client_socket, client_address = server.accept()
           global current_client_socket
           current_client_socket = client_socket

           break

       except socket.timeout:
           continue

       except OSError:
           print("[SERVER] Socket server đã được đóng.")
           return

    print(f"[SERVER] Đã kết nối với {client_address}")
    client_socket.settimeout(1.0)
    # 3. Chờ lệnh xin phép kết nối từ Client[cite: 5]
    cmd, payload = receive_message(client_socket)

    # XÁC THỰC ID / PASSWORD
    if cmd == CMD_AUTH_REQ:
        import json

        try:
            auth_data = json.loads(
                payload.decode("utf-8")
            )

            input_id = auth_data.get("id", "")
            input_password = auth_data.get("password", "")

            auth_result = verify_credentials(
                input_id,
                input_password,
                client_ip=client_address[0]
            )

            send_message(
                client_socket,
                CMD_AUTH_RES,
                bytearray([1 if auth_result else 0])
            )

            if not auth_result:
                print("[SERVER] Xác thực thất bại!")
                client_socket.close()
                server.close()
                return

            print("[SERVER] Xác thực thành công!")
            # Sau khi xác thực thành công,
            # tiếp tục chờ Client gửi yêu cầu kết nối
            while True:
                try:
                    cmd, payload = receive_message(client_socket)

                    if not cmd:
                        print("[SERVER] Client đã ngắt kết nối.")
                        client_socket.close()
                        server.close()
                        return

                    break

                except socket.timeout:
                    if stop_event and stop_event.is_set():
                        client_socket.close()
                        server.close()
                        return
                    continue

        except Exception as e:
            print(f"[SERVER] Lỗi xác thực: {e}")

            send_message(
                client_socket,
                CMD_AUTH_RES,
                bytearray([0])
            )

            client_socket.close()
            server.close()
            return
    
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
                kwargs={"stop_event": stop_event},
                daemon=True
            )
            stream_thread.start()
            print("[SERVER] Luồng truyền hình ảnh TV2 đã được kích hoạt thành công!")
            # =========================================================

            # =========================================================
            # MODULE TV3: VÒNG LẶP NHẬN & THỰC THI LỆNH ĐIỀU KHIỂN
            # =========================================================
            while True:
                # Kiểm tra yêu cầu dừng từ Host GUI
                if stop_event and stop_event.is_set():
                    print("[SERVER] Nhận yêu cầu ngắt khẩn cấp.")
                    break

                try:
                    msg_cmd, msg_payload = receive_message(client_socket)

                    if not msg_cmd:
                        print("[SERVER] Client đã ngắt kết nối.")
                        break

                    # Truyền dữ liệu phím/chuột cho TV3 xử lý
                    if msg_cmd in (CMD_MOUSE, CMD_KEY):
                        process_input_command(msg_cmd, msg_payload)
            
                except socket.timeout:
                    # Timeout chỉ để kiểm tra stop_event
                    continue

                except (ConnectionResetError, BrokenPipeError, OSError) as e:
                    print(f"[SERVER] Client đã mất kết nối: {e}")
                    break

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

    try:
        client_socket.shutdown(socket.SHUT_RDWR)
    except:
        pass

    try:
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

    # Đóng Client socket
    if current_client_socket:
        try:
            current_client_socket.shutdown(socket.SHUT_RDWR)
        except:
            pass

        try:
            current_client_socket.close()
        except:
            pass

        current_client_socket = None

    # Đóng Server socket
    if current_server_socket:
        try:
            current_server_socket.close()
        except:
            pass

    current_client_socket = None
    current_server_socket = None

    print("[SERVER] Đã ngắt kết nối và giải phóng socket.")

if __name__ == "__main__":
    start_server()