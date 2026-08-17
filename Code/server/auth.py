"""
server/auth.py
-------------------------------------------------------------------
THÀNH VIÊN 3 - Server Core Logic (Sprint 2 - Tuần 1)

Quản lý và xác thực thông tin đăng nhập kiểu UltraViewer:
    - ID:       6 chữ số, gắn với Host, không đổi trong suốt phiên
                chạy chương trình (có thể cố định vĩnh viễn nếu đọc
                từ file cấu hình, xem init_credentials()).
    - Password: 4 chữ số, sinh ngẫu nhiên, có thể đổi mới bất cứ lúc
                nào (nút "Đổi mật khẩu" trên GUI của TV5 sẽ gọi
                regenerate_password()).

-------------------------------------------------------------------
HƯỚNG DẪN TÍCH HỢP CHO TV1 (server/core.py) & TV5 (host_gui.py)
-------------------------------------------------------------------
1) Khi Host khởi động (trong host_gui.py hoặc server_core.py), gọi:

        from server.auth import init_credentials, get_current_credentials
        host_id, host_password = init_credentials()
        # -> hiển thị host_id, host_password lên 2 ô to trên giao diện Host

   Nếu muốn ID cố định vĩnh viễn cho máy (đúng chuẩn UltraViewer, ID
   không đổi mỗi lần mở app), đọc ID đã lưu từ file cấu hình và
   truyền vào: init_credentials(fixed_id="123456").

2) Khi người dùng bấm nút "Đổi mật khẩu" trên GUI:

        from server.auth import regenerate_password
        new_password = regenerate_password()
        # -> cập nhật lại ô hiển thị password trên giao diện

3) Trong server_core.py, khi nhận được gói CMD_AUTH_REQ từ Client
   (payload JSON do TV1 định nghĩa trong protocol.py, gợi ý cấu trúc:
   {"id": "123456", "password": "5678"}), gọi:

        from server.auth import verify_credentials
        import json

        req = json.loads(payload.decode("utf-8"))
        ok = verify_credentials(
            req.get("id", ""),
            req.get("password", ""),
            client_ip=client_address[0],   # dùng cho chống brute-force, có thể bỏ qua
        )
        send_message(
            client_socket,
            CMD_AUTH_RES,
            bytearray([1 if ok else 0]),
        )
        if not ok:
            client_socket.close()   # từ chối, đóng kết nối
            return

Module tự lo phần try/except bên trong, verify_credentials() không
bao giờ raise exception ra ngoài - luôn trả về True/False.
"""

import random
import string
import logging
import time

logger = logging.getLogger("auth")

# -------------------------------------------------------------------
# Trạng thái đăng nhập hiện tại của Host (in-memory, 1 Host = 1 phiên)
# -------------------------------------------------------------------
_current_id = None
_current_password = None

# -------------------------------------------------------------------
# Chống dò mật khẩu (brute-force) đơn giản: khóa tạm thời 1 IP sau
# nhiều lần nhập sai liên tiếp. Đây là phần "Bảo mật" bổ sung, không
# bắt buộc phải dùng - nếu TV1 không truyền client_ip, tính năng này
# tự động bỏ qua (không ảnh hưởng hàm chính).
# -------------------------------------------------------------------
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 30

_failed_attempts = {}   # {ip: [số lần sai, thời điểm sai cuối]}


def _generate_id() -> str:
    return "".join(random.choices(string.digits, k=6))


def _generate_password() -> str:
    return "".join(random.choices(string.digits, k=4))


def init_credentials(fixed_id: str = None):
    """Khởi tạo ID + Password cho phiên chạy hiện tại của Host.

    fixed_id: nếu truyền vào (đọc từ file cấu hình lưu trên máy), ID
    sẽ cố định theo giá trị này thay vì random mỗi lần mở app - đúng
    kiểu UltraViewer (ID gắn với máy). Nếu None, sinh ID ngẫu nhiên.
    Password luôn được sinh ngẫu nhiên mỗi lần gọi hàm này.
    """
    global _current_id, _current_password
    _current_id = fixed_id if fixed_id else _generate_id()
    _current_password = _generate_password()
    _failed_attempts.clear()
    logger.info(f"[AUTH] Đã khởi tạo thông tin đăng nhập, ID={_current_id}")
    return _current_id, _current_password


def regenerate_password() -> str:
    """Đổi mật khẩu mới, giữ nguyên ID. Dùng khi người dùng bấm nút
    'Đổi mật khẩu' trên giao diện Host."""
    global _current_password
    if _current_id is None:
        init_credentials()
    _current_password = _generate_password()
    logger.info("[AUTH] Đã đổi mật khẩu mới")
    return _current_password


def get_current_credentials():
    """Trả về (id, password) hiện tại để GUI hiển thị. Tự khởi tạo
    nếu chưa có (an toàn khi gọi sớm)."""
    if _current_id is None or _current_password is None:
        init_credentials()
    return _current_id, _current_password


def _is_locked_out(client_ip: str) -> bool:
    if not client_ip or client_ip not in _failed_attempts:
        return False
    count, last_fail_time = _failed_attempts[client_ip]
    if count >= MAX_FAILED_ATTEMPTS and (time.time() - last_fail_time) < LOCKOUT_SECONDS:
        return True
    if count >= MAX_FAILED_ATTEMPTS and (time.time() - last_fail_time) >= LOCKOUT_SECONDS:
        # Hết thời gian khóa -> reset để cho thử lại
        _failed_attempts.pop(client_ip, None)
    return False


def _record_failed_attempt(client_ip: str):
    if not client_ip:
        return
    count, _ = _failed_attempts.get(client_ip, (0, 0))
    _failed_attempts[client_ip] = (count + 1, time.time())
    if count + 1 >= MAX_FAILED_ATTEMPTS:
        logger.warning(f"[AUTH] IP {client_ip} bị khóa tạm thời {LOCKOUT_SECONDS}s do nhập sai quá nhiều lần")


def verify_credentials(input_id: str, input_pass: str, client_ip: str = None) -> bool:
    """Kiểm tra ID + Password Client gửi lên có khớp với Host hiện tại
    hay không. Luôn trả về True/False, không bao giờ raise exception.

    client_ip: tuỳ chọn, dùng để khóa tạm thời IP sau nhiều lần sai
    liên tiếp (chống dò mật khẩu). Có thể bỏ qua nếu TV1 chưa cần.
    """
    try:
        if _is_locked_out(client_ip):
            logger.warning(f"[AUTH] Từ chối xác thực - IP {client_ip} đang bị khóa tạm thời")
            return False

        if _current_id is None or _current_password is None:
            logger.warning("[AUTH] Chưa khởi tạo thông tin đăng nhập của Host (chưa gọi init_credentials)")
            return False

        if not isinstance(input_id, str) or not isinstance(input_pass, str):
            logger.warning(f"[AUTH] Kiểu dữ liệu id/password không hợp lệ: {type(input_id)}, {type(input_pass)}")
            _record_failed_attempt(client_ip)
            return False

        input_id = input_id.strip()
        input_pass = input_pass.strip()

        # Kiểm tra định dạng: ID phải đúng 6 chữ số, Password đúng 4 chữ số
        if not (input_id.isdigit() and len(input_id) == 6):
            logger.warning(f"[AUTH] ID sai định dạng (phải là 6 chữ số): {input_id!r}")
            _record_failed_attempt(client_ip)
            return False

        if not (input_pass.isdigit() and len(input_pass) == 4):
            logger.warning(f"[AUTH] Password sai định dạng (phải là 4 chữ số): {input_pass!r}")
            _record_failed_attempt(client_ip)
            return False

        is_valid = (input_id == _current_id) and (input_pass == _current_password)

        if is_valid:
            _failed_attempts.pop(client_ip, None)
            logger.info(f"[AUTH] Xác thực THÀNH CÔNG cho ID={input_id}")
        else:
            _record_failed_attempt(client_ip)
            logger.warning(f"[AUTH] Xác thực THẤT BẠI cho ID={input_id}")

        return is_valid

    except Exception as e:
        logger.error(f"[AUTH] Lỗi không xác định khi xác thực: {e}")
        return False
