import socket
import time
from common.protocol import send_message, receive_message, CMD_REQ_CONNECT, CMD_RES_CONNECT

def start_test_client(ip="127.0.0.1", port=9999):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        print(f"[CLIENT] Đang kết nối tới Server {ip}:{port}...")
        client.connect((ip, port))
        print("[CLIENT] Kết nối TCP thành công!")

        # 1. Test gửi lệnh Xin kết nối (Không có dữ liệu đi kèm, payload rỗng)
        print("[CLIENT] Đang gửi yêu cầu CMD_REQ_CONNECT...")
        send_message(client, CMD_REQ_CONNECT)

        # 2. Chờ Server phản hồi
        cmd, payload = receive_message(client)
        if cmd == CMD_RES_CONNECT:
            # Lấy byte đầu tiên ra xem là 1 (Đồng ý) hay 0 (Từ chối)
            status = payload[0]
            if status == 1:
                print("[CLIENT] Server ĐÃ ĐỒNG Ý kết nối!")
            else:
                print("[CLIENT] Server ĐÃ TỪ CHỐI kết nối!")
        
        # Giữ kết nối một lúc để xem Server có treo không
        time.sleep(5)

    except ConnectionRefusedError:
        print("[CLIENT] Lỗi: Không thể kết nối. Server chưa bật hoặc sai Port!")
    except Exception as e:
        print(f"[CLIENT] Có lỗi xảy ra: {e}")
    finally:
        client.close()
        print("[CLIENT] Đã đóng kết nối an toàn.")

if __name__ == "__main__":
    start_test_client()