import sys

from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5.QtCore import Qt

from client.input_listener import InputEventFilter


class FakeSocket:
    """
    Socket giả để test.
    Không gửi dữ liệu thật qua mạng.
    """
    pass


class TestInputEventFilter(InputEventFilter):

    def __init__(self, client_socket, parent=None):
        super().__init__(self)
        self.move_threshold = 10

    def send_input_data(self, command, data):
        print("\n==============================")
        print("COMMAND:", command)
        print("DATA:", data)
        print("==============================")


app = QApplication(sys.argv)

# Widget dùng để nhận event
test_widget = QLabel("TEST INPUT LISTENER")
test_widget.resize(800, 600)
test_widget.setFocusPolicy(Qt.StrongFocus)



# Tạo InputEventFilter
fake_socket = FakeSocket()

input_filter = TestInputEventFilter(fake_socket)

# Gắn Event Filter vào widget
test_widget.installEventFilter(input_filter)

test_widget.show()
test_widget.setFocus()


test_widget.setMouseTracking(True)


print("================================")
print("INPUT LISTENER TEST")
print("================================")
print()
print("Test 1: Click chuột trái")
print("Test 2: Click chuột phải")
print("Test 3: Di chuyển chuột")
print("Test 4: Cuộn chuột")
print("Test 5: Nhấn phím")
print("Test 6: Thả phím")
print()
print("Hãy thao tác trực tiếp trên cửa sổ TEST.")


sys.exit(app.exec_())