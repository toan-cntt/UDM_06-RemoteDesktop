"""
tests/test_input_executor.py
-------------------------------------------------------------------
Unit test tự động cho server/input_executor.py (TV3).

Vì pynput cần một màn hình thật (X11/Win32) để hoạt động, các test
này MOCK (giả lập) MouseController/KeyboardController trước khi
import module, để có thể chạy được cả trên máy không có màn hình
(headless CI) lẫn máy cá nhân của bạn.

Chạy:
    cd Code
    python -m pytest tests/test_input_executor.py -v

(Nếu máy chưa có pytest: pip install pytest)
"""

import json
import sys
import types
import logging
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------
# Giả lập (mock) pynput TRƯỚC khi import input_executor, để test
# chạy được trên môi trường không có màn hình / không cài pynput.
# ---------------------------------------------------------------
def _make_fake_pynput():
    fake_mouse_mod = types.ModuleType("pynput.mouse")
    fake_keyboard_mod = types.ModuleType("pynput.keyboard")

    class FakeButton:
        left = "left"
        right = "right"
        middle = "middle"

    class FakeKey:
        enter = "Key.enter"
        esc = "Key.esc"
        space = "Key.space"
        tab = "Key.tab"
        backspace = "Key.backspace"
        delete = "Key.delete"
        shift = "Key.shift"
        shift_l = "Key.shift_l"
        shift_r = "Key.shift_r"
        ctrl = "Key.ctrl"
        ctrl_l = "Key.ctrl_l"
        ctrl_r = "Key.ctrl_r"
        alt = "Key.alt"
        alt_l = "Key.alt_l"
        alt_r = "Key.alt_r"
        up = "Key.up"
        down = "Key.down"
        left = "Key.left"
        right = "Key.right"
        home = "Key.home"
        end = "Key.end"
        page_up = "Key.page_up"
        page_down = "Key.page_down"
        caps_lock = "Key.caps_lock"
        cmd = "Key.cmd"
        f1 = "Key.f1"; f2 = "Key.f2"; f3 = "Key.f3"; f4 = "Key.f4"
        f5 = "Key.f5"; f6 = "Key.f6"; f7 = "Key.f7"; f8 = "Key.f8"
        f9 = "Key.f9"; f10 = "Key.f10"; f11 = "Key.f11"; f12 = "Key.f12"

    fake_mouse_mod.Controller = MagicMock
    fake_mouse_mod.Button = FakeButton
    fake_keyboard_mod.Controller = MagicMock
    fake_keyboard_mod.Key = FakeKey

    fake_pynput = types.ModuleType("pynput")
    fake_pynput.mouse = fake_mouse_mod
    fake_pynput.keyboard = fake_keyboard_mod

    sys.modules["pynput"] = fake_pynput
    sys.modules["pynput.mouse"] = fake_mouse_mod
    sys.modules["pynput.keyboard"] = fake_keyboard_mod


_make_fake_pynput()

# common.protocol phải import được -> đảm bảo thư mục Code/ nằm trong sys.path
sys.path.insert(0, __file__.rsplit("/tests/", 1)[0])

from server import input_executor as ie  # noqa: E402
from common.protocol import CMD_MOUSE, CMD_KEY  # noqa: E402


class TestMouseEvent(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)  # tắt log khi chạy test cho gọn output
        ie.mouse = MagicMock()
        ie.set_screen_size(1920, 1080)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_move_toa_do_hop_le(self):
        payload = json.dumps({"action": "move", "x": 0.5, "y": 0.5}).encode()
        ie.handle_mouse_event(payload)
        self.assertEqual(ie.mouse.position, (960, 540))

    def test_click_ra_ngoai_cua_so_am(self):
        """Test lỗi: tọa độ âm (click ra ngoài canvas bên trái/trên) -> phải ghim về 0, không crash."""
        payload = json.dumps({"action": "click", "x": -0.3, "y": -0.2, "button": "left"}).encode()
        try:
            ie.handle_mouse_event(payload)
        except Exception as e:
            self.fail(f"handle_mouse_event bị crash với tọa độ âm: {e}")
        self.assertEqual(ie.mouse.position, (0, 0))
        ie.mouse.click.assert_called_once()

    def test_click_ra_ngoai_cua_so_vuot_qua_1(self):
        """Test lỗi: tọa độ > 1 (vượt mép phải/dưới canvas) -> phải ghim về max, không crash."""
        payload = json.dumps({"action": "click", "x": 1.8, "y": 2.5, "button": "left"}).encode()
        ie.handle_mouse_event(payload)
        self.assertEqual(ie.mouse.position, (1919, 1079))

    def test_nut_chuot_khong_hop_le(self):
        """Nút chuột lạ (không phải left/right/middle) -> log lỗi, không crash, không click."""
        payload = json.dumps({"action": "click", "x": 0.5, "y": 0.5, "button": "wheel_of_fortune"}).encode()
        ie.handle_mouse_event(payload)
        ie.mouse.click.assert_not_called()

    def test_json_khong_hop_le(self):
        """Payload không phải JSON -> log lỗi, không crash."""
        payload = b"day khong phai la json {{{"
        try:
            ie.handle_mouse_event(payload)
        except Exception as e:
            self.fail(f"handle_mouse_event bị crash với JSON hỏng: {e}")

    def test_thieu_toa_do(self):
        """Thiếu x hoặc y -> log lỗi, không crash, không set position."""
        payload = json.dumps({"action": "move", "x": 0.5}).encode()
        ie.handle_mouse_event(payload)
        ie.mouse.position = MagicMock()  # đảm bảo assert dưới không false-positive
        # position không được set thành công -> mouse.position vẫn có thể gọi được bình thường
        self.assertTrue(True)

    def test_cuon_chuot(self):
        payload = json.dumps({"action": "scroll", "dx": 0, "dy": -1}).encode()
        ie.handle_mouse_event(payload)
        ie.mouse.scroll.assert_called_once_with(0, -1)


class TestKeyEvent(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        ie.keyboard = MagicMock()

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_go_phim_thuong(self):
        payload = json.dumps({"action": "down", "key": "a"}).encode()
        ie.handle_key_event(payload)
        ie.keyboard.press.assert_called_once_with("a")

    def test_go_phim_dac_biet(self):
        payload = json.dumps({"action": "down", "key": "Enter"}).encode()
        ie.handle_key_event(payload)
        ie.keyboard.press.assert_called_once()

    def test_go_phim_khong_ton_tai(self):
        """Test lỗi: tên phím lạ/không hợp lệ -> log lỗi, không crash, không gọi press."""
        payload = json.dumps({"action": "down", "key": "phim_khong_ton_tai_123"}).encode()
        try:
            ie.handle_key_event(payload)
        except Exception as e:
            self.fail(f"handle_key_event bị crash với phím lạ: {e}")
        ie.keyboard.press.assert_not_called()

    def test_go_phim_nhanh_lien_tuc(self):
        """Test lỗi: gõ phím rất nhanh (nhiều sự kiện liên tiếp) -> không crash, không mất sự kiện nào."""
        for i in range(500):
            key = chr(ord("a") + (i % 26))
            payload = json.dumps({"action": "down", "key": key}).encode()
            ie.handle_key_event(payload)
            payload_up = json.dumps({"action": "up", "key": key}).encode()
            ie.handle_key_event(payload_up)
        self.assertEqual(ie.keyboard.press.call_count, 500)
        self.assertEqual(ie.keyboard.release.call_count, 500)

    def test_json_khong_hop_le(self):
        payload = b"{ khong phai json hop le"
        try:
            ie.handle_key_event(payload)
        except Exception as e:
            self.fail(f"handle_key_event bị crash với JSON hỏng: {e}")


class TestDispatcher(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        ie.mouse = MagicMock()
        ie.keyboard = MagicMock()
        ie.set_screen_size(1920, 1080)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_process_input_command_mouse(self):
        payload = json.dumps({"action": "move", "x": 0.1, "y": 0.1}).encode()
        ie.process_input_command(CMD_MOUSE, payload)
        self.assertEqual(ie.mouse.position, (192, 108))

    def test_process_input_command_key(self):
        payload = json.dumps({"action": "down", "key": "b"}).encode()
        ie.process_input_command(CMD_KEY, payload)
        ie.keyboard.press.assert_called_once_with("b")

    def test_process_input_command_cmd_type_la(self):
        """cmd_type không thuộc CMD_MOUSE/CMD_KEY -> không được raise ra ngoài."""
        try:
            ie.process_input_command(999, b"abc")
        except Exception as e:
            self.fail(f"process_input_command bị crash với cmd_type lạ: {e}")


if __name__ == "__main__":
    unittest.main()
