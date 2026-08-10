import io
import time
import mss
from PIL import Image
from common.protocol import send_message, CMD_SCREEN

def capture_screen(quality=70):
    # Chụp màn hình và nén thành JPEG
    # Trả về dữ liệu ảnh dưới dạng bytes

    with mss.MSS() as sct:
        # monitors[0] = toàn bộ màn hình
        # monitors[1] = màn hình chính
        monitor = sct.monitors[1]

        screenshot = sct.grab(monitor)

        # Chuyển ảnh MSS sang Pillow
        image = Image.frombytes(
            "RGB",
            screenshot.size,
            screenshot.rgb
        )

        # Lưu ảnh vào bộ nhớ
        buffer = io.BytesIO()

        # Nén thành JPEG
        image.save(
            buffer,
            format="JPEG",
            quality=quality
        )

        return buffer.getvalue()

def send_screen(sock, quality=70):
    # Chụp màn hình, nén JPEG và gửi qua TCP

    image_bytes = capture_screen(quality)

    send_message(
        sock,
        CMD_SCREEN,
        image_bytes
    )

def screen_stream(sock, fps=10, quality=70):
    # Liên tục chụp và gửi màn hình
    # sock: TCP socket
    # fps: số frame mỗi giây
    # quality: chất lượng JPEG

    delay = 1 / fps

    while True:
        start_time = time.time()

        send_screen(sock, quality)

        elapsed = time.time() - start_time
        sleep_time = delay - elapsed

        if sleep_time > 0:
            time.sleep(sleep_time)