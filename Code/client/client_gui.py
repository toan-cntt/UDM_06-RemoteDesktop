import sys
import socket
import json
import os

from client.image_receiver import ImageReceiverThread
from client.input_listener import InputEventFilter
from PyQt5.QtCore import Qt
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
    CMD_AUTH_RES,
    CMD_MOUSE,
    CMD_KEY
)

app = QApplication(sys.argv)

# =========================
# LOAD STYLE QSS
# =========================
style_path = os.path.join(os.path.dirname(__file__), "..", "style.qss")
try:
    with open(style_path, "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())
except Exception as e:
    pass

client_socket = None
screen_receiver = None
authenticated = False
input_filter = None

window = QWidget()
window.setWindowTitle("Remote Desktop Client")
window.resize(900, 600)
main_layout = QVBoxLayout()
window.setLayout(main_layout)

# =========================
# GIAO DIỆN CẤU HÌNH
# =========================
ip_layout = QHBoxLayout()
ip_label = QLabel("IP:")
ip_input = QLineEdit()
ip_input.setText("127.0.0.1")
ip_input.setPlaceholderText("Ví dụ: 127.0.0.1")
ip_layout.addWidget(ip_label)
ip_layout.addWidget(ip_input)
main_layout.addLayout(ip_layout)

partner_id_layout = QHBoxLayout()
partner_id_label = QLabel("ID đối tác:")
partner_id_input = QLineEdit()
partner_id_input.setPlaceholderText("Nhập ID đối tác")
partner_id_layout.addWidget(partner_id_label)
partner_id_layout.addWidget(partner_id_input)
main_layout.addLayout(partner_id_layout)

password_layout = QHBoxLayout()
password_label = QLabel("Mật khẩu:")
password_input = QLineEdit()
password_input.setPlaceholderText("Nhập mật khẩu")
password_input.setEchoMode(QLineEdit.Password)
password_layout.addWidget(password_label)
password_layout.addWidget(password_input)
main_layout.addLayout(password_layout)

port_layout = QHBoxLayout()
port_label = QLabel("Port:")
port_input = QLineEdit()
port_input.setText("9999")
port_layout.addWidget(port_label)
port_layout.addWidget(port_input)
main_layout.addLayout(port_layout)

button_layout = QHBoxLayout()
connect_button = QPushButton("Kết nối")
disconnect_button = QPushButton("Ngắt kết nối")
button_layout.addWidget(connect_button)
button_layout.addWidget(disconnect_button)
main_layout.addLayout(button_layout)

status = QStatusBar()
status.showMessage("Chưa kết nối")
main_layout.addWidget(status)

# =========================
# KHUNG TRUYỀN HÌNH ẢNH
# =========================
screen_label = QLabel()
screen_label.setText("Remote Screen")
screen_label.setMinimumSize(800, 450)
screen_label.setStyleSheet("border: 2px solid black; background-color: lightgray;")
screen_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
screen_label.setFocusPolicy(Qt.StrongFocus)
main_layout.addWidget(screen_label)

def update_screen(qt_img):
    if isinstance(qt_img, QImage):
        pixmap = QPixmap.fromImage(qt_img)
        scaled_pixmap = pixmap.scaled(screen_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        screen_label.setPixmap(scaled_pixmap)

# =========================
# LÕI KẾT NỐI (BẢO MẬT KÉP)
# =========================
def connect_to_server():
    global client_socket, screen_receiver, authenticated, input_filter

    ip = ip_input.text().strip()
    port_text = port_input.text().strip()
    partner_id = partner_id_input.text().strip()
    password = password_input.text().strip()

    if not ip or not port_text or not partner_id or not password:
        status.showMessage("Vui lòng điền đầy đủ thông tin!")
        return

    try:
        port = int(port_text)
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        status.showMessage(f"Đang kết nối tới {ip}:{port}...")
        client_socket.connect((ip, port))

        # --- BƯỚC 1: XÁC THỰC MẬT KHẨU ---
        auth_data = {"id": partner_id, "password": password}
        send_message(client_socket, CMD_AUTH_REQ, json.dumps(auth_data).encode("utf-8"))
        
        cmd_type, payload = receive_message(client_socket)
        
        if cmd_type == CMD_AUTH_RES and payload == b'\x01':
            status.showMessage("Mật khẩu đúng! Đang chờ Host cấp quyền...")
            
            # --- BƯỚC 2: XIN QUYỀN ĐIỀU KHIỂN (POP-UP) ---
            send_message(client_socket, CMD_REQ_CONNECT, b"")
            cmd_type2, payload2 = receive_message(client_socket)
            
            if cmd_type2 == CMD_RES_CONNECT and payload2 == b'\x01':
                authenticated = True
                status.showMessage("Đã kết nối - đang điều khiển màn hình")

                # KÍCH HOẠT NHẬN ẢNH VÀ ĐIỀU KHIỂN
                screen_receiver = ImageReceiverThread(client_socket)
                if hasattr(screen_receiver, 'image_received'):
                    screen_receiver.image_received.connect(update_screen)
                elif hasattr(screen_receiver, 'change_pixmap_signal'):
                    screen_receiver.change_pixmap_signal.connect(update_screen)
                screen_receiver.start()

                input_filter = InputEventFilter(client_socket)
                screen_label.installEventFilter(input_filter)
            else:
                authenticated = False
                status.showMessage("Chủ máy đã TỪ CHỐI kết nối!")
                client_socket.close()
                client_socket = None
        else:
            authenticated = False
            status.showMessage("Mã ID hoặc Mật khẩu không đúng!")
            client_socket.close()
            client_socket = None

    except Exception as e:
        authenticated = False
        status.showMessage(f"Lỗi kết nối: {e}")
        if client_socket:
            try: client_socket.close()
            except: pass
        client_socket = None

def disconnect_from_server():
    global client_socket, screen_receiver, authenticated, input_filter
    authenticated = False
    if input_filter is not None:
        screen_label.removeEventFilter(input_filter)
        input_filter = None
    if screen_receiver:
        if hasattr(screen_receiver, 'stop'):
            screen_receiver.stop()
        try: screen_receiver.wait(1000)
        except: pass
        screen_receiver = None
    if client_socket:
        try:
            client_socket.shutdown(socket.SHUT_RDWR)
            client_socket.close()
        except: pass
        client_socket = None
    screen_label.clear()
    screen_label.setText("Remote Screen")
    status.showMessage("Đã ngắt kết nối")

connect_button.clicked.connect(connect_to_server)
disconnect_button.clicked.connect(disconnect_from_server)

if __name__ == "__main__":
    window.show()
    sys.exit(app.exec_())