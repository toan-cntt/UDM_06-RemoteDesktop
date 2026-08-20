import json

from PyQt5.QtCore import QObject, QEvent, Qt

from common.protocol import CMD_MOUSE, send_message, CMD_KEY


class InputEventFilter(QObject):

    def __init__(self, client_socket, parent=None):
        super().__init__(parent)

        self.client_socket = client_socket

        # Lưu vị trí cuối cùng đã gửi
        self.last_x = -1
        self.last_y = -1

        # Khoảng cách tối thiểu giữa 2 lần gửi
        self.move_threshold = 5


    def eventFilter(self, obj, event):

        # CLICK CHUỘT

        if event.type() == QEvent.MouseButtonPress:

            x = event.pos().x()
            y = event.pos().y()

            width = obj.width()
            height = obj.height()

            if width <= 0 or height <= 0:
                return True

            x_rel = x / width
            y_rel = y / height

            x_rel = max(0.0, min(1.0, x_rel))
            y_rel = max(0.0, min(1.0, y_rel))

            if event.button() == Qt.LeftButton:
                button = "left"

            elif event.button() == Qt.RightButton:
                button = "right"

            else:
                return True
        

            data = {
                "action": "down",
                "button": button,
                "x": x_rel,
                "y": y_rel
            }

            self.send_input_data(CMD_MOUSE,data)

            return True
    

        # DI CHUỘT

        if event.type() == QEvent.MouseMove:

            x = event.pos().x()
            y = event.pos().y()

            # Kiểm tra khoảng cách với vị trí trước
            if self.last_x >= 0 and self.last_y >= 0:

                dx = abs(x - self.last_x)
                dy = abs(y - self.last_y)

                if dx < self.move_threshold and dy < self.move_threshold:
                    return True

            width = obj.width()
            height = obj.height()

            if width <= 0 or height <= 0:
                return True
            
            # Tọa độ tương đối
            x_rel = x / width
            y_rel = y / height

            x_rel = max(0.0, min(1.0, x_rel))
            y_rel = max(0.0, min(1.0, y_rel))
    
            data = {
                "action": "move",
                "x": x_rel,
                "y": y_rel
            }

            self.send_input_data(CMD_MOUSE,data)

            # Lưu vị trí vừa gửi
            self.last_x = x
            self.last_y = y

            return True

        # Cuộn chuột

        if event.type() == QEvent.Wheel:

            delta = event.angleDelta().y()

            if delta == 0:
                return True

            # Qt:
            # delta > 0 → cuộn lên
            # delta < 0 → cuộn xuống

            if delta > 0:
                dy = 1
            else:
                dy = -1

            data = {
                "action": "scroll",
                "dx": 0,
                "dy": dy
            }

            self.send_input_data(
                CMD_MOUSE,
                data
            )

            return True

        #Thả chuột
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                button = "left"

            elif event.button() == Qt.RightButton:
                button = "right"

            else:
                return True
            x = event.pos().x()
            y = event.pos().y()

            width = obj.width()
            height = obj.height()

            if width <= 0 or height <= 0:
                return True

            x_rel = x / width
            y_rel = y / height

            x_rel = max(0.0, min(1.0, x_rel))
            y_rel = max(0.0, min(1.0, y_rel))

            data = {
                "action": "up",
                "button": button,
                "x": x_rel,
                "y": y_rel
            }

            self.send_input_data(
                CMD_MOUSE,
                data
            )

            return True
        
        #Bàn phím

        if event.type() == QEvent.KeyPress:

            key = self.get_key_name(event)

            data = {
                "action": "down",
                "key": key
            }

            self.send_input_data(CMD_KEY,data)

            return True

        if event.type() == QEvent.KeyRelease:

            key = self.get_key_name(event)

            data = {
                "action": "up",
                "key": key
            }

            self.send_input_data(CMD_KEY,data)

            return True
        return super().eventFilter(obj, event)
        

    # GỬI DATA INPUT

    def send_input_data(self, command, data):
        payload = json.dumps(data).encode("utf-8")

        try:
            send_message(
                self.client_socket,
                command,
                payload
            )

            print("Input event sent:", data)

        except Exception as e:
            print("Failed to send input event:", e)

    #Định dạng input
    def get_key_name(self, event):

        key = event.key()

        special_keys = {
            Qt.Key_Return: "enter",
            Qt.Key_Enter: "enter",
            Qt.Key_Backspace: "backspace",
            Qt.Key_Tab: "tab",
            Qt.Key_Escape: "esc",
            Qt.Key_Delete: "delete",
            Qt.Key_Insert: "insert",
            Qt.Key_Home: "home",
            Qt.Key_End: "end",
            Qt.Key_PageUp: "pageup",
            Qt.Key_PageDown: "pagedown",

            Qt.Key_Left: "left",
            Qt.Key_Right: "right",
            Qt.Key_Up: "up",
            Qt.Key_Down: "down",

            Qt.Key_Shift: "shift",
            Qt.Key_Control: "ctrl",
            Qt.Key_Alt: "alt",
            Qt.Key_Meta: "win",

            Qt.Key_Space: "space"
        }

        if key in special_keys:
            return special_keys[key]

        # Phím thông thường
        text = event.text()

        if text:
            return text

        # F1 -> F12
        if Qt.Key_F1 <= key <= Qt.Key_F12:
            return f"f{key - Qt.Key_F1 + 1}"

        return str(key) 
