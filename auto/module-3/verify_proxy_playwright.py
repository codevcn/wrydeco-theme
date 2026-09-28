import os
import sys
import time
import requests
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
os.makedirs("test_results", exist_ok=True)

BASE_URL = "https://wrydeco.shopify.vnote.site/update-product-logo"

def run_proxy_tests():
    print("=== BẮT ĐẦU KIỂM THỬ PLAYWRIGHT PROXY GATEWAY TRÊN LIVE SITE ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 950})
        page = context.new_page()

        # Đảm bảo reset trạng thái Proxy về Tắt trước khi bắt đầu test
        requests.post("https://wrydeco.shopify.vnote.site/api/proxy/toggle", json={"enabled": False})

        # 1. Truy cập trang /update-product-logo
        print("\n[Bước 1] Truy cập https://wrydeco.shopify.vnote.site/update-product-logo...")
        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 2. Kiểm tra Section Proxy Gateway xuất hiện đúng vị trí
        print("\n[Bước 2] Kiểm tra hiển thị Section Proxy Gateway...")
        proxy_section = page.locator("#proxyGatewaySection")
        assert proxy_section.is_visible(), "Section Proxy Gateway không hiển thị trên giao diện!"
        
        title_text = page.locator("#proxyGatewaySection h3").inner_text()
        print(f"  -> Tiêu đề Section: {title_text}")
        assert "Bảo vệ Kết nối Proxy" in title_text

        # 3. Kiểm tra trạng thái ban đầu (Proxy TẮT)
        badge = page.locator("#proxyStatusBadge")
        badge_text = badge.inner_text().strip()
        print(f"  -> Huy hiệu trạng thái ban đầu: {badge_text}")
        assert "Proxy đang Tắt" in badge_text

        switch = page.locator("#proxyToggleSwitch")
        assert not switch.is_checked(), "Công tắc switch ban đầu phải ở trạng thái Tắt!"
        page.screenshot(path="test_results/proxy_01_initial_disabled.png")
        print("  -> Chụp ảnh màn hình: test_results/proxy_01_initial_disabled.png")

        # 4. Bật công tắc Proxy (Toggle Switch ON)
        print("\n[Bước 3] Bật công tắc Switch Proxy...")
        switch.click(force=True)
        
        # Đợi gọi API /api/proxy/toggle và tự động test kết nối
        page.wait_for_timeout(3500)
        
        # Kiểm tra badge cập nhật thành Xanh (Ổn định)
        badge_text_on = badge.inner_text().strip()
        print(f"  -> Huy hiệu sau khi BẬT: {badge_text_on}")
        assert "Proxy Ổn định" in badge_text_on or "185.124.63.174" in badge_text_on, f"Badge không chuyển sang Ổn định! Nội dung: {badge_text_on}"
        assert switch.is_checked(), "Công tắc switch phải ở trạng thái Bật!"
        page.screenshot(path="test_results/proxy_02_enabled_stable.png")
        print("  -> Chụp ảnh màn hình: test_results/proxy_02_enabled_stable.png")

        # 5. Bấm nút "Kiểm tra Proxy" (Health Check)
        print("\n[Bước 4] Bấm nút 'Kiểm tra Proxy'...")
        btn_check = page.locator("#btnCheckProxy")
        btn_check.click()
        
        # Chờ nút hoàn tất và kiểm tra toast
        page.wait_for_timeout(3500)
        badge_text_checked = badge.inner_text().strip()
        print(f"  -> Huy hiệu sau khi Kiểm tra Proxy: {badge_text_checked}")
        assert "Proxy Ổn định" in badge_text_checked

        # Kiểm tra toast phản hồi
        toast = page.locator("#toastContainer")
        toast_text = toast.inner_text().strip()
        print(f"  -> Toast thông báo: {toast_text}")
        assert "Proxy phản hồi hoàn hảo" in toast_text or "Proxy đã BẬT" in toast_text
        page.screenshot(path="test_results/proxy_03_check_success.png")
        print("  -> Chụp ảnh màn hình: test_results/proxy_03_check_success.png")

        # 6. Kiểm tra tải sản phẩm khi Proxy BẬT & Ổn định
        print("\n[Bước 5] Tải sản phẩm qua Proxy...")
        page.locator("#identifiersInput").fill("rustic-wooden-floating-wall-shelf-organic-bowl-design")
        btn_load = page.locator("#btnLoadProducts")
        with page.expect_response("**/api/products/batch-media", timeout=20000) as response_info:
            btn_load.click()
        resp = response_info.value
        print(f"  -> batch-media HTTP status: {resp.status}")
        data = resp.json()
        print(f"  -> batch-media trả về: success={data.get('success')}, số sản phẩm={len(data.get('products', []))}")
        assert data.get('success') is True
        assert len(data.get('products', [])) > 0
        page.wait_for_timeout(1000)

        # Xác nhận sản phẩm đã được load trong #productsContainer
        products_container = page.locator("#productsContainer")
        assert products_container.is_visible()
        badge_count = page.locator("#productTotalBadge").inner_text()
        print(f"  -> Tổng sản phẩm hiển thị: {badge_count}")
        page.screenshot(path="test_results/proxy_04_product_loaded_via_proxy.png")
        print("  -> Chụp ảnh màn hình: test_results/proxy_04_product_loaded_via_proxy.png")

        # 7. Kiểm thử Chốt Chặn An Toàn (Safety Gate) khi Proxy BẬT nhưng Không ổn định
        print("\n[Bước 6] Kiểm thử Chốt Chặn An Toàn (Safety Gate)...")
        # Giả lập trạng thái proxy không ổn định trên frontend
        page.evaluate("""() => {
            proxyState.enabled = true;
            proxyState.isStable = false;
            proxyState.lastError = 'Mất kết nối máy chủ Proxy (Giả lập kiểm thử)';
            updateProxyUI({
                enabled: true,
                is_stable: false,
                proxy_ip: '185.124.63.174',
                last_error: 'Mất kết nối máy chủ Proxy (Giả lập kiểm thử)',
                last_status: 'unstable',
                last_latency_ms: 0
            });
        }""")
        page.wait_for_timeout(500)

        # Kiểm tra Hộp cảnh báo đỏ hiển thị
        unstable_alert = page.locator("#proxyUnstableAlert")
        assert unstable_alert.is_visible(), "Hộp cảnh báo đỏ không xuất hiện khi Proxy không ổn định!"
        print("  -> Hộp cảnh báo đỏ đã xuất hiện chính xác.")

        # Kiểm tra hiệu ứng thị giác: các nút hành động phải có class opacity-60
        btn_backup = page.locator("#stickyBtnBackup")
        btn_apply = page.locator("#stickyBtnApply")
        btn_rollback = page.locator("#btnRollback")

        load_classes = btn_load.get_attribute("class") or ""
        backup_classes = btn_backup.get_attribute("class") or ""
        apply_classes = btn_apply.get_attribute("class") or ""
        rollback_classes = btn_rollback.get_attribute("class") or ""

        assert "opacity-60" in load_classes, "Nút Tải dữ liệu chưa nhận class opacity-60 khi Proxy không ổn định!"
        assert "opacity-60" in backup_classes, "Nút Sao lưu chưa nhận class opacity-60 khi Proxy không ổn định!"
        assert "opacity-60" in apply_classes, "Nút Cập nhật chưa nhận class opacity-60 khi Proxy không ổn định!"
        assert "opacity-60" in rollback_classes, "Nút Rollback chưa nhận class opacity-60 khi Proxy không ổn định!"
        print("  -> Tất cả các nút hành động (Tải/Sao lưu/Cập nhật/Rollback) đã được làm mờ (opacity-60) chuẩn xác.")

        # 1. Thử bấm nút 'OK (Tải dữ liệu)' -> Phải bị chặn đứng và hiển thị Toast lỗi đỏ
        print("  -> Thử bấm nút 'OK (Tải dữ liệu)' khi Proxy không ổn định...")
        btn_load.click()
        page.wait_for_timeout(500)
        toast_block = page.locator("#toastContainer").inner_text()
        assert "CHỐT CHẶN AN TOÀN" in toast_block, "Chốt chặn an toàn Frontend không chặn đứng nút Tải sản phẩm!"
        print("  -> Chốt chặn an toàn nút Tải sản phẩm: ĐÃ CHẶN 100% THÀNH CÔNG!")

        # 2. Thử bấm nút '1. Sao lưu tất cả' -> Phải bị chặn đứng
        print("  -> Thử bấm nút '1. Sao lưu tất cả' khi Proxy không ổn định...")
        btn_backup.dispatch_event('click')
        page.wait_for_timeout(500)
        toast_block = page.locator("#toastContainer").inner_text()
        assert "CHỐT CHẶN AN TOÀN" in toast_block, "Chốt chặn an toàn Frontend không chặn đứng nút Sao lưu!"
        print("  -> Chốt chặn an toàn nút Sao lưu: ĐÃ CHẶN 100% THÀNH CÔNG!")

        # 3. Thử bấm nút '2. Tiến hành cập nhật tất cả' -> Phải bị chặn đứng
        print("  -> Thử bấm nút '2. Tiến hành cập nhật tất cả' khi Proxy không ổn định...")
        btn_apply.dispatch_event('click')
        page.wait_for_timeout(500)
        toast_block = page.locator("#toastContainer").inner_text()
        assert "CHỐT CHẶN AN TOÀN" in toast_block, "Chốt chặn an toàn Frontend không chặn đứng nút Cập nhật!"
        print("  -> Chốt chặn an toàn nút Cập nhật: ĐÃ CHẶN 100% THÀNH CÔNG!")

        # 4. Thử bấm nút 'Khôi phục ảnh gốc (Rollback)' -> Phải bị chặn đứng
        print("  -> Thử bấm nút 'Khôi phục ảnh gốc (Rollback)' khi Proxy không ổn định...")
        btn_rollback.dispatch_event('click')
        page.wait_for_timeout(500)
        toast_block = page.locator("#toastContainer").inner_text()
        assert "CHỐT CHẶN AN TOÀN" in toast_block, "Chốt chặn an toàn Frontend không chặn đứng nút Rollback!"
        print("  -> Chốt chặn an toàn nút Rollback: ĐÃ CHẶN 100% THÀNH CÔNG!")

        page.screenshot(path="test_results/proxy_05_safety_gate_blocked.png")
        print("  -> Chụp ảnh màn hình: test_results/proxy_05_safety_gate_blocked.png")

        # 8. Khôi phục trạng thái: Tắt Proxy Switch
        print("\n[Bước 7] Tắt Proxy Switch và khôi phục trạng thái chuẩn...")
        switch.click(force=True)
        page.wait_for_timeout(1000)
        badge_final = badge.inner_text().strip()
        print(f"  -> Huy hiệu sau khi Tắt: {badge_final}")
        assert "Proxy đang Tắt" in badge_final
        page.screenshot(path="test_results/proxy_06_disabled_restored.png")
        print("  -> Chụp ảnh màn hình: test_results/proxy_06_disabled_restored.png")

        browser.close()
        print("\n=== TẤT CẢ KỊCH BẢN KIỂM THỬ PLAYWRIGHT ĐÃ VƯỢT QUA 100% THÀNH CÔNG ===")

if __name__ == "__main__":
    run_proxy_tests()
