import socket
import json
import threading
import time

import cv2
import numpy as np
import mss

from common.protocol import (
    receive_message,
    send_message,
    CMD_REQ_CONNECT,
    CMD_RES_CONNECT,
    CMD_SCREEN,
    CMD_MOUSE,
    CMD_KEY,
    CMD_AUTH_REQ,
    CMD_AUTH_RES
)

from server.input_executor import process_input_command
from server.auth import (
    init_credentials,
    verify_credentials,
    get_current_credentials
)


# =========================================================
# SCREEN STREAMING CONFIG
# =========================================================

SCREEN_FPS = 20
JPEG_QUALITY = 70
SCREEN_SCALE = 0.75


# =========================================================
# SCREEN SENDER
# =========================================================

def screen_streamer(client_socket, stop_event):
    """
    Liên tục chụp màn hình Host, encode JPEG
    và gửi cho Client bằng CMD_SCREEN.
    """

    print("[SCREEN] Screen streaming đã bắt đầu!")

    frame_interval = 1.0 / SCREEN_FPS

    try:
        with mss.mss() as sct:

            # Monitor 1 = màn hình chính
            monitor = sct.monitors[1]

            while not stop_event.is_set():

                start_time = time.perf_counter()

                # -----------------------------------------
                # Capture màn hình
                # -----------------------------------------

                screenshot = sct.grab(monitor)

                # MSS trả về BGRA
                frame = np.array(screenshot)

                # BGRA -> BGR
                frame = cv2.cvtColor(
                    frame,
                    cv2.COLOR_BGRA2BGR
                )

                # -----------------------------------------
                # Resize để giảm bandwidth / CPU
                # -----------------------------------------

                if SCREEN_SCALE != 1.0:

                    width = int(
                        frame.shape[1] * SCREEN_SCALE
                    )

                    height = int(
                        frame.shape[0] * SCREEN_SCALE
                    )

                    frame = cv2.resize(
                        frame,
                        (width, height),
                        interpolation=cv2.INTER_AREA
                    )

                # -----------------------------------------
                # Encode JPEG
                # -----------------------------------------

                success, encoded = cv2.imencode(
                    ".jpg",
                    frame,
                    [
                        cv2.IMWRITE_JPEG_QUALITY,
                        JPEG_QUALITY
                    ]
                )

                if not success:
                    print("[SCREEN] JPEG encode thất bại")
                    continue

                jpeg_data = encoded.tobytes()

                # -----------------------------------------
                # Gửi CMD_SCREEN
                # -----------------------------------------

                send_message(
                    client_socket,
                    CMD_SCREEN,
                    jpeg_data
                )

                # -----------------------------------------
                # FPS limiter
                # -----------------------------------------

                elapsed = time.perf_counter() - start_time

                sleep_time = frame_interval - elapsed

                if sleep_time > 0:
                    time.sleep(sleep_time)

    except (ConnectionResetError, BrokenPipeError, OSError) as e:

        print(
            f"[SCREEN] Client đã ngắt kết nối: {e}"
        )

    except Exception as e:

        print(
            f"[SCREEN] Lỗi Screen Streaming: {e}"
        )

    finally:

        print("[SCREEN] Screen streaming đã dừng!")


# =========================================================
# SERVER
# =========================================================

def start_server(ip="0.0.0.0", port=9999):

    # =====================================================
    # AUTHENTICATION
    # =====================================================

    init_credentials()

    host_id, host_password = get_current_credentials()

    print(f"Host ID: {host_id}")
    print(f"Host Password: {host_password}")

    # =====================================================
    # TCP SOCKET
    # =====================================================

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind((ip, port))

    server.listen(1)

    print(
        f"[SERVER] Đang lắng nghe tại {ip}:{port}..."
    )

    # =====================================================
    # ACCEPT CLIENT
    # =====================================================

    client_socket, client_address = server.accept()

    print(
        f"[SERVER] Đã kết nối với {client_address}"
    )

    # =====================================================
    # BƯỚC 1: AUTHENTICATION
    # =====================================================

    cmd, payload = receive_message(client_socket)

    if cmd != CMD_AUTH_REQ:

        print(
            f"[SERVER] Từ chối kết nối: "
            f"Client gửi command {cmd} "
            f"thay vì CMD_AUTH_REQ"
        )

        client_socket.close()
        server.close()

        return

    try:

        req = json.loads(
            payload.decode("utf-8")
        )

        print(
            f"[SERVER] Nhận yêu cầu xác thực "
            f"từ ID={req.get('id', '')}"
        )

        ok = verify_credentials(
            req.get("id", ""),
            req.get("password", ""),
            client_ip=client_address[0]
        )

        send_message(
            client_socket,
            CMD_AUTH_RES,
            bytes([1 if ok else 0])
        )

        if ok:

            print(
                "[SERVER] Xác thực thành công!"
            )

        else:

            print(
                "[SERVER] Xác thực thất bại!"
            )

            client_socket.close()
            server.close()

            return

    except (
        json.JSONDecodeError,
        UnicodeDecodeError
    ) as e:

        print(
            f"[SERVER] Payload authentication "
            f"không hợp lệ: {e}"
        )

        send_message(
            client_socket,
            CMD_AUTH_RES,
            bytes([0])
        )

        client_socket.close()
        server.close()

        return

    # =====================================================
    # BƯỚC 2: REQUEST REMOTE DESKTOP
    # =====================================================

    cmd, payload = receive_message(client_socket)

    if cmd != CMD_REQ_CONNECT:

        print(
            f"[SERVER] Authentication OK nhưng "
            f"Client gửi command {cmd} "
            f"thay vì CMD_REQ_CONNECT"
        )

        client_socket.close()
        server.close()

        return

    print(
        "[SERVER] Có người muốn xem màn hình!"
    )

    # -----------------------------------------------------
    # Tạm thời tự động cho phép
    # -----------------------------------------------------

    send_message(
        client_socket,
        CMD_RES_CONNECT,
        bytes([1])
    )

    print(
        "[SERVER] Đã cho phép. Bắt đầu phiên!"
    )

    # =====================================================
    # BƯỚC 3: START SCREEN STREAMING
    # =====================================================

    stop_event = threading.Event()

    screen_thread = threading.Thread(
        target=screen_streamer,
        args=(
            client_socket,
            stop_event
        ),
        daemon=True
    )

    screen_thread.start()

    # =====================================================
    # BƯỚC 4: NHẬN INPUT
    # =====================================================

    try:

        while True:

            msg_cmd, msg_payload = receive_message(
                client_socket
            )

            if not msg_cmd:
                break

            print(
                f"[SERVER] Nhận lệnh {msg_cmd} "
                f"có kích thước "
                f"{len(msg_payload)} bytes"
            )

            # ---------------------------------------------
            # Mouse / Keyboard
            # ---------------------------------------------

            if msg_cmd in (
                CMD_MOUSE,
                CMD_KEY
            ):

                process_input_command(
                    msg_cmd,
                    msg_payload
                )

    except (
        ConnectionResetError,
        BrokenPipeError,
        OSError
    ) as e:

        print(
            f"[SERVER] Client ngắt kết nối: {e}"
        )

    except Exception as e:

        print(
            f"[SERVER] Lỗi: {e}"
        )

    finally:

        # =================================================
        # STOP SCREEN STREAMING
        # =================================================

        stop_event.set()

        screen_thread.join(
            timeout=2
        )

        # =================================================
        # CLOSE SOCKET
        # =================================================

        try:
            client_socket.close()
        except Exception:
            pass

        try:
            server.close()
        except Exception:
            pass

        print(
            "[SERVER] Phiên Remote Desktop đã kết thúc."
        )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    start_server()