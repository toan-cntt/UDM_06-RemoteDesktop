"""
tests/test_auth.py
-------------------------------------------------------------------
Unit test tự động cho server/auth.py (TV3 - Sprint 2, Tuần 1).

Chạy:
    cd Code
    python -m pytest tests/test_auth.py -v
"""

import sys
import os
import time
import logging
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import auth  # noqa: E402


class TestInitAndGenerate(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_id_du_6_chu_so(self):
        host_id, host_pass = auth.init_credentials()
        self.assertEqual(len(host_id), 6)
        self.assertTrue(host_id.isdigit())

    def test_password_du_4_chu_so(self):
        host_id, host_pass = auth.init_credentials()
        self.assertEqual(len(host_pass), 4)
        self.assertTrue(host_pass.isdigit())

    def test_fixed_id_duoc_giu_nguyen(self):
        host_id, _ = auth.init_credentials(fixed_id="999888")
        self.assertEqual(host_id, "999888")

    def test_get_current_credentials_tu_khoi_tao_neu_chua_co(self):
        auth._current_id = None
        auth._current_password = None
        host_id, host_pass = auth.get_current_credentials()
        self.assertIsNotNone(host_id)
        self.assertIsNotNone(host_pass)


class TestVerifyCredentials(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        auth.init_credentials(fixed_id="123456")
        auth._current_password = "5678"

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_id_va_password_dung(self):
        self.assertTrue(auth.verify_credentials("123456", "5678"))

    def test_password_sai(self):
        self.assertFalse(auth.verify_credentials("123456", "0000"))

    def test_id_sai(self):
        self.assertFalse(auth.verify_credentials("111111", "5678"))

    def test_id_sai_dinh_dang_khong_phai_so(self):
        self.assertFalse(auth.verify_credentials("abcdef", "5678"))

    def test_id_sai_dinh_dang_thieu_so(self):
        self.assertFalse(auth.verify_credentials("12345", "5678"))

    def test_password_sai_dinh_dang_thua_so(self):
        self.assertFalse(auth.verify_credentials("123456", "56789"))

    def test_input_none_khong_crash(self):
        try:
            result = auth.verify_credentials(None, None)
        except Exception as e:
            self.fail(f"verify_credentials bị crash với input None: {e}")
        self.assertFalse(result)

    def test_input_co_khoang_trang_van_hop_le(self):
        self.assertTrue(auth.verify_credentials("  123456  ", " 5678 "))

    def test_chua_init_credentials_tra_ve_false(self):
        auth._current_id = None
        auth._current_password = None
        self.assertFalse(auth.verify_credentials("123456", "5678"))


class TestRegeneratePassword(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        auth.init_credentials(fixed_id="123456")
        auth._current_password = "1111"

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_doi_mat_khau_thanh_cong(self):
        old_pass = auth._current_password
        new_pass = auth.regenerate_password()
        self.assertNotEqual(old_pass, new_pass)  # xác suất trùng cực nhỏ (1/10000)

    def test_mat_khau_cu_khong_con_hop_le_sau_khi_doi(self):
        auth.regenerate_password()
        self.assertFalse(auth.verify_credentials("123456", "1111"))

    def test_id_khong_doi_khi_doi_mat_khau(self):
        old_id = auth._current_id
        auth.regenerate_password()
        self.assertEqual(auth._current_id, old_id)


class TestBruteForceLockout(unittest.TestCase):
    """Test tính năng bổ sung: khóa tạm thời IP sau nhiều lần nhập sai."""

    def setUp(self):
        logging.disable(logging.CRITICAL)
        auth.init_credentials(fixed_id="123456")
        auth._current_password = "5678"
        auth._failed_attempts.clear()

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_khoa_sau_5_lan_sai_lien_tiep(self):
        ip = "10.0.0.9"
        for _ in range(auth.MAX_FAILED_ATTEMPTS):
            auth.verify_credentials("123456", "0000", client_ip=ip)
        # Lần thứ 6 dù nhập ĐÚNG cũng phải bị từ chối vì đang bị khóa
        self.assertFalse(auth.verify_credentials("123456", "5678", client_ip=ip))

    def test_khong_khoa_neu_khong_truyen_ip(self):
        for _ in range(10):
            auth.verify_credentials("123456", "0000")
        # Không truyền client_ip -> không bị khóa, nhập đúng vẫn qua được
        self.assertTrue(auth.verify_credentials("123456", "5678"))

    def test_nhap_dung_reset_so_lan_sai(self):
        ip = "10.0.0.5"
        auth.verify_credentials("123456", "0000", client_ip=ip)
        auth.verify_credentials("123456", "0000", client_ip=ip)
        auth.verify_credentials("123456", "5678", client_ip=ip)  # đúng -> reset
        self.assertNotIn(ip, auth._failed_attempts)

    def test_mo_khoa_sau_khi_het_thoi_gian_lockout(self):
        ip = "10.0.0.7"
        for _ in range(auth.MAX_FAILED_ATTEMPTS):
            auth.verify_credentials("123456", "0000", client_ip=ip)
        self.assertFalse(auth.verify_credentials("123456", "5678", client_ip=ip))

        # Giả lập đã hết thời gian khóa (chỉnh lại timestamp thay vì sleep thật 30s)
        count, _ = auth._failed_attempts[ip]
        auth._failed_attempts[ip] = (count, time.time() - auth.LOCKOUT_SECONDS - 1)

        self.assertTrue(auth.verify_credentials("123456", "5678", client_ip=ip))


if __name__ == "__main__":
    unittest.main()
