import os
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
os.makedirs("test_results", exist_ok=True)

BASE_URL = "https://wrydeco.shopify.vnote.site/update-product-logo"

def run_tests():
    print("=== BẮT ĐẦU KIỂM THỬ PLAYWRIGHT: LIVE EGRESS VERIFICATION (GEO & ISP) ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 950})
        page = context.new_page()

        # 1. Mở trang
        print(f"\n[Bước 1] Mở trang {BASE_URL}...")
        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 2. Click nút "Kiểm tra Proxy"
        print("\n[Bước 2] Click nút 'Kiểm tra Proxy' để thực hiện Live Egress Verification...")
        btn_check = page.locator("#btnCheckProxy")
        btn_check.click()

        # Chờ kiểm tra hoàn thành (khoảng 2-6 giây vì tunnel qua proxy tới Shopify + GeoIP)
        print("  -> Đang chờ Backend bắn request xuyên tunnel Proxy...")
        page.wait_for_function("document.getElementById('btnCheckProxyText').textContent === 'Kiểm tra Proxy'", timeout=20000)
        page.wait_for_timeout(1000)

        # 3. Kiểm tra Huy hiệu trạng thái Proxy
        print("\n[Bước 3] Kiểm tra Huy hiệu trạng thái Proxy...")
        badge = page.locator("#proxyStatusBadge")
        badge_text = badge.inner_text().strip()
        print(f"  ✓ Huy hiệu hiển thị: {repr(badge_text)}")
        assert "Proxy Ổn định" in badge_text, "Badge không báo Proxy Ổn định!"
        assert "185.124.63.174" in badge_text, "Badge thiếu địa chỉ IP Proxy!"
        assert "Lewes" in badge_text or "Delaware" in badge_text or "US" in badge_text, "Badge thiếu địa điểm!"

        # 4. Kiểm tra Thẻ thông tin Live Egress Geo
        print("\n[Bước 4] Kiểm tra Thẻ thông tin Live Egress Geo...")
        geo_badge = page.locator("#proxyGeoInfoBadge")
        assert geo_badge.is_visible(), "Thẻ thông tin Geo không hiển thị!"

        geo_loc = page.locator("#proxyGeoLocation").inner_text().strip()
        geo_isp = page.locator("#proxyGeoIsp").inner_text().strip()

        print(f"  ✓ Vị trí địa lý: {geo_loc}")
        print(f"  ✓ Nhà mạng (ISP): {geo_isp}")

        assert page.locator("#proxyGeoFlag iconify-icon").count() > 0 or len(page.locator("#proxyGeoFlag").inner_text()) > 0, "Thiếu cờ quốc gia!"
        assert "United States" in geo_loc or "US" in geo_loc or "Delaware" in geo_loc or "Lewes" in geo_loc, f"Vị trí không khớp: {geo_loc}"
        assert "Verizon" in geo_isp, f"ISP không đúng Verizon: {geo_isp}"

        page.screenshot(path="test_results/proxy_live_egress_verified.png")
        print("\n  ✓ Đã lưu screenshot: test_results/proxy_live_egress_verified.png")

        # 5. Kiểm tra bật công tắc Switch
        print("\n[Bước 5] Bật công tắc Switch Proxy Gateway...")
        switch = page.locator("#proxyToggleSwitch")
        if not switch.is_checked():
            page.locator("label[title='Bật/Tắt định tuyến Proxy']").click()
            page.wait_for_timeout(2500)

        assert switch.is_checked(), "Công tắc Switch chưa được bật!"
        assert geo_badge.is_visible(), "Thẻ thông tin Geo bị ẩn sau khi bật!"
        print("  ✓ Proxy đã BẬT với đầy đủ định danh Live Egress Geo!")

        page.screenshot(path="test_results/proxy_live_egress_switch_on.png")

        browser.close()
        print("\n=== TẤT CẢ KIỂM THỬ LIVE EGRESS VERIFICATION ĐÃ PASS 100%! ===")

if __name__ == "__main__":
    run_tests()
