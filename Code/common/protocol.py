import struct
import socket

# Cấu trúc Header: 1 Byte cho Loại Lệnh, 4 Bytes cho Độ dài dữ liệu (Chuẩn !BI)
HEADER_FORMAT = "!BI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# Danh sách các mã lệnh giao tiếp
CMD_REQ_CONNECT = 1   # Xin kết nối
CMD_RES_CONNECT = 2   # Phản hồi (1 = OK, 0 = No)
CMD_SCREEN      = 3   # Dữ liệu ảnh màn hình
CMD_MOUSE       = 4   # Tọa độ chuột
CMD_KEY         = 5   # Phím bấm

def send_message(sock: socket.socket, cmd_type: int, payload: bytes = b''):
    """Hàm đóng gói dữ liệu và gửi đi"""
    # Tính độ dài của cục dữ liệu (payload)
    payload_length = len(payload)
    
    # Đóng gói Header (Mã lệnh + Độ dài)
    header = struct.pack(HEADER_FORMAT, cmd_type, payload_length)
    
    # Gửi Header + Dữ liệu thực tế qua đường ống mạng
    sock.sendall(header + payload)

def receive_all(sock: socket.socket, length: int) -> bytes:
    """Hàm gom đủ số byte mới cho đi tiếp (chống lỗi mẻ gói tin)"""
    data = bytearray()
    while len(data) < length:
        packet = sock.recv(length - len(data))
        if not packet:
            return None # Rớt mạng
        data.extend(packet)
    return bytes(data)

def receive_message(sock: socket.socket):
    """Hàm nhận và tách gói tin"""
    # 1. Đọc đủ 5 byte đầu tiên (Header)
    header_bytes = receive_all(sock, HEADER_SIZE)
    if not header_bytes:
        return None, None
    
    # 2. Giải mã Header để biết: Đây là lệnh gì? Độ dài bao nhiêu?
    cmd_type, payload_length = struct.unpack(HEADER_FORMAT, header_bytes)
    
    # 3. Đọc tiếp phần dữ liệu thực tế dựa trên độ dài vừa lấy được
    payload = receive_all(sock, payload_length)
    
    return cmd_type, payload