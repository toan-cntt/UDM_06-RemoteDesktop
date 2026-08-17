import sys
import socket

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
    CMD_SCREEN
)


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

app = QApplication(sys.argv)

client_socket = None
screen_receiver = None


window = QWidget()
window.setWindowTitle("Remote Desktop Client")
window.resize(900, 600)

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

screen_label = QLabel()

screen_label.setText("Remote Screen")

screen_label.setMinimumSize(800, 450)

screen_label.setStyleSheet("""
    border: 2px solid black;
    background-color: lightgray;
""")

screen_label.setAlignment(Qt.AlignCenter)

main_layout.addWidget(screen_label)


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

    ip = ip_input.text().strip()
    port_text = port_input.text().strip()

    if not ip or not port_text:
        status.showMessage("Vui lòng nhập IP và Port")
        return

    try:
        port = int(port_text)

        client_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        print(f"[CLIENT] Đang kết nối tới {ip}:{port}...")

        client_socket.connect((ip, port))

        print("[CLIENT] Kết nối TCP thành công!")

        # Gửi yêu cầu kết nối
        send_message(
            client_socket,
            CMD_REQ_CONNECT
        )

        # Chờ Server phản hồi
        cmd_type, payload = receive_message(client_socket)

        if cmd_type == CMD_RES_CONNECT and payload == b'\x01':

            status.showMessage("Đã kết nối")

            print("[CLIENT] Server đã cho phép!")

            # Tạo thread nhận màn hình
            screen_receiver = ScreenReceiver(client_socket)

            screen_receiver.frame_received.connect(
                update_screen
            )

            screen_receiver.connection_error.connect(
                lambda error: status.showMessage(
                    f"Lỗi nhận màn hình: {error}"
                )
            )

            screen_receiver.start()

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

        print(f"[CLIENT] Lỗi: {e}")

        if client_socket:
            try:
                client_socket.close()
            except:
                pass

        client_socket = None


# =========================
# NGẮT KẾT NỐI
# =========================

def disconnect_from_server():
    global client_socket
    global screen_receiver

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
