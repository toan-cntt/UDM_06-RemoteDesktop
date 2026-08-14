import sys
import threading
import logging

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QMessageBox
)

from server_core import start_server


# =========================================================
# LOG
# =========================================================

logging.basicConfig(
    filename="host_activity.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# =========================================================
# HOST GUI
# =========================================================

class HostGUI(QWidget):

    # Signal dùng để đưa yêu cầu kết nối
    # từ server thread về GUI thread
    connection_request_signal = pyqtSignal(str)

    def __init__(self):

        super().__init__()

        self.running = False
        self.server_thread = None

        # Kết quả Accept / Reject
        self.connection_result = None

        self.client_ip = None

        self.init_ui()

        # Khi server nhận Client
        # → signal này sẽ mở popup
        self.connection_request_signal.connect(
            self.show_connection_dialog
        )

    # =====================================================
    # UI
    # =====================================================

    def init_ui(self):

        self.setWindowTitle(
            "Remote Desktop - Host"
        )

        self.resize(650, 550)

        main_layout = QVBoxLayout()

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        title = QLabel(
            "REMOTE DESKTOP - HOST"
        )

        title.setStyleSheet(
            """
            QLabel {
                font-size: 24px;
                font-weight: bold;
                padding: 15px;
            }
            """
        )

        main_layout.addWidget(title)

        # -------------------------------------------------
        # CONNECTION SETTINGS
        # -------------------------------------------------

        connection_group = QGroupBox(
            "Cấu hình kết nối"
        )

        connection_layout = QVBoxLayout()

        port_layout = QHBoxLayout()

        port_label = QLabel(
            "Port:"
        )

        self.port_input = QSpinBox()

        self.port_input.setRange(
            1024,
            65535
        )

        self.port_input.setValue(
            9999
        )

        port_layout.addWidget(
            port_label
        )

        port_layout.addWidget(
            self.port_input
        )

        connection_layout.addLayout(
            port_layout
        )

        # -------------------------------------------------
        # BUTTONS
        # -------------------------------------------------

        button_layout = QHBoxLayout()

        self.start_button = QPushButton(
            "START HOST"
        )

        self.stop_button = QPushButton(
            "STOP HOST"
        )

        self.stop_button.setEnabled(
            False
        )

        self.start_button.clicked.connect(
            self.start_server
        )

        self.stop_button.clicked.connect(
            self.stop_server
        )

        button_layout.addWidget(
            self.start_button
        )

        button_layout.addWidget(
            self.stop_button
        )

        connection_layout.addLayout(
            button_layout
        )

        connection_group.setLayout(
            connection_layout
        )

        main_layout.addWidget(
            connection_group
        )

        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        status_group = QGroupBox(
            "Trạng thái"
        )

        status_layout = QVBoxLayout()

        self.status_label = QLabel(
            "● OFFLINE"
        )

        self.client_label = QLabel(
            "Client: Chưa kết nối"
        )

        self.permission_label = QLabel(
            "Quyền điều khiển: CHƯA CẤP"
        )

        status_layout.addWidget(
            self.status_label
        )

        status_layout.addWidget(
            self.client_label
        )

        status_layout.addWidget(
            self.permission_label
        )

        status_group.setLayout(
            status_layout
        )

        main_layout.addWidget(
            status_group
        )

        # -------------------------------------------------
        # LOG
        # -------------------------------------------------

        log_group = QGroupBox(
            "System Log"
        )

        log_layout = QVBoxLayout()

        self.log_display = QTextEdit()

        self.log_display.setReadOnly(
            True
        )

        log_layout.addWidget(
            self.log_display
        )

        log_group.setLayout(
            log_layout
        )

        main_layout.addWidget(
            log_group
        )

        # -------------------------------------------------
        # EMERGENCY STOP
        # -------------------------------------------------

        self.emergency_button = QPushButton(
            "NGẮT KHẨN CẤP"
        )

        self.emergency_button.setMinimumHeight(
            55
        )

        self.emergency_button.setStyleSheet(
            """
            QPushButton {
                font-size: 18px;
                font-weight: bold;
            }
            """
        )

        self.emergency_button.clicked.connect(
            self.emergency_stop
        )

        main_layout.addWidget(
            self.emergency_button
        )

        self.setLayout(
            main_layout
        )

    # =====================================================
    # LOG
    # =====================================================

    def add_log(self, message):

        self.log_display.append(
            message
        )

        logging.info(
            message
        )

    # =====================================================
    # START SERVER
    # =====================================================

    def start_server(self):

        port = self.port_input.value()

        self.running = True

        self.start_button.setEnabled(
            False
        )

        self.stop_button.setEnabled(
            True
        )

        self.port_input.setEnabled(
            False
        )

        self.status_label.setText(
            "● WAITING FOR CLIENT"
        )

        self.add_log(
            f"Host started on port {port}"
        )

        # Server phải chạy thread riêng
        # để GUI không bị treo
        self.server_thread = threading.Thread(
            target=self.run_server,
            args=(port,),
            daemon=True
        )

        self.server_thread.start()

    # =====================================================
    # RUN SERVER
    # =====================================================

    def run_server(self, port):

        try:

            start_server(
                ip="0.0.0.0",
                port=port,
                on_connection_request=(
                    self.on_connection_request
                )
            )

        except Exception as e:

            self.add_log(
                f"SERVER ERROR: {e}"
            )

    # =====================================================
    # SERVER → GUI CALLBACK
    # =====================================================

    def on_connection_request(
        self,
        client_ip
    ):
        """
        Hàm này được server_core.py gọi
        khi Client gửi CMD_REQ_CONNECT.
        """

        self.client_ip = client_ip

        # Reset kết quả
        self.connection_result = None

        # Gửi yêu cầu về GUI thread
        self.connection_request_signal.emit(
            client_ip
        )

        # =================================================
        # CHỜ GUI CHỌN ACCEPT / REJECT
        # =================================================

        while (
            self.connection_result is None
            and self.running
        ):

            # Không dùng busy loop quá mạnh
            import time
            time.sleep(0.1)

        # Nếu Host bị Stop / Emergency
        if not self.running:

            return False

        return self.connection_result

    # =====================================================
    # POPUP ACCEPT / REJECT
    # =====================================================

    def show_connection_dialog(
        self,
        client_ip
    ):

        self.client_label.setText(
            f"Client: {client_ip}"
        )

        self.status_label.setText(
            "● CONNECTION REQUEST"
        )

        self.add_log(
            f"Connection request from "
            f"{client_ip}"
        )

        dialog = QMessageBox(
            self
        )

        dialog.setWindowTitle(
            "Yêu cầu kết nối"
        )

        dialog.setIcon(
            QMessageBox.Question
        )

        dialog.setText(
            "Có yêu cầu kết nối từ xa!"
        )

        dialog.setInformativeText(
            f"Client IP: {client_ip}\n\n"
            "Bạn có muốn cho phép "
            "điều khiển máy tính không?"
        )

        accept_button = dialog.addButton(
            "CHẤP NHẬN",
            QMessageBox.AcceptRole
        )

        reject_button = dialog.addButton(
            "TỪ CHỐI",
            QMessageBox.RejectRole
        )

        dialog.exec_()

        clicked_button = dialog.clickedButton()

        # -------------------------------------------------
        # ACCEPT
        # -------------------------------------------------

        if clicked_button == accept_button:

            self.connection_result = True

            self.permission_label.setText(
                "Quyền điều khiển: ĐÃ CẤP"
            )

            self.status_label.setText(
                "● REMOTE CONTROL ACTIVE"
            )

            self.add_log(
                f"ACCEPTED: {client_ip}"
            )

        # -------------------------------------------------
        # REJECT
        # -------------------------------------------------

        else:

            self.connection_result = False

            self.permission_label.setText(
                "Quyền điều khiển: BỊ TỪ CHỐI"
            )

            self.status_label.setText(
                "● CONNECTION REJECTED"
            )

            self.add_log(
                f"REJECTED: {client_ip}"
            )

    # =====================================================
    # STOP SERVER
    # =====================================================

    def stop_server(self):

        self.running = False

        self.add_log(
            "Host stopped"
        )

        self.status_label.setText(
            "● OFFLINE"
        )

        self.client_label.setText(
            "Client: Chưa kết nối"
        )

        self.permission_label.setText(
            "Quyền điều khiển: CHƯA CẤP"
        )

        self.start_button.setEnabled(
            True
        )

        self.stop_button.setEnabled(
            False
        )

        self.port_input.setEnabled(
            True
        )

        # Lưu ý:
        # server_core hiện tại chưa có hàm stop_server()
        # nên phần đóng socket sẽ xử lý sau.

    # =====================================================
    # EMERGENCY STOP
    # =====================================================

    def emergency_stop(self):

        self.running = False

        self.connection_result = False

        logging.warning(
            "EMERGENCY STOP"
        )

        self.add_log(
            "!!! NGẮT KHẨN CẤP !!!"
        )

        self.status_label.setText(
            "● EMERGENCY STOPPED"
        )

        self.client_label.setText(
            "Client: Đã ngắt"
        )

        self.permission_label.setText(
            "Quyền điều khiển: ĐÃ NGẮT"
        )

        self.start_button.setEnabled(
            True
        )

        self.stop_button.setEnabled(
            False
        )

        self.port_input.setEnabled(
            True
        )

    # =====================================================
    # CLOSE WINDOW
    # =====================================================

    def closeEvent(
        self,
        event
    ):

        self.running = False

        self.connection_result = False

        logging.info(
            "Host GUI closed"
        )

        event.accept()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # --- CHÈN THÊM DÒNG NÀY ĐỂ NẠP DARK MODE ---
    with open("style.qss", "r", encoding="utf-8") as f:
        app.setStyleSheet(f.read())
    # -------------------------------------------

    window = HostGUI()
    window.show()
    sys.exit(app.exec_())