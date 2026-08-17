from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from common.protocol import receive_message, CMD_SCREEN


class ImageReceiverThread(QThread):
    """
    Thread chuyên nhận và decode frame màn hình từ Server.
    """

    image_received = pyqtSignal(QImage)
    connection_error = pyqtSignal(str)
    receiver_stopped = pyqtSignal()

    def __init__(self, client_socket, parent=None):
        super().__init__(parent)

        self.client_socket = client_socket
        self.running = True
    
    def run(self):

        try:
            while self.running:

                cmd_type, payload = receive_message(
                    self.client_socket
                )

                # Socket bị đóng / mất kết nối
                if not cmd_type:
                    break

                # Chỉ xử lý packet màn hình
                if cmd_type != CMD_SCREEN:
                    continue

                # Nếu thread đã được yêu cầu dừng
                if not self.running:
                    break

                # Decode JPEG thành QImage
                image = QImage()

                if not image.loadFromData(payload, "JPEG"):
                    print("[TV4] Không thể decode frame JPEG")
                    continue

                # Gửi QImage về GUI thread
                self.image_received.emit(image)

        except Exception as e:

            if self.running:
                print(f"[TV4] Lỗi nhận màn hình: {e}")
                self.connection_error.emit(str(e))

        finally:

            self.receiver_stopped.emit()

    def stop(self):

        self.running = False