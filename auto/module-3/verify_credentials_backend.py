import os
import sys
import json
import time
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from main import (
    app,
    load_proxy_config,
    save_proxy_config,
    load_logo_updater_config,
    save_logo_updater_config,
    get_logo_updater_credentials,
    clean_shopify_domain,
    LOGO_UPDATER_CONFIG_FILE,
    SHOPIFY_SHOP,
    SHOPIFY_ADMIN_TOKEN,
)

client = TestClient(app)

def run_tests():
    print("=" * 60)
    print("BẮT ĐẦU KIỂM THỬ BACKEND CREDENTIALS & PROXY COUPLING")
    print("=" * 60)

    # Backup original configs if existing
    orig_logo_cfg = load_logo_updater_config()
    orig_proxy_cfg = load_proxy_config()

    try:
        # TEST 1: Proxy TẮT -> BẮT BUỘC dùng Loại 1 (Mặc định Server)
        print("\n--- TEST 1: Proxy TẮT -> Bắt buộc dùng Loại 1 ---")
        proxy_cfg = load_proxy_config()
        proxy_cfg["enabled"] = False
        save_proxy_config(proxy_cfg)

        creds = get_logo_updater_credentials()
        assert creds["type"] == 1, f"Expected type 1, got {creds['type']}"
        assert creds["is_custom"] is False
        assert creds["shop"] == SHOPIFY_SHOP
        assert creds["token"] == SHOPIFY_ADMIN_TOKEN
        print("✓ get_logo_updater_credentials() khi Proxy TẮT: Loại 1 (Mặc định Server)")

        res = client.get("/api/logo-updater/store-info")
        assert res.status_code == 200
        info = res.json()
        assert info["credentials_type"] == 1
        assert info["is_custom"] is False
        assert info["proxy_enabled"] is False
        assert "Trực tiếp" in info["status_label"]
        print("✓ GET /api/logo-updater/store-info khi Proxy TẮT:", info["status_label"])

        # TEST 2: Proxy BẬT nhưng chưa cấu hình Loại 2 -> Fallback về Loại 1
        print("\n--- TEST 2: Proxy BẬT nhưng chưa cấu hình Loại 2 -> Fallback Loại 1 ---")
        # Reset logo updater config
        reset_res = client.post("/api/settings/logo-updater/reset")
        assert reset_res.status_code == 200

        proxy_cfg["enabled"] = True
        save_proxy_config(proxy_cfg)

        creds = get_logo_updater_credentials()
        assert creds["type"] == 1, f"Expected fallback type 1, got {creds['type']}"
        assert creds["is_custom"] is False
        assert creds["shop"] == SHOPIFY_SHOP
        print("✓ Fallback khi Proxy BẬT & Loại 2 rỗng: Thành công về Loại 1")

        res = client.get("/api/logo-updater/store-info")
        info = res.json()
        assert info["credentials_type"] == 1
        assert info["is_custom"] is False
        assert info["proxy_enabled"] is True
        assert "Proxy US" in info["status_label"]
        print("✓ GET /api/logo-updater/store-info khi Proxy BẬT & Fallback:", info["status_label"])

        # TEST 3: Kiểm tra API /api/settings/logo-updater GET & MASK
        print("\n--- TEST 3: GET /api/settings/logo-updater ---")
        res = client.get("/api/settings/logo-updater")
        assert res.status_code == 200
        settings_data = res.json()
        assert settings_data["success"] is True
        assert "config" in settings_data
        print("✓ GET /api/settings/logo-updater thành công")

        # TEST 4: POST /api/settings/logo-updater với Token không hợp lệ -> Bị từ chối
        print("\n--- TEST 4: POST /api/settings/logo-updater với Token rác -> Báo lỗi 400 ---")
        bad_save = client.post("/api/settings/logo-updater", json={
            "shop_domain": "wrydeco",
            "access_token": "shpat_invalid_fake_token_12345"
        })
        assert bad_save.status_code in (400, 500)
        assert bad_save.json()["success"] is False
        print("✓ Token rác bị chặn chuẩn xác:", bad_save.json()["message"])

        # TEST 5: POST /api/settings/logo-updater với Token hợp lệ (sử dụng SHOPIFY_ADMIN_TOKEN làm custom app)
        print("\n--- TEST 5: POST /api/settings/logo-updater với Token hợp lệ ---")
        good_save = client.post("/api/settings/logo-updater", json={
            "shop_domain": "wrydeco.myshopify.com",
            "client_id": "test_client_id_123",
            "client_secret": "shpss_test_secret_456",
            "access_token": SHOPIFY_ADMIN_TOKEN
        })
        assert good_save.status_code == 200, f"Failed: {good_save.text}"
        data_good = good_save.json()
        assert data_good["success"] is True
        print("✓ Lưu cấu hình Loại 2 thành công:", data_good["message"])

        # TEST 6: Proxy BẬT + Đã có Loại 2 -> Kích hoạt Loại 2
        print("\n--- TEST 6: Proxy BẬT + Có Loại 2 -> Sử dụng Loại 2 ---")
        proxy_cfg["enabled"] = True
        save_proxy_config(proxy_cfg)

        creds = get_logo_updater_credentials()
        assert creds["type"] == 2, f"Expected type 2, got {creds['type']}"
        assert creds["is_custom"] is True
        assert creds["token"] == SHOPIFY_ADMIN_TOKEN
        assert creds["client_id"] == "test_client_id_123"
        print("✓ get_logo_updater_credentials() kích hoạt Loại 2 thành công!")

        res = client.get("/api/logo-updater/store-info")
        info = res.json()
        assert info["credentials_type"] == 2
        assert info["is_custom"] is True
        assert info["proxy_enabled"] is True
        assert "Cấu hình riêng" in info["status_label"]
        print("✓ GET /api/logo-updater/store-info khi Loại 2 kích hoạt:", info["status_label"])

        # TEST 7: Chuyển Proxy sang TẮT trong khi Loại 2 vẫn được lưu -> BẮT BUỘC fallback về Loại 1
        print("\n--- TEST 7: Chuyển Proxy sang TẮT -> BẮT BUỘC fallback về Loại 1 ---")
        proxy_cfg["enabled"] = False
        save_proxy_config(proxy_cfg)

        creds = get_logo_updater_credentials()
        assert creds["type"] == 1, f"Expected forced type 1 when proxy off, got {creds['type']}"
        assert creds["is_custom"] is False
        assert creds["client_id"] == os.getenv("SHOPIFY_CLIENT_ID", "")

        res = client.get("/api/logo-updater/store-info")
        info = res.json()
        assert info["credentials_type"] == 1
        assert "Trực tiếp" in info["status_label"]
        print("✓ Chốt chặn Proxy TẮT cưỡng chế fallback Loại 1 thành công 100%!")

        # TEST 8: Xác nhận endpoint POST /api/settings/logo-updater/test đã được gỡ bỏ hoàn toàn (404)
        print("\n--- TEST 8: Xác nhận /api/settings/logo-updater/test đã bị gỡ bỏ ---")
        test_conn = client.post("/api/settings/logo-updater/test", json={
            "shop_domain": "wrydeco",
            "access_token": SHOPIFY_ADMIN_TOKEN
        })
        assert test_conn.status_code == 404, f"Expected 404 Not Found, got {test_conn.status_code}"
        print("✓ Endpoint /api/settings/logo-updater/test đã được gỡ bỏ chính xác (HTTP 404)!")

        # TEST 9: Reset cấu hình Loại 2
        print("\n--- TEST 9: POST /api/settings/logo-updater/reset ---")
        reset_res = client.post("/api/settings/logo-updater/reset")
        assert reset_res.status_code == 200
        assert reset_res.json()["success"] is True
        cfg_after = load_logo_updater_config()
        assert cfg_after["is_custom"] is False
        assert cfg_after["access_token"] == ""
        print("✓ Reset cấu hình Loại 2 về mặc định thành công!")

        # TEST 10: Kiểm thử hàm clean_shopify_domain với mọi dạng URL
        print("\n--- TEST 10: Kiểm thử hàm clean_shopify_domain với URL phức tạp ---")
        test_domain_cases = [
            ("wrydeco", "wrydeco"),
            ("wrydeco.myshopify.com", "wrydeco"),
            ("https://wrydeco.myshopify.com", "wrydeco"),
            ("https://wrydeco.myshopify.com/", "wrydeco"),
            ("https://admin.shopify.com/store/wrydeco", "wrydeco"),
            ("https://admin.shopify.com/store/wrydeco/products", "wrydeco"),
            ("admin.shopify.com/store/wrydeco", "wrydeco"),
            ("https://wrydeco.myshopify.com:443/admin", "wrydeco"),
            ("WRYDECO.MYSHOPIFY.COM", "wrydeco"),
        ]
        for raw_in, exp_out in test_domain_cases:
            res_out = clean_shopify_domain(raw_in)
            assert res_out == exp_out, f"clean_shopify_domain('{raw_in}') = '{res_out}', expected '{exp_out}'"
        print("✓ clean_shopify_domain chuẩn hóa thành công 100% mọi biến thể URL!")

        # TEST 11: Chốt chặn an toàn trong Settings: Proxy BẬT nhưng proxy chết -> Trả về 503, TUYỆT ĐỐI không lộ IP
        print("\n--- TEST 11: Proxy Safety chốt chặn trong Settings endpoint khi Proxy chết ---")
        orig_proxy_url = proxy_cfg.get("proxy_url", "")
        proxy_cfg["enabled"] = True
        proxy_cfg["proxy_url"] = "http://127.0.0.1:9999"
        proxy_cfg["is_stable"] = False
        proxy_cfg["last_checked_at"] = (datetime.now() - timedelta(seconds=120)).isoformat()
        proxy_cfg["last_error"] = "Test Proxy Dead"
        save_proxy_config(proxy_cfg)

        res_test_blocked = client.post("/api/settings/logo-updater", json={
            "shop_domain": "wrydeco",
            "access_token": SHOPIFY_ADMIN_TOKEN
        })
        assert res_test_blocked.status_code == 503, f"Expected 503 blocked, got {res_test_blocked.status_code}"
        assert "chặn request" in res_test_blocked.json()["message"].lower() or "mất kết nối" in res_test_blocked.json()["message"].lower()
        print("✓ Chốt chặn Settings API chặn request thành công (HTTP 503), bảo vệ 100% chống rò rỉ IP VPS!")

        # Khôi phục proxy stable cho các bước kế tiếp
        proxy_cfg["proxy_url"] = orig_proxy_url
        proxy_cfg["is_stable"] = True
        proxy_cfg["last_error"] = None
        proxy_cfg["enabled"] = False
        save_proxy_config(proxy_cfg)

        print("\n" + "=" * 60)
        print("TẤT CẢ 11 BÀI KIỂM THỬ BACKEND ĐỀU ĐẠT 100%!")
        print("=" * 60)

    finally:
        # Restore original configs
        save_logo_updater_config(orig_logo_cfg)
        save_proxy_config(orig_proxy_cfg)

if __name__ == "__main__":
    run_tests()
