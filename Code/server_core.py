import socket
import threading
import json

from common.protocol import (
    receive_message,
    send_message,
    CMD_AUTH_REQ,
    CMD_AUTH_RES,
    CMD_MOUSE,
    CMD_KEY
)

from server.input_executor import process_input_command
from server.screen_stream import screen_stream


# =========================
# THÔNG TIN XÁC THỰC HOST
# =========================

HOST_ID = "123456"
HOST_PASSWORD = "1234"


def start_server(ip="0.0.0.0", port=9999, on_connection_request=None):

    # =========================
    # 1. KHỞI TẠO SERVER
    # =========================

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.bind((ip, port))
    server.listen(1)

    print(
        f"[SERVER] Đang lắng nghe tại {ip}:{port}..."
    )


    # =========================
    # 2. CHẤP NHẬN CLIENT
    # =========================

    client_socket, client_address = server.accept()

    print(
        f"[SERVER] Đã kết nối với {client_address}"
    )


    # =========================
    # 3. NHẬN YÊU CẦU XÁC THỰC
    # =========================

    cmd, payload = receive_message(client_socket)

    if cmd == CMD_AUTH_REQ:

        print("[SERVER] Nhận yêu cầu xác thực!")

        try:

            # =========================
            # GIẢI MÃ JSON
            # =========================

            auth_data = json.loads(
                payload.decode("utf-8")
            )

            partner_id = str(
                auth_data.get("id", "")
            )

            partner_password = str(
                auth_data.get("password", "")
            )

            print(
                f"[SERVER] Client gửi ID: {partner_id}"
            )


            # =========================
            # KIỂM TRA ID + MẬT KHẨU
            # =========================

            if (
                partner_id == HOST_ID
                and partner_password == HOST_PASSWORD
            ):

                print(
                    "[SERVER] Xác thực thành công!"
                )

                # =========================
                # TRẢ KẾT QUẢ XÁC THỰC
                # =========================

                send_message(
                    client_socket,
                    CMD_AUTH_RES,
                    bytearray([1])
                )


                # =========================
                # XIN PHÉP KẾT NỐI
                # =========================

                print(
                    "[SERVER] Có người muốn xem màn hình!"
                )

                if on_connection_request:

                    result = on_connection_request(
                        client_address[0]
                    )

                else:

                    result = False


                # =========================
                # HOST CHO PHÉP
                # =========================

                if result:

                    print(
                        "[SERVER] Đã cho phép. "
                        "Bắt đầu phiên!"
                    )


                    # =========================
                    # TV2 - SCREEN STREAM
                    # =========================

                    stream_thread = threading.Thread(
                        target=screen_stream,
                        args=(client_socket,),
                        daemon=True
                    )

                    stream_thread.start()

                    print(
                        "[SERVER] Luồng truyền hình ảnh "
                        "TV2 đã được kích hoạt!"
                    )


                    # =========================
                    # TV3 - MOUSE / KEYBOARD
                    # =========================

                    while True:

                        try:

                            msg_cmd, msg_payload = (
                                receive_message(
                                    client_socket
                                )
                            )

                            if not msg_cmd:
                                break

                            if msg_cmd in (
                                CMD_MOUSE,
                                CMD_KEY
                            ):

                                process_input_command(
                                    msg_cmd,
                                    msg_payload
                                )

                        except Exception as e:

                            print(
                                f"[SERVER] "
                                f"Lỗi phiên kết nối: {e}"
                            )

                            break


                else:

                    print(
                        "[SERVER] "
                        "GUI Host từ chối kết nối!"
                    )


            # =========================
            # SAI ID / MẬT KHẨU
            # =========================

            else:

                print(
                    "[SERVER] Xác thực thất bại!"
                )

                send_message(
                    client_socket,
                    CMD_AUTH_RES,
                    bytearray([0])
                )


        except Exception as e:

            print(
                f"[SERVER] "
                f"Lỗi xử lý xác thực: {e}"
            )


    else:

        print(
            "[SERVER] "
            "Nhận lệnh không hợp lệ!"
        )


    # =========================
    # 4. ĐÓNG KẾT NỐI
    # =========================

    try:
        client_socket.close()
    except:
        pass

    try:
        server.close()
    except:
        pass


if __name__ == "__main__":
    start_server()