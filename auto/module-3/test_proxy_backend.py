import os
import sys
import json
import threading
import time
from fastapi.testclient import TestClient

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from main import (
    app,
    load_proxy_config,
    save_proxy_config,
    get_shopify_request_proxies,
    PROXY_CONFIG_FILE,
    test_proxy_connectivity,
    ProxySafetyException,
    mark_proxy_unstable,
)

client = TestClient(app)

def test_proxy_status():
    # 1. Test GET /api/proxy/status
    res = client.get("/api/proxy/status")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "enabled" in data
    assert "is_stable" in data
    assert data["proxy_ip"] == "185.124.63.174"
    print("GET /api/proxy/status PASSED:", data)

def test_proxy_check_success():
    # 2. Test POST /api/proxy/check with the real proxy
    res = client.post("/api/proxy/check")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["is_stable"] is True
    assert data["last_status"] == "stable"
    assert data["last_latency_ms"] > 0
    print("POST /api/proxy/check PASSED: latency =", data["last_latency_ms"], "ms")

def test_proxy_toggle():
    # 3. Test toggle ON
    res_on = client.post("/api/proxy/toggle", json={"enabled": True})
    assert res_on.status_code == 200
    data_on = res_on.json()
    assert data_on["enabled"] is True
    assert data_on["is_stable"] is True
    print("POST /api/proxy/toggle ON PASSED")

    # When enabled and stable, get_shopify_request_proxies() should return dict
    proxies = get_shopify_request_proxies()
    assert isinstance(proxies, dict)
    assert "185.124.63.174" in proxies["http"]
    print("get_shopify_request_proxies() when ON PASSED:", proxies)

    # 4. Test toggle OFF
    res_off = client.post("/api/proxy/toggle", json={"enabled": False})
    assert res_off.status_code == 200
    data_off = res_off.json()
    assert data_off["enabled"] is False
    print("POST /api/proxy/toggle OFF PASSED")

    # When disabled, get_shopify_request_proxies() returns None
    assert get_shopify_request_proxies() is None
    print("get_shopify_request_proxies() when OFF PASSED (returned None)")

def test_proxy_safety_gate_blocking():
    # 5. Test safety gate across ALL media endpoints: Simulate unstable/broken proxy while enabled
    cfg = load_proxy_config()
    orig_url = cfg["proxy_url"]
    try:
        # Point to bad proxy port
        cfg["enabled"] = True
        cfg["proxy_url"] = "http://baduser:badpass@185.124.63.174:9999"
        cfg["is_stable"] = False
        cfg["last_checked_at"] = None
        save_proxy_config(cfg)

        # Calling get_shopify_request_proxies should fail and raise ProxySafetyException
        raised = False
        try:
            get_shopify_request_proxies()
        except ProxySafetyException as e:
            raised = True
            assert "CHỐT CHẶN AN TOÀN" in str(e)
            print("Safety gate exception PASSED: [ProxySafetyException]", str(e))
        except Exception as e:
            raised = True
            assert "CHỐT CHẶN AN TOÀN" in str(e)
            print("Safety gate exception PASSED: [Exception]", str(e))
        assert raised, "Expected get_shopify_request_proxies to raise an exception!"

        # Endpoint 1: batch-media should return HTTP 503
        res1 = client.post("/api/products/batch-media", json={"identifiers": ["test-handle"]})
        assert res1.status_code == 503, f"Expected 503 for batch-media, got {res1.status_code}: {res1.text}"
        assert "CHỐT CHẶN AN TOÀN" in res1.json()["error"]
        print("Endpoint 1 batch-media 503 blocking PASSED")

        # Endpoint 2: backup-media should return HTTP 503
        res2 = client.post("/api/products/backup-media", json={
            "product_id": "123",
            "media_id": "456",
            "image_url": "https://cdn.shopify.com/test.jpg"
        })
        assert res2.status_code == 503, f"Expected 503 for backup-media, got {res2.status_code}: {res2.text}"
        assert "CHỐT CHẶN AN TOÀN" in res2.json()["error"]
        print("Endpoint 2 backup-media 503 blocking PASSED")

        # Endpoint 3: apply-media-update should return HTTP 503
        res3 = client.post("/api/products/apply-media-update", json={
            "product_id": "123",
            "old_media_id": "456",
            "image_base64": "testb64"
        })
        assert res3.status_code == 503, f"Expected 503 for apply-media-update, got {res3.status_code}: {res3.text}"
        assert "CHỐT CHẶN AN TOÀN" in res3.json()["error"]
        print("Endpoint 3 apply-media-update 503 blocking PASSED")

        # Endpoint 4: rollback-media should return HTTP 503
        res4 = client.post("/api/products/rollback-media", json={
            "product_id": "123",
            "original_media_id": "456"
        })
        assert res4.status_code == 503, f"Expected 503 for rollback-media, got {res4.status_code}: {res4.text}"
        assert "CHỐT CHẶN AN TOÀN" in res4.json()["error"]
        print("Endpoint 4 rollback-media 503 blocking PASSED")

    finally:
        # Restore configuration
        cfg["enabled"] = False
        cfg["proxy_url"] = orig_url
        cfg["is_stable"] = False
        save_proxy_config(cfg)
        print("Restored default proxy configuration.")

def test_atomic_config_concurrency():
    # 6. Test concurrent read/write to proxy_config.json to verify no file corruption
    errors = []
    stop_event = threading.Event()

    def writer():
        for i in range(50):
            if stop_event.is_set():
                break
            cfg = load_proxy_config()
            cfg["last_latency_ms"] = i * 10
            save_proxy_config(cfg)
            time.sleep(0.005)

    def reader():
        for _ in range(100):
            if stop_event.is_set():
                break
            try:
                cfg = load_proxy_config()
                assert isinstance(cfg, dict)
                assert "enabled" in cfg
            except Exception as e:
                errors.append(e)
            time.sleep(0.003)

    threads = [
        threading.Thread(target=writer),
        threading.Thread(target=reader),
        threading.Thread(target=reader)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Atomic config concurrency test encountered errors: {errors}"
    print("Atomic config concurrency test PASSED with 0 errors!")

def test_mark_proxy_unstable():
    # 7. Test mark_proxy_unstable helper
    mark_proxy_unstable("Simulated live network drop", latency=999)
    cfg = load_proxy_config()
    assert cfg["is_stable"] is False
    assert cfg["last_status"] == "unstable"
    assert "Simulated live network drop" in cfg["last_error"]
    print("mark_proxy_unstable PASSED")

if __name__ == "__main__":
    test_proxy_status()
    test_proxy_check_success()
    test_proxy_toggle()
    test_proxy_safety_gate_blocking()
    test_atomic_config_concurrency()
    test_mark_proxy_unstable()
    print("\nALL BACKEND PROXY TESTS PASSED 100% SUCCESSFULLY!")
