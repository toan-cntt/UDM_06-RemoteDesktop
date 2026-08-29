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
    CMD_AUTH_REQ,
    CMD_AUTH_RES
)


class ScreenReceiver(QThread):
    frame_received = pyqtSignal(bytes)
    connection_error = pyqtSignal(str)
    connection_finished = pyqtSignal()

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
        self.connection_finished.emit()

    def stop(self):
        self.running = False

app = QApplication(sys.argv)

client_socket = None
screen_receiver = None
authenticated = False


window = QWidget()
window.setWindowTitle("Remote Desktop Client")
window.resize(900, 600)
# =========================
# BẮT SỰ KIỆN CHUỘT / BÀN PHÍM
# =========================

class RemoteScreenLabel(QLabel):

    def mousePressEvent(self, event):
        send_mouse_event(
            "click",
            event.position().x(),
            event.position().y(),
            event.button()
        )

    def mouseMoveEvent(self, event):
        send_mouse_event(
            "move",
            event.position().x(),
            event.position().y(),
            None
        )

    def keyPressEvent(self, event):
        send_key_event(
            event.key(),
            event.text()
        )

    def mouseReleaseEvent(self, event):
        send_mouse_event(
            "release",
            event.position().x(),
            event.position().y(),
            event.button()
        )

main_layout = QVBoxLayout()
window.setLayout(main_layout)


# =========================
# IP
# =========================

ip_layout = QHBoxLayout()

ip_label = QLabel("IP:")

ip_input = QLineEdit()
ip_input.setText("127.0.0.1")
ip_input.setPlaceholderText("Ví dụ: 127.0.0.1")

ip_layout.addWidget(ip_label)
ip_layout.addWidget(ip_input)

main_layout.addLayout(ip_layout)
# =========================
# ID ĐỐI TÁC
# =========================

partner_id_layout = QHBoxLayout()

partner_id_label = QLabel("ID đối tác:")

partner_id_input = QLineEdit()
partner_id_input.setPlaceholderText("Nhập ID đối tác")

partner_id_layout.addWidget(partner_id_label)
partner_id_layout.addWidget(partner_id_input)

main_layout.addLayout(partner_id_layout)


# =========================
# MẬT KHẨU
# =========================

password_layout = QHBoxLayout()

password_label = QLabel("Mật khẩu:")

password_input = QLineEdit()
password_input.setPlaceholderText("Nhập mật khẩu")
password_input.setEchoMode(QLineEdit.Password)

password_layout.addWidget(password_label)
password_layout.addWidget(password_input)

main_layout.addLayout(password_layout)


# =========================
# PORT
# =========================

port_layout = QHBoxLayout()

port_label = QLabel("Port:")

port_input = QLineEdit()
port_input.setText("9999")
port_input.setPlaceholderText("Ví dụ: 9999")

port_layout.addWidget(port_label)
port_layout.addWidget(port_input)

main_layout.addLayout(port_layout)


# =========================
# BUTTON
# =========================

button_layout = QHBoxLayout()

connect_button = QPushButton("Kết nối")
disconnect_button = QPushButton("Ngắt kết nối")

button_layout.addWidget(connect_button)
button_layout.addWidget(disconnect_button)

main_layout.addLayout(button_layout)


# =========================
# STATUS
# =========================

status = QStatusBar()
status.showMessage("Chưa kết nối")

main_layout.addWidget(status)


# =========================
# REMOTE SCREEN
# =========================

screen_label = RemoteScreenLabel()

screen_label.setText("Remote Screen")

screen_label.setMinimumSize(800, 450)

screen_label.setStyleSheet("""
    border: 2px solid black;
    background-color: lightgray;
""")

screen_label.setAlignment(Qt.AlignCenter)

screen_label.setFocusPolicy(Qt.StrongFocus)

main_layout.addWidget(screen_label)

# =========================
# GỬI SỰ KIỆN CHUỘT
# =========================

def send_mouse_event(event_type, x, y, button):

    global client_socket
    global authenticated

    if not client_socket or not authenticated:
        return

    try:

        # Kích thước ảnh thực tế đang hiển thị
        pixmap = screen_label.pixmap()

        if pixmap is None:
            return

        display_width = pixmap.width()
        display_height = pixmap.height()

        if display_width <= 0 or display_height <= 0:
            return

        # Tính vị trí bắt đầu của ảnh trong QLabel
        offset_x = (
            screen_label.width()
            - display_width
        ) / 2

        offset_y = (
            screen_label.height()
            - display_height
        ) / 2

        # Tọa độ tương đối bên trong ảnh
        image_x = x - offset_x
        image_y = y - offset_y

        if (
            image_x < 0
            or image_y < 0
            or image_x >= display_width
            or image_y >= display_height
        ):
            return

        # Lấy kích thước màn hình Host
        # từ kích thước ảnh gốc đã scale
        image = pixmap.toImage()

        host_x = int(
            image_x
            * image.width()
            / display_width
        )

        host_y = int(
            image_y
            * image.height()
            / display_height
        )

        if button is not None:
            button_value = int(button)
        else:
            button_value = 0

        mouse_data = {
            "event": event_type,
            "x": host_x,
            "y": host_y,
            "button": button_value
        }

        payload = json.dumps(
            mouse_data
        ).encode("utf-8")

        send_message(
            client_socket,
            CMD_MOUSE,
            payload
        )

    except Exception as e:

        print(
            f"[CLIENT] Lỗi gửi chuột: {e}"
        )
        
# =========================
# GỬI SỰ KIỆN BÀN PHÍM
# =========================

def send_key_event(key, text):

    global client_socket
    global authenticated

    if not client_socket or not authenticated:
        return

    try:

        key_data = {
            "key": int(key),
            "text": text
        }

        payload = json.dumps(
            key_data
        ).encode("utf-8")

        send_message(
            client_socket,
            CMD_KEY,
            payload
        )

    except Exception as e:

        print(
            f"[CLIENT] Lỗi gửi bàn phím: {e}"
        )

# =========================
# HIỂN THỊ FRAME
# =========================

def update_screen(frame_data):
    image = QImage()

    if image.loadFromData(frame_data, "JPEG"):

        pixmap = QPixmap.fromImage(image)

        scaled_pixmap = pixmap.scaled(
            screen_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        screen_label.setPixmap(scaled_pixmap)

    else:
        print("[CLIENT] Không thể đọc frame JPEG")


# =========================
# KẾT NỐI SERVER
# =========================

def connect_to_server():
    global client_socket
    global screen_receiver
    global authenticated

    ip = ip_input.text().strip()
    port_text = port_input.text().strip()
    partner_id = partner_id_input.text().strip()
    password = password_input.text().strip()

    # Kiểm tra dữ liệu nhập
    if not ip or not port_text:
        status.showMessage("Vui lòng nhập IP và Port")
        return

    if not partner_id or not password:
        status.showMessage("Vui lòng nhập ID và Mật khẩu")
        return

    if not partner_id.isdigit() or len(partner_id) != 6:
        status.showMessage("ID phải gồm 6 chữ số")
        return

    if not password.isdigit() or len(password) != 4:
        status.showMessage("Mật khẩu phải gồm 4 chữ số")
        return

    try:
        port = int(port_text)

        client_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        print(
            f"[CLIENT] Đang kết nối tới "
            f"{ip}:{port}..."
        )

        client_socket.connect(
            (ip, port)
        )

        print(
            "[CLIENT] Kết nối TCP thành công!"
        )

        # =================================================
        # XÁC THỰC ID / PASSWORD
        # =================================================

        import json

        auth_data = {
            "id": partner_id,
            "password": password
        }

        auth_payload = json.dumps(
            auth_data
        ).encode("utf-8")

        print(
            "[CLIENT] Đang gửi thông tin "
            "xác thực..."
        )

        send_message(
            client_socket,
            CMD_AUTH_REQ,
            auth_payload
        )

        # Chờ Server phản hồi xác thực
        cmd_type, payload = receive_message(
            client_socket
        )

        if (
            cmd_type == CMD_AUTH_RES
            and payload == b'\x01'
        ):

            authenticated = True

            print(
                "[CLIENT] Xác thực thành công!"
            )

            status.showMessage(
                "Xác thực thành công - đang chờ Host..."
            )

        else:

            authenticated = False

            status.showMessage(
                "Mật khẩu hoặc ID không đúng!"
            )

            print(
                "[CLIENT] Xác thực thất bại!"
            )

            client_socket.close()
            client_socket = None

            return

        # =================================================
        # GỬI YÊU CẦU KẾT NỐI
        # =================================================

        send_message(
            client_socket,
            CMD_REQ_CONNECT
        )

        print(
            "[CLIENT] Đã gửi yêu cầu kết nối "
            "đến Host."
        )

        # Chờ Host Accept / Reject
        cmd_type, payload = receive_message(
            client_socket
        )

        if (
            cmd_type == CMD_RES_CONNECT
            and payload == b'\x01'
        ):

            status.showMessage(
                "Đã kết nối - đang nhận màn hình"
            )

            print(
                "[CLIENT] Host đã cho phép!"
            )

            # =================================================
            # TẠO THREAD NHẬN MÀN HÌNH
            # =================================================

            screen_receiver = ScreenReceiver(
                client_socket
            )

            screen_receiver.frame_received.connect(
                update_screen
            )

            screen_receiver.connection_error.connect(
                lambda error: status.showMessage(
                    f"Lỗi nhận màn hình: {error}"
                )
            )

            screen_receiver.connection_finished.connect(
                handle_receiver_finished
            )

            screen_receiver.start()

        else:

            status.showMessage(
                "Host từ chối kết nối"
            )

            print(
                "[CLIENT] Host từ chối kết nối!"
            )

            client_socket.close()
            client_socket = None
            authenticated = False

    except Exception as e:

        authenticated = False

        status.showMessage(
            f"Lỗi kết nối: {e}"
        )

        print(
            f"[CLIENT] Lỗi: {e}"
        )

        if client_socket:

            try:
                client_socket.close()
            except:
                pass

        client_socket = None

def handle_receiver_finished():
    global client_socket
    global screen_receiver
    global authenticated

    authenticated = False

    if screen_receiver:
        screen_receiver = None

    if client_socket:
        try:
            client_socket.close()
        except:
            pass

        client_socket = None

    screen_label.clear()
    screen_label.setText("Remote Screen")

    status.showMessage(
        "Kết nối đã kết thúc"
    )
# =========================
# NGẮT KẾT NỐI
# =========================

def disconnect_from_server():
    global client_socket
    global screen_receiver
    global authenticated

    authenticated = False


    # Dừng thread nhận màn hình
    if screen_receiver:
        screen_receiver.stop()

        try:
            screen_receiver.wait(1000)
        except:
            pass

        screen_receiver = None

    # Đóng socket
    if client_socket:
        try:
            client_socket.shutdown(socket.SHUT_RDWR)
        except:
            pass

        try:
            client_socket.close()
        except:
            pass

        client_socket = None

    # Reset giao diện
    screen_label.clear()
    screen_label.setText("Remote Screen")

    status.showMessage("Đã ngắt kết nối")


# =========================
# BUTTON EVENTS
# =========================

connect_button.clicked.connect(connect_to_server)
disconnect_button.clicked.connect(disconnect_from_server)


# =========================
# CHẠY GUI
# =========================

window.show()

sys.exit(app.exec_())
