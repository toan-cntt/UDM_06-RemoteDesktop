"""
server/input_executor.py
-------------------------------------------------------------------
THÀNH VIÊN 3 - Host Input Executor (Mô phỏng Thao tác Máy Đích)

Module này nhận payload của gói tin CMD_MOUSE (=4) và CMD_KEY (=5)
(đã được server/core.py của TV1 bóc Header và đưa vào đây dưới dạng
bytes JSON), sau đó:
    1. Giải mã (decode) JSON.
    2. Quy đổi tọa độ tương đối (0.0 - 1.0) sang tọa độ điểm ảnh thật
       trên màn hình Host:
           X_host = X_rel * Width_host
           Y_host = Y_rel * Height_host
    3. Dùng pynput để thực thi thao tác (di chuột, click, cuộn, gõ phím).

Toàn bộ hàm public đều "nuốt" lỗi nội bộ (log lại, không raise ra
ngoài) để một gói tin lỗi/dị dạng không bao giờ làm crash luồng
Server đang chạy vòng lặp nhận lệnh.

-------------------------------------------------------------------
HƯỚNG DẪN TÍCH HỢP CHO TV1 (server/core.py)
-------------------------------------------------------------------
Trong vòng lặp nhận lệnh liên tục của server_core.py, hiện đang có:

    while True:
        try:
            msg_cmd, msg_payload = receive_message(client_socket)
            if not msg_cmd:
                break
            print(f"[SERVER] Nhận lệnh {msg_cmd} có kích thước {len(msg_payload)} bytes")
            # Truyền cho TV3 xử lý input ở đây
        except Exception as e:
            ...

Chỉ cần thêm 2 dòng:

    from server.input_executor import process_input_command
    ...
    if msg_cmd in (CMD_MOUSE, CMD_KEY):
        process_input_command(msg_cmd, msg_payload)

Module tự lo phần try/except bên trong nên không cần bọc thêm gì cả.

-------------------------------------------------------------------
CHUẨN JSON (do TV3 đề xuất - TV4 đóng gói phía Client theo đúng format này)
-------------------------------------------------------------------
CMD_MOUSE (payload là JSON UTF-8):
    Di chuột:
        {"action": "move", "x": 0.512, "y": 0.334}
    Nhấn/nhả chuột (down + up riêng biệt, để hỗ trợ kéo-thả):
        {"action": "down", "x": 0.512, "y": 0.334, "button": "left"}
        {"action": "up",   "x": 0.512, "y": 0.334, "button": "left"}
    Click nhanh (nhấn + nhả gộp lại, dùng khi không cần kéo-thả):
        {"action": "click", "x": 0.512, "y": 0.334, "button": "left"}
    Cuộn chuột (không cần x, y):
        {"action": "scroll", "dx": 0, "dy": -1}

    - x, y: số thực trong khoảng [0, 1], là tỷ lệ vị trí trên canvas
      hiển thị của Client (X_rel = X_client_click / Width_canvas).
    - button: "left" | "right" | "middle" (mặc định "left" nếu thiếu).

CMD_KEY (payload là JSON UTF-8):
        {"action": "down", "key": "a"}
        {"action": "up",   "key": "a"}
        {"action": "down", "key": "enter"}

    - key: 1 ký tự thường (vd "a", "1", "!") HOẶC tên phím đặc biệt
      (không phân biệt hoa thường) nằm trong SPECIAL_KEY_MAP bên dưới,
      ví dụ: "enter", "esc", "space", "tab", "backspace", "delete",
      "shift", "ctrl", "alt", "up", "down", "left", "right",
      "f1".."f12", "caps_lock", "cmd".
"""

import json
import logging

from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

from common.protocol import CMD_MOUSE, CMD_KEY

logger = logging.getLogger("input_executor")

# -------------------------------------------------------------------
# Controller dùng chung (khởi tạo 1 lần)
# -------------------------------------------------------------------
mouse = MouseController()
keyboard = KeyboardController()

# -------------------------------------------------------------------
# Độ phân giải màn hình Host - lấy 1 lần, cache lại (dùng thư viện mss
# đã có sẵn trong project, do TV2 dùng để chụp màn hình).
# -------------------------------------------------------------------
_screen_width = None
_screen_height = None


def _get_screen_size():
    """Lấy (width, height) màn hình chính của Host, cache lại sau lần gọi đầu."""
    global _screen_width, _screen_height
    if _screen_width is None or _screen_height is None:
        import mss
        with mss.mss() as sct:
            # monitors[0] là vùng gộp toàn bộ các màn hình, monitors[1] là màn hình chính
            monitor = sct.monitors[1]
            _screen_width = monitor["width"]
            _screen_height = monitor["height"]
    return _screen_width, _screen_height


def set_screen_size(width: int, height: int):
    """Cho phép ghi đè thủ công độ phân giải (dùng khi unit test, hoặc
    khi máy có nhiều màn hình và cần chọn màn hình khác)."""
    global _screen_width, _screen_height
    _screen_width, _screen_height = width, height


# -------------------------------------------------------------------
# Bảng ánh xạ nút chuột / phím đặc biệt
# -------------------------------------------------------------------
BUTTON_MAP = {
    "left": Button.left,
    "right": Button.right,
    "middle": Button.middle,
}

SPECIAL_KEY_MAP = {
    "enter": Key.enter, "esc": Key.esc, "escape": Key.esc,
    "space": Key.space, "tab": Key.tab, "backspace": Key.backspace,
    "delete": Key.delete,
    "shift": Key.shift, "shift_l": Key.shift_l, "shift_r": Key.shift_r,
    "ctrl": Key.ctrl, "ctrl_l": Key.ctrl_l, "ctrl_r": Key.ctrl_r,
    "alt": Key.alt, "alt_l": Key.alt_l, "alt_r": Key.alt_r,
    "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
    "home": Key.home, "end": Key.end,
    "page_up": Key.page_up, "page_down": Key.page_down,
    "caps_lock": Key.caps_lock, "cmd": Key.cmd,
}
SPECIAL_KEY_MAP.update({f"f{i}": getattr(Key, f"f{i}") for i in range(1, 13)})


def _clamp(value: float, min_v: float, max_v: float) -> float:
    return max(min_v, min(max_v, value))


# -------------------------------------------------------------------
# Xử lý CMD_MOUSE
# -------------------------------------------------------------------
def handle_mouse_event(payload: bytes):
    try:
        data = json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as e:
        logger.error(f"[MOUSE] Payload JSON không hợp lệ: {e} | raw={payload!r}")
        return

    if not isinstance(data, dict):
        logger.error(f"[MOUSE] Payload không phải object JSON: {data!r}")
        return

    action = data.get("action")

    if action == "scroll":
        try:
            dx = int(data.get("dx", 0))
            dy = int(data.get("dy", 0))
            mouse.scroll(dx, dy)
        except Exception as e:
            logger.error(f"[MOUSE] Lỗi khi cuộn chuột: {e}")
        return

    # Các action còn lại đều cần tọa độ x, y
    x_rel, y_rel = data.get("x"), data.get("y")
    if x_rel is None or y_rel is None:
        logger.error(f"[MOUSE] Thiếu tọa độ x/y trong payload: {data}")
        return

    try:
        x_rel = float(x_rel)
        y_rel = float(y_rel)
    except (TypeError, ValueError):
        logger.error(f"[MOUSE] Tọa độ x/y không phải số: {data}")
        return

    # Trường hợp lỗi "click ra ngoài cửa sổ": Client lỡ gửi x/y ngoài
    # [0, 1] (vd kéo chuột ra ngoài canvas). Thay vì bỏ qua hẳn sự kiện,
    # ta ghim (clamp) về biên gần nhất để trải nghiệm mượt hơn, đồng
    # thời log cảnh báo để phục vụ việc kiểm thử/ghi log.
    if not (0.0 <= x_rel <= 1.0) or not (0.0 <= y_rel <= 1.0):
        logger.warning(f"[MOUSE] Tọa độ ngoài phạm vi [0,1]: x={x_rel}, y={y_rel} -> đã ghim về biên")
    x_rel = _clamp(x_rel, 0.0, 1.0)
    y_rel = _clamp(y_rel, 0.0, 1.0)

    try:
        width, height = _get_screen_size()
    except Exception as e:
        logger.error(f"[MOUSE] Không lấy được độ phân giải màn hình: {e}")
        return

    x_host = min(int(x_rel * width), width - 1)
    y_host = min(int(y_rel * height), height - 1)

    try:
        mouse.position = (x_host, y_host)
    except Exception as e:
        logger.error(f"[MOUSE] Lỗi khi di chuyển chuột tới ({x_host},{y_host}): {e}")
        return

    if action == "move":
        return

    if action in ("down", "up", "click"):
        button_name = data.get("button", "left")
        button = BUTTON_MAP.get(button_name)
        if button is None:
            logger.error(f"[MOUSE] Tên nút chuột không hợp lệ: {button_name!r}")
            return
        try:
            if action == "down":
                mouse.press(button)
            elif action == "up":
                mouse.release(button)
            else:  # click gộp
                mouse.click(button, 1)
        except Exception as e:
            logger.error(f"[MOUSE] Lỗi khi thực thi '{action}' nút {button_name}: {e}")
        return

    logger.error(f"[MOUSE] Hành động (action) không xác định: {action!r} | payload={data}")


# -------------------------------------------------------------------
# Xử lý CMD_KEY
# -------------------------------------------------------------------
def handle_key_event(payload: bytes):
    try:
        data = json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as e:
        logger.error(f"[KEY] Payload JSON không hợp lệ: {e} | raw={payload!r}")
        return

    if not isinstance(data, dict):
        logger.error(f"[KEY] Payload không phải object JSON: {data!r}")
        return

    action = data.get("action")
    key_str = data.get("key")

    if not key_str or not isinstance(key_str, str):
        logger.error(f"[KEY] Thiếu hoặc sai định dạng trường 'key': {data}")
        return

    if key_str.lower() in SPECIAL_KEY_MAP:
        key_obj = SPECIAL_KEY_MAP[key_str.lower()]
    elif len(key_str) == 1:
        key_obj = key_str
    else:
        # Trường hợp lỗi: tên phím lạ / gõ phím không hợp lệ -> chỉ log,
        # không crash (đáp ứng yêu cầu test "gõ phím nhanh"/phím lạ).
        logger.error(f"[KEY] Không nhận diện được phím: {key_str!r}")
        return

    try:
        if action == "down":
            keyboard.press(key_obj)
        elif action == "up":
            keyboard.release(key_obj)
        else:
            logger.error(f"[KEY] Hành động (action) không xác định: {action!r}")
    except Exception as e:
        logger.error(f"[KEY] Lỗi khi thực thi phím {key_str!r} ({action}): {e}")


# -------------------------------------------------------------------
# Điểm vào duy nhất mà TV1 cần gọi
# -------------------------------------------------------------------
def process_input_command(cmd_type: int, payload: bytes):
    """Dispatcher chính. Không bao giờ raise exception ra ngoài."""
    try:
        if cmd_type == CMD_MOUSE:
            handle_mouse_event(payload)
        elif cmd_type == CMD_KEY:
            handle_key_event(payload)
        else:
            logger.warning(f"[INPUT] cmd_type={cmd_type} không thuộc phạm vi input_executor")
    except Exception as e:
        # Lưới an toàn cuối cùng: dù có lỗi lạ cỡ nào cũng không được
        # làm chết luồng nhận lệnh của Server.
        logger.error(f"[INPUT] Lỗi không xác định khi xử lý input: {e}")
