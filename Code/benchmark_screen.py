import time
import mss
import numpy as np
import cv2


def capture_screen(sct, quality=70, scale=0.75):
    monitor = sct.monitors[1]

    # Chụp màn hình
    screenshot = sct.grab(monitor)

    # MSS -> NumPy
    frame = np.array(screenshot)

    # BGRA -> BGR
    frame = cv2.cvtColor(
        frame,
        cv2.COLOR_BGRA2BGR
    )

    # Resize
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
        raise RuntimeError("Không thể nén ảnh")

    return encoded_image.tobytes()


def benchmark(iterations=50, quality=70, scale=0.75):

    total_time = 0
    total_size = 0

    print("\n=== SCREEN STREAM BENCHMARK ===")
    print(f"Iterations: {iterations}")
    print(f"JPEG Quality: {quality}")
    print(f"Scale: {scale * 100:.0f}%")
    print("-" * 40)

    # Chỉ khởi tạo MSS MỘT LẦN
    with mss.MSS() as sct:

        for _ in range(iterations):

            start_time = time.perf_counter()

            image_bytes = capture_screen(
                sct,
                quality=quality,
                scale=scale
            )

            elapsed = time.perf_counter() - start_time

            total_time += elapsed
            total_size += len(image_bytes)

    avg_time = total_time / iterations
    avg_size = total_size / iterations
    estimated_fps = 1 / avg_time

    print("=== RESULT ===")
    print(f"Average capture + encode: {avg_time * 1000:.2f} ms")
    print(f"Average JPEG size: {avg_size / 1024:.2f} KB")
    print(f"Estimated maximum FPS: {estimated_fps:.2f}")

    return {
        "scale": scale,
        "time": avg_time,
        "size": avg_size,
        "fps": estimated_fps
    }


if __name__ == "__main__":

    results = []

    results.append(
        benchmark(
            iterations=50,
            quality=70,
            scale=1.0
        )
    )

    results.append(
        benchmark(
            iterations=50,
            quality=70,
            scale=0.75
        )
    )

    results.append(
        benchmark(
            iterations=50,
            quality=70,
            scale=0.5
        )
    )

    print("\n" + "=" * 55)
    print("FINAL COMPARISON")
    print("=" * 55)

    for result in results:
        print(
            f"Scale {result['scale'] * 100:.0f}% | "
            f"{result['time'] * 1000:.2f} ms | "
            f"{result['size'] / 1024:.2f} KB | "
            f"{result['fps']:.2f} FPS"
        )