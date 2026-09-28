import os
import sys
import time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding='utf-8')
os.makedirs("test_results", exist_ok=True)

BASE_URL = "https://wrydeco.shopify.vnote.site/update-product-logo"

def run_tests():
    print("=== BẮT ĐẦU KIỂM THỬ PLAYWRIGHT SPEED DIAL TRÁI & POPOVER AN TOÀN ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 950})
        page = context.new_page()

        # 1. Mở trang
        print(f"\n[Bước 1] Mở trang {BASE_URL}...")
        page.goto(BASE_URL, timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 2. Xác nhận banner inline cũ đã biến mất
        print("\n[Bước 2] Xác nhận banner inline cũ đã bị xóa khỏi main...")
        banner_in_main = page.locator("main .bg-gradient-to-r.from-indigo-900.to-purple-900")
        assert banner_in_main.count() == 0, "Banner inline vẫn còn xuất hiện trong thẻ main!"
        print("  ✓ Đã xác nhận: Banner inline cũ đã được dọn sạch khỏi trang!")

        # 3. Kiểm tra Speed Dial bên trái
        print("\n[Bước 3] Kiểm tra Speed Dial bên trái neo cố định...")
        sd_left = page.locator("#speedDialLeftContainer")
        assert sd_left.is_visible(), "Speed Dial bên trái không hiển thị!"
        box = sd_left.bounding_box()
        print(f"  ✓ Bounding box Speed Dial trái: top={box['y']}px, left={box['x']}px (Chuẩn: top=78px, left=24px)")
        assert abs(box['y'] - 78) < 5, f"Vị trí top không khớp 78px: {box['y']}"
        assert abs(box['x'] - 24) < 5, f"Vị trí left không khớp 24px: {box['x']}"

        page.screenshot(path="test_results/speed_dial_left_01_initial.png")

        # 4. Click mở Speed Dial bên trái
        print("\n[Bước 4] Click mở Speed Dial bên trái...")
        trigger_left = page.locator("#speedDialLeftTrigger")
        trigger_left.click()
        page.wait_for_timeout(400)

        menu_left = page.locator("#speedDialLeftMenu")
        assert menu_left.is_visible(), "Menu con của Speed Dial trái không hiển thị!"
        menu_text = menu_left.inner_text()
        print(f"  ✓ Menu con hiển thị nút action: {repr(menu_text)}")
        assert "Quy trình An toàn" in menu_text
        assert "2 Bước" in menu_text

        page.screenshot(path="test_results/speed_dial_left_02_menu_open.png")

        # 5. Click vào nút action con để mở Popover
        print("\n[Bước 5] Click nút action con -> Mở Popover...")
        action_item = menu_left.locator("div.group.cursor-pointer")
        action_item.click()
        page.wait_for_timeout(400)

        popover_wrapper = page.locator("#safetyPolicyPopoverWrapper")
        popover = page.locator("#safetyPolicyPopover")
        assert popover_wrapper.is_visible(), "Popover wrapper không hiển thị!"
        assert popover.is_visible(), "Popover card không hiển thị!"

        popover_text = popover.inner_text()
        print(f"  ✓ Đã lấy được nội dung Popover (độ dài: {len(popover_text)} ký tự)")
        text_lower = popover_text.lower()
        assert "zero data loss" in text_lower, "Missing Zero Data Loss"
        assert "rollback" in text_lower, "Missing Rollback"
        assert "/backups" in text_lower, "Missing /backups"
        assert "bước 1" in text_lower, "Missing Step 1"
        assert "bước 2" in text_lower, "Missing Step 2"
        print("    - Đã xác thực đầy đủ: Tiêu đề An toàn, Zero Data Loss, Bước 1, Bước 2, Rollback, /backups")

        page.screenshot(path="test_results/speed_dial_left_03_popover_open.png")

        # 6. Click nút Đóng (X) trên Popover
        print("\n[Bước 6] Đóng Popover bằng nút (X)...")
        close_btn = popover.locator("button[title='Đóng']")
        close_btn.click()
        page.wait_for_timeout(400)
        assert not popover_wrapper.is_visible(), "Popover wrapper vẫn hiển thị sau khi đóng!"
        print("  ✓ Popover đóng thành công!")

        # 7. Mở lại Popover và kiểm tra đóng bằng phím Escape
        print("\n[Bước 7] Mở lại Popover và đóng bằng phím Escape...")
        trigger_left.click()
        page.wait_for_timeout(300)
        action_item.click()
        page.wait_for_timeout(300)
        assert popover_wrapper.is_visible()
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        assert not popover_wrapper.is_visible(), "Popover không đóng khi nhấn phím Escape!"
        print("  ✓ Phím Escape đóng Popover thành công!")

        # 8. Mở lại Popover và kiểm tra đóng bằng click ngoài (backdrop)
        print("\n[Bước 8] Mở lại Popover và đóng bằng click ngoài backdrop...")
        trigger_left.click()
        page.wait_for_timeout(300)
        action_item.click()
        page.wait_for_timeout(300)
        assert popover_wrapper.is_visible()
        # Click vào góc phải ngoài popover (backdrop)
        page.mouse.click(1000, 200)
        page.wait_for_timeout(300)
        assert not popover_wrapper.is_visible(), "Popover không đóng khi click backdrop!"
        print("  ✓ Click ngoài backdrop đóng Popover thành công!")

        # 9. Kiểm tra tương tác mở chéo với Speed Dial bên phải
        print("\n[Bước 9] Kiểm tra tương tác mở chéo giữa Speed Dial trái và phải...")
        trigger_left.click()
        page.wait_for_timeout(300)
        assert menu_left.is_visible(), "Speed Dial trái chưa mở!"

        # Click mở Speed Dial phải
        trigger_right = page.locator("#speedDialTrigger")
        trigger_right.click()
        page.wait_for_timeout(300)

        menu_right = page.locator("#speedDialMenu")
        assert menu_right.is_visible(), "Speed Dial phải chưa mở!"
        assert not menu_left.is_visible(), "Speed Dial trái không tự động đóng khi mở Speed Dial phải!"
        print("  ✓ Khi mở Speed Dial phải, Speed Dial trái tự động đóng mượt mà!")

        page.screenshot(path="test_results/speed_dial_left_04_cross_toggle.png")

        browser.close()
        print("\n=== TẤT CẢ CÁC BƯỚC KIỂM THỬ PLAYWRIGHT ĐÃ PASS 100%! ===")

if __name__ == "__main__":
    run_tests()
