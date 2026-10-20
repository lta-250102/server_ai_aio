"""
Locust load test cho API /yolo/detect
Chạy: locust -f locustfile.py --host http://localhost:8080
"""

import random
from locust import HttpUser, task, between


class YoloDetectUser(HttpUser):
    """User mô phỏng gọi API detect ảnh qua YOLO."""

    wait_time = between(1, 3)  # Chờ 1-3 giây giữa các request

    @task(3)
    def detect(self):
        """POST /yolo/detect - Gửi ảnh để detect objects."""
        image_path = random.choice(self.image_files)
        with open(image_path, "rb") as f:
            image_content = f.read()

        files = {"image": ("test.jpg", image_content, "image/jpeg")}
        with self.client.post("/yolo/detect", files=files, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}: {response.text[:200]}")

    def on_start(self):
        """Chuẩn bị danh sách ảnh test khi user bắt đầu."""
        import os
        test_dir = os.path.dirname(__file__)
        self.image_files = [
            os.path.join(test_dir, img)
            for img in os.listdir(test_dir)
            if img.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))
        ]
        if not self.image_files:
            raise FileNotFoundError(
                "Không tìm thấy ảnh test trong thư mục locust_test/. "
                "Hãy thêm ảnh .jpg/.png vào đó."
            )
