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
    CMD_AUTH_RES,
    CMD_REQ_CONNECT,
    CMD_RES_CONNECT
)
from server.input_executor import process_input_command
from server.screen_stream import screen_stream
from server.auth import verify_credentials

current_client_socket = None
current_server_socket = None

def start_server(ip="0.0.0.0", port=9999, on_connection_request=None, stop_event=None):   
    global current_client_socket
    global current_server_socket

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    current_server_socket = server
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((ip, port))
    server.listen(1)
    server.settimeout(1.0)
    print(f"[SERVER] Đang lắng nghe tại {ip}:{port}...")

    while True:
        if stop_event and stop_event.is_set():
            break

        try:
            client_socket, client_address = server.accept()
            current_client_socket = client_socket
            client_socket.settimeout(1.0)
        except socket.timeout:
            continue
        except OSError:
            break

        client_connected = True
        while client_connected:
            if stop_event and stop_event.is_set():
                client_connected = False
                break

            try:
                cmd, payload = receive_message(client_socket)
                if not cmd:
                    continue
                
                # BƯỚC 1: KIỂM TRA MẬT KHẨU
                if cmd == CMD_AUTH_REQ:
                    auth_data = json.loads(payload.decode("utf-8"))
                    input_id = auth_data.get("id", "")
                    input_password = auth_data.get("password", "")
                    client_ip = auth_data.get("ip", client_address[0])
                    
                    is_valid = verify_credentials(input_id, input_password, client_ip=client_ip)
                    
                    if is_valid:
                        send_message(client_socket, CMD_AUTH_RES, bytearray([1]))
                    else:
                        send_message(client_socket, CMD_AUTH_RES, bytearray([0]))
                        client_connected = False
                        break 

                # BƯỚC 2: GỌI GIAO DIỆN XIN PHÉP
                elif cmd == CMD_REQ_CONNECT:
                    if on_connection_request:
                        is_accepted = on_connection_request(client_address[0])
                    else:
                        is_accepted = False
                    
                    if is_accepted:
                        send_message(client_socket, CMD_RES_CONNECT, bytearray([1]))
                        stream_thread = threading.Thread(
                            target=screen_stream,
                            args=(client_socket,),
                            kwargs={"stop_event": stop_event},
                            daemon=True
                        )
                        stream_thread.start()
                    else:
                        send_message(client_socket, CMD_RES_CONNECT, bytearray([0]))
                        client_connected = False
                        break

                # BƯỚC 3: NHẬN LỆNH CHUỘT PHÍM
                elif cmd in (CMD_MOUSE, CMD_KEY):
                    process_input_command(cmd, payload)

            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError, OSError):
                client_connected = False
                break
            except Exception:
                client_connected = False
                break

        try:
            client_socket.shutdown(socket.SHUT_RDWR)
            client_socket.close()
        except:
            pass
        current_client_socket = None

    try: server.close()
    except: pass
    current_server_socket = None

def stop_server():
    global current_client_socket, current_server_socket
    if current_client_socket:
        try:
            current_client_socket.shutdown(socket.SHUT_RDWR)
            current_client_socket.close()
        except: pass
        current_client_socket = None
    if current_server_socket:
        try: current_server_socket.close()
        except: pass
        current_server_socket = None