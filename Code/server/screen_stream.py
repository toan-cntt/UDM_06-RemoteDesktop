import time
import mss
import numpy as np
import cv2

from common.protocol import send_message, CMD_SCREEN


def capture_screen(sct, quality=70, scale=0.75):
    # Chụp màn hình và nén thành JPEG bằng OpenCV

    # monitors[1] = màn hình chính
    monitor = sct.monitors[1]

    # Chụp màn hình
    screenshot = sct.grab(monitor)

    # Chuyển ảnh MSS sang NumPy array
    frame = np.array(screenshot)

    # Chuyển BGRA sang BGR
    frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGRA2BGR
    )

    # Resize để giảm dung lượng truyền
    if scale != 1.0:
        frame = cv2.resize(
            frame,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA
        )

    # Nén JPEG
    success, encoded_image = cv2.imencode(
        ".jpg",
        frame,
        [
            cv2.IMWRITE_JPEG_QUALITY,
            quality
        ]
    )

    if not success:
        raise RuntimeError("Không thể nén ảnh màn hình")

    return encoded_image.tobytes()


def send_screen(sct, sock, quality=70, scale=0.75):
    # Chụp màn hình, nén JPEG và gửi qua TCP

    image_bytes = capture_screen(
        sct,
        quality=quality,
        scale=scale
    )

    send_message(
        sock,
        CMD_SCREEN,
        image_bytes
    )


def screen_stream(sock, fps=20, quality=70, scale=0.75):
    # Liên tục chụp và gửi màn hình

    delay = 1 / fps

    # Chỉ tạo MSS một lần
    with mss.MSS() as sct:

        while True:
            start_time = time.perf_counter()

            send_screen(
                sct,
                sock,
                quality=quality,
                scale=scale
            )

            elapsed = time.perf_counter() - start_time
            sleep_time = delay - elapsed

            if sleep_time > 0:
                time.sleep(sleep_time)