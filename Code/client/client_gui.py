import sys
import socket
import json

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QStatusBar
)

from common.protocol import (
    send_message,
    receive_message,
    CMD_REQ_CONNECT,
    CMD_RES_CONNECT,
    CMD_SCREEN,
    CMD_MOUSE,
    CMD_KEY,
    CMD_AUTH_REQ,
    CMD_AUTH_RES
)


# ============================================================
# GLOBAL CLIENT STATE
# ============================================================

client_socket = None
screen_receiver = None


# ============================================================
# SCREEN RECEIVER THREAD
# ============================================================

class ScreenReceiver(QThread):

    frame_received = pyqtSignal(bytes)
    connection_error = pyqtSignal(str)

    def __init__(self, client_socket):
        super().__init__()

        self.client_socket = client_socket
        self.running = True

    def run(self):

        while self.running:

            try:

                cmd_type, payload = receive_message(
                    self.client_socket
                )

                if not cmd_type:
                    break

                if cmd_type == CMD_SCREEN and self.running:

                    self.frame_received.emit(payload)

            except Exception as e:

                if self.running:
                    self.connection_error.emit(str(e))

                break

    def stop(self):

        self.running = False


# ============================================================
# REMOTE SCREEN
# ============================================================

class RemoteScreen(QLabel):

    def __init__(self):
        super().__init__()

        self.setText("Remote Screen")

        self.setMinimumSize(800, 450)

        self.setStyleSheet("""
            QLabel {
                border: 2px solid black;
                background-color: lightgray;
            }
        """)

        self.setAlignment(Qt.AlignCenter)

        # Cho phép QLabel nhận keyboard event
        self.setFocusPolicy(Qt.StrongFocus)

        # Cho phép nhận mouse move
        self.setMouseTracking(True)

    # ========================================================
    # SEND MOUSE
    # ========================================================

    def send_mouse(self, action, x, y, button=None):

        global client_socket

        if client_socket is None:
            return

        try:

            data = {
                "action": action,
                "x": x,
                "y": y
            }

            if button is not None:
                data["button"] = button

            payload = json.dumps(
                data
            ).encode("utf-8")

            send_message(
                client_socket,
                CMD_MOUSE,
                payload
            )

        except Exception as e:

            print(
                f"[CLIENT] Lỗi gửi mouse: {e}"
            )

    # ========================================================
    # SEND KEYBOARD
    # ========================================================

    def send_key(self, action, key):

        global client_socket

        if client_socket is None:
            return

        try:

            data = {
                "action": action,
                "key": key
            }

            payload = json.dumps(
                data
            ).encode("utf-8")

            send_message(
                client_socket,
                CMD_KEY,
                payload
            )

        except Exception as e:

            print(
                f"[CLIENT] Lỗi gửi keyboard: {e}"
            )

    # ========================================================
    # MOUSE POSITION
    # ========================================================

    def get_normalized_position(self, event):

        width = self.width()
        height = self.height()

        if width <= 0 or height <= 0:
            return 0.0, 0.0

        x = event.pos().x() / width
        y = event.pos().y() / height

        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))

        return x, y

    # ========================================================
    # MOUSE MOVE
    # ========================================================

    def mouseMoveEvent(self, event):

        x, y = self.get_normalized_position(event)

        self.send_mouse(
            "move",
            x,
            y
        )

        event.accept()

    # ========================================================
    # MOUSE PRESS
    # ========================================================

    def mousePressEvent(self, event):

        x, y = self.get_normalized_position(event)

        if event.button() == Qt.LeftButton:

            button = "left"

        elif event.button() == Qt.RightButton:

            button = "right"

        elif event.button() == Qt.MiddleButton:

            button = "middle"

        else:

            button = "left"

        self.send_mouse(
            "down",
            x,
            y,
            button
        )

        # Click vào màn hình remote thì lấy keyboard focus
        self.setFocus()

        event.accept()

    # ========================================================
    # MOUSE RELEASE
    # ========================================================

    def mouseReleaseEvent(self, event):

        x, y = self.get_normalized_position(event)

        if event.button() == Qt.LeftButton:

            button = "left"

        elif event.button() == Qt.RightButton:

            button = "right"

        elif event.button() == Qt.MiddleButton:

            button = "middle"

        else:

            button = "left"

        self.send_mouse(
            "up",
            x,
            y,
            button
        )

        event.accept()

    # ========================================================
    # MOUSE WHEEL
    # ========================================================

    def wheelEvent(self, event):

        delta = event.angleDelta().y()

        if delta > 0:

            scroll = 1

        elif delta < 0:

            scroll = -1

        else:

            scroll = 0

        if scroll == 0:
            return

        global client_socket

        if client_socket is not None:

            try:

                data = {
                    "action": "scroll",
                    "amount": scroll
                }

                payload = json.dumps(
                    data
                ).encode("utf-8")

                send_message(
                    client_socket,
                    CMD_MOUSE,
                    payload
                )

            except Exception as e:

                print(
                    f"[CLIENT] Lỗi scroll: {e}"
                )

        event.accept()

    # ========================================================
    # KEY PRESS
    # ========================================================

    def keyPressEvent(self, event):

        key = event.key()

        key_name = self.qt_key_to_string(
            key,
            event.text()
        )

        if key_name:

            self.send_key(
                "key_down",
                key_name
            )

        event.accept()

    # ========================================================
    # KEY RELEASE
    # ========================================================

    def keyReleaseEvent(self, event):

        key = event.key()

        key_name = self.qt_key_to_string(
            key,
            event.text()
        )

        if key_name:

            self.send_key(
                "key_up",
                key_name
            )

        event.accept()

    # ========================================================
    # QT KEY -> STRING
    # ========================================================

    def qt_key_to_string(self, key, text):

        special_keys = {

            Qt.Key_Return: "enter",
            Qt.Key_Enter: "enter",

            Qt.Key_Backspace: "backspace",
            Qt.Key_Tab: "tab",
            Qt.Key_Escape: "esc",
            Qt.Key_Delete: "delete",

            Qt.Key_Left: "left",
            Qt.Key_Right: "right",
            Qt.Key_Up: "up",
            Qt.Key_Down: "down",

            Qt.Key_Home: "home",
            Qt.Key_End: "end",
            Qt.Key_PageUp: "page_up",
            Qt.Key_PageDown: "page_down",

            Qt.Key_Shift: "shift",
            Qt.Key_Control: "ctrl",
            Qt.Key_Alt: "alt",

            Qt.Key_Space: "space",

            Qt.Key_F1: "f1",
            Qt.Key_F2: "f2",
            Qt.Key_F3: "f3",
            Qt.Key_F4: "f4",
            Qt.Key_F5: "f5",
            Qt.Key_F6: "f6",
            Qt.Key_F7: "f7",
            Qt.Key_F8: "f8",
            Qt.Key_F9: "f9",
            Qt.Key_F10: "f10",
            Qt.Key_F11: "f11",
            Qt.Key_F12: "f12",
        }

        if key in special_keys:

            return special_keys[key]

        if text:

            return text.lower()

        return None


# ============================================================
# APPLICATION
# ============================================================

app = QApplication(sys.argv)


# ============================================================
# MAIN WINDOW
# ============================================================

window = QWidget()

window.setWindowTitle(
    "Remote Desktop Client"
)

window.resize(
    900,
    600
)


main_layout = QVBoxLayout()

window.setLayout(
    main_layout
)


# ============================================================
# IP
# ============================================================

ip_layout = QHBoxLayout()

ip_label = QLabel("IP:")

ip_input = QLineEdit()

ip_input.setText(
    "127.0.0.1"
)

ip_input.setPlaceholderText(
    "Ví dụ: 127.0.0.1"
)

ip_layout.addWidget(
    ip_label
)

ip_layout.addWidget(
    ip_input
)

main_layout.addLayout(
    ip_layout
)


# ============================================================
# PORT
# ============================================================

port_layout = QHBoxLayout()

port_label = QLabel("Port:")

port_input = QLineEdit()

port_input.setText(
    "9999"
)

port_input.setPlaceholderText(
    "Ví dụ: 9999"
)

port_layout.addWidget(
    port_label
)

port_layout.addWidget(
    port_input
)

main_layout.addLayout(
    port_layout
)


# ============================================================
# HOST ID
# ============================================================

id_layout = QHBoxLayout()

id_label = QLabel("Host ID:")

id_input = QLineEdit()

id_input.setPlaceholderText(
    "Ví dụ: 123456"
)

id_layout.addWidget(
    id_label
)

id_layout.addWidget(
    id_input
)

main_layout.addLayout(
    id_layout
)


# ============================================================
# PASSWORD
# ============================================================

password_layout = QHBoxLayout()

password_label = QLabel("Password:")

password_input = QLineEdit()

password_input.setPlaceholderText(
    "Ví dụ: 5678"
)

password_input.setEchoMode(
    QLineEdit.Password
)

password_layout.addWidget(
    password_label
)

password_layout.addWidget(
    password_input
)

main_layout.addLayout(
    password_layout
)


# ============================================================
# BUTTONS
# ============================================================

button_layout = QHBoxLayout()

connect_button = QPushButton(
    "Kết nối"
)

disconnect_button = QPushButton(
    "Ngắt kết nối"
)

button_layout.addWidget(
    connect_button
)

button_layout.addWidget(
    disconnect_button
)

main_layout.addLayout(
    button_layout
)


# ============================================================
# STATUS
# ============================================================

status = QStatusBar()

status.showMessage(
    "Chưa kết nối"
)

main_layout.addWidget(
    status
)


# ============================================================
# REMOTE SCREEN
# ============================================================

screen_label = RemoteScreen()

main_layout.addWidget(
    screen_label
)


# ============================================================
# UPDATE SCREEN
# ============================================================

def update_screen(frame_data):

    image = QImage()

    if image.loadFromData(
        frame_data,
        "JPEG"
    ):

        pixmap = QPixmap.fromImage(
            image
        )

        scaled_pixmap = pixmap.scaled(
            screen_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        screen_label.setPixmap(
            scaled_pixmap
        )

    else:

        print(
            "[CLIENT] Không thể đọc frame JPEG"
        )


# ============================================================
# CONNECT TO SERVER
# ============================================================

def connect_to_server():

    global client_socket
    global screen_receiver

    ip = ip_input.text().strip()

    port_text = port_input.text().strip()

    host_id = id_input.text().strip()

    host_password = password_input.text().strip()

    if (
        not ip
        or not port_text
        or not host_id
        or not host_password
    ):

        status.showMessage(
            "Vui lòng nhập IP, Port, Host ID và Password"
        )

        return

    try:

        port = int(port_text)

        client_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        print(
            f"[CLIENT] Đang kết nối tới {ip}:{port}..."
        )

        client_socket.connect(
            (ip, port)
        )

        print(
            "[CLIENT] Kết nối TCP thành công!"
        )

        # ====================================================
        # AUTHENTICATION
        # ====================================================

        auth_data = {
            "id": host_id,
            "password": host_password
        }

        auth_payload = json.dumps(
            auth_data
        ).encode("utf-8")

        print(
            "[CLIENT] Gửi yêu cầu xác thực..."
        )

        send_message(
            client_socket,
            CMD_AUTH_REQ,
            auth_payload
        )

        cmd_type, payload = receive_message(
            client_socket
        )

        if cmd_type != CMD_AUTH_RES:

            status.showMessage(
                "Server không phản hồi Authentication"
            )

            print(
                f"[CLIENT] Command xác thực không hợp lệ: {cmd_type}"
            )

            client_socket.close()

            client_socket = None

            return

        if payload != b"\x01":

            status.showMessage(
                "Sai Host ID hoặc Password"
            )

            print(
                "[CLIENT] Authentication thất bại!"
            )

            client_socket.close()

            client_socket = None

            return

        print(
            "[CLIENT] Authentication thành công!"
        )

        # ====================================================
        # REQUEST REMOTE DESKTOP
        # ====================================================

        print(
            "[CLIENT] Yêu cầu kết nối Remote Desktop..."
        )

        send_message(
            client_socket,
            CMD_REQ_CONNECT
        )

        cmd_type, payload = receive_message(
            client_socket
        )

        if (
            cmd_type == CMD_RES_CONNECT
            and payload == b"\x01"
        ):

            status.showMessage(
                "Đã kết nối"
            )

            print(
                "[CLIENT] Server đã cho phép!"
            )

            # =================================================
            # START SCREEN RECEIVER
            # =================================================

            screen_receiver = ScreenReceiver(
                client_socket
            )

            screen_receiver.frame_received.connect(
                update_screen
            )

            screen_receiver.connection_error.connect(
                lambda error:
                status.showMessage(
                    f"Lỗi nhận màn hình: {error}"
                )
            )

            screen_receiver.start()

            # Cho RemoteScreen nhận keyboard
            screen_label.setFocus()

        else:

            status.showMessage(
                "Server từ chối kết nối"
            )

            client_socket.close()

            client_socket = None

    except Exception as e:

        status.showMessage(
            f"Lỗi kết nối: {e}"
        )

        print(
            f"[CLIENT] Lỗi: {e}"
        )

        if client_socket:

            try:

                client_socket.close()

            except Exception:

                pass

        client_socket = None


# ============================================================
# DISCONNECT
# ============================================================

def disconnect_from_server():

    global client_socket
    global screen_receiver

    # ========================================================
    # STOP SCREEN THREAD
    # ========================================================

    if screen_receiver:

        screen_receiver.stop()

        try:

            screen_receiver.wait(1000)

        except Exception:

            pass

        screen_receiver = None

    # ========================================================
    # CLOSE SOCKET
    # ========================================================

    if client_socket:

        try:

            client_socket.shutdown(
                socket.SHUT_RDWR
            )

        except Exception:

            pass

        try:

            client_socket.close()

        except Exception:

            pass

        client_socket = None

    # ========================================================
    # RESET GUI
    # ========================================================

    screen_label.clear()

    screen_label.setText(
        "Remote Screen"
    )

    status.showMessage(
        "Đã ngắt kết nối"
    )


# ============================================================
# BUTTON EVENTS
# ============================================================

connect_button.clicked.connect(
    connect_to_server
)

disconnect_button.clicked.connect(
    disconnect_from_server
)


# ============================================================
# START GUI
# ============================================================

window.show()

sys.exit(
    app.exec_()
)
