import os
import sys
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
os.makedirs("test_results", exist_ok=True)

BASE_URL = "https://wrydeco.shopify.vnote.site/update-product-logo"

def run_backdrop_tests():
    print("=== BẮT ĐẦU KIỂM THỬ PLAYWRIGHT: ĐÓNG POPUP BACKUP LIST KHI CLICK BACKDROP ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 950})
        page = context.new_page()

        # 1. Mở trang
        print(f"\n[Bước 1] Mở trang {BASE_URL}...")
        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 2. Mở popup Backup List qua Speed Dial phải
        print("\n[Bước 2] Mở popup Backup List...")
        page.locator("#speedDialTrigger").click()
        page.wait_for_timeout(300)
        page.locator("#speedDialMenu div.group").click()
        page.wait_for_timeout(500)

        modal = page.locator("#backupListModal")
        assert modal.is_visible(), "Popup Backup List không hiển thị!"
        print("  ✓ Popup Backup List đã mở hiển thị trên màn hình.")
        page.screenshot(path="test_results/backup_backdrop_01_opened.png")

        # 3. Click bên trong modal card -> Modal KHÔNG ĐƯỢC đóng
        print("\n[Bước 3] Click vào ô tìm kiếm bên trong card modal...")
        search_input = page.locator("#backupSearchInput")
        search_input.click()
        page.wait_for_timeout(300)
        assert modal.is_visible(), "Lỗi: Popup bị đóng khi click vào bên trong card modal!"
        print("  ✓ Popup vẫn mở bình thường khi tương tác bên trong hộp thoại.")

        # 4. Click vào vùng backdrop bên ngoài card modal (góc trên bên trái: x=40, y=40)
        print("\n[Bước 4] Click vào vùng backdrop bên ngoài card modal (x=40, y=40)...")
        page.mouse.click(40, 40)
        page.wait_for_timeout(400)
        assert not modal.is_visible(), "Lỗi: Popup không đóng khi click vào vùng backdrop!"
        print("  ✓ Popup Backup List đã đóng thành công khi click backdrop!")
        page.screenshot(path="test_results/backup_backdrop_02_closed.png")

        # 5. Mở lại popup và click vùng backdrop góc phải dưới (x=1360, y=900)
        print("\n[Bước 5] Mở lại popup và click vùng backdrop góc phải dưới (x=1360, y=900)...")
        page.locator("#speedDialTrigger").click()
        page.wait_for_timeout(300)
        page.locator("#speedDialMenu div.group").click()
        page.wait_for_timeout(500)
        assert modal.is_visible(), "Popup không mở lại được!"

        page.mouse.click(1360, 900)
        page.wait_for_timeout(400)
        assert not modal.is_visible(), "Lỗi: Popup không đóng khi click vào vùng backdrop góc phải dưới!"
        print("  ✓ Popup Backup List đã đóng thành công khi click backdrop góc phải dưới!")

        browser.close()
        print("\n=== KIỂM THỬ PLAYWRIGHT CLICK BACKDROP ĐÃ PASS 100%! ===")

if __name__ == "__main__":
    run_backdrop_tests()
