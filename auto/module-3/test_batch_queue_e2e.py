import os
import sys
import time
import requests
import paramiko
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')
os.makedirs("test_results", exist_ok=True)

BASE_URL = "https://wrydeco.shopify.vnote.site"

def test_batch_media_api():
    print("\n[Kiểm thử API 1] Kiểm tra endpoint /api/products/batch-media...")
    payload = {
        "id_type": "handle",
        "identifiers": "rustic-wooden-floating-wall-shelf-organic-bowl-design"
    }
    res = requests.post(f"{BASE_URL}/api/products/batch-media", json=payload, timeout=20)
    assert res.status_code == 200, f"HTTP Error {res.status_code}"
    data = res.json()
    assert data.get("success") is True, f"Response error: {data}"
    prods = data.get("products", [])
    assert len(prods) > 0, "Không tìm thấy sản phẩm nào!"
    prod = prods[0]
    print(f"  -> Tìm thấy sản phẩm: {prod.get('title')} (Handle: {prod.get('handle')})")
    media_list = prod.get("media", [])
    assert len(media_list) > 0, "Sản phẩm không có media!"
    print(f"  -> Sản phẩm có {len(media_list)} media.")
    for idx, m in enumerate(media_list, 1):
        assert "is_logo_applied" in m, f"Media #{idx} thiếu trường 'is_logo_applied'!"
        assert "has_backup" in m, f"Media #{idx} thiếu trường 'has_backup'!"
    print("  -> TẤT CẢ MEDIA ĐỀU CÓ TRƯỜNG 'is_logo_applied' VÀ 'has_backup'. ĐẠT!")


def test_playwright_batch_queue():
    print("\n[Kiểm thử Playwright E2E] Kiểm tra giao diện Hàng đợi (Batch Queue) & Sticky Bottom Bar...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        # 1. Mở trang /update-product-logo
        print("  1. Truy cập trang /update-product-logo...")
        page.goto(f"{BASE_URL}/update-product-logo", timeout=30000, wait_until="networkidle")
        page.wait_for_timeout(1000)

        # 2. Nhập handle và nạp sản phẩm
        print("  2. Nạp sản phẩm bằng handle...")
        page.fill("#identifiersInput", "rustic-wooden-floating-wall-shelf-organic-bowl-design")
        with page.expect_response("**/api/products/batch-media") as resp_info:
            page.click("#btnLoadProducts")
        batch_res = resp_info.value.json()
        assert batch_res.get("success") is True
        page.wait_for_selector("#product-card-10324646690873", timeout=10000)
        print("  -> Section 2 đã nạp danh sách sản phẩm thành công.")

        # 3. Mở Media #1 vào Canvas Editor
        print("  3. Mở Media #1 trong Canvas Editor...")
        thumbs = page.locator("#product-card-10324646690873 img[alt='Thumbnail']")
        thumb_count = thumbs.count()
        assert thumb_count >= 2, f"Cần ít nhất 2 ảnh để kiểm thử batch queue! Hiện có: {thumb_count}"
        
        thumbs.nth(0).click()
        page.wait_for_selector("#sectionSetupLogo:not(.hidden)", timeout=5000)
        page.wait_for_timeout(500)

        # 4. Kiểm tra nút "Chọn để cập nhật" trong Canvas Editor Header
        btn_add = page.locator("#btnAddToQueue")
        assert btn_add.is_visible(), "Không tìm thấy nút 'Chọn để cập nhật' trong Canvas Editor Header!"
        btn_text = page.locator("#btnAddToQueueText").inner_text()
        print(f"  -> Trạng thái nút ban đầu: '{btn_text}'")

        # 5. Bấm "Chọn để cập nhật" cho Media #1
        print("  4. Bấm 'Chọn để cập nhật' cho Media #1...")
        btn_add.click()
        page.wait_for_timeout(500)

        # Xác nhận nút chuyển sang trạng thái đã thêm vào hàng đợi
        btn_text_after = page.locator("#btnAddToQueueText").inner_text()
        assert "Đã thêm vào hàng đợi" in btn_text_after, f"Nút chưa đổi trạng thái: {btn_text_after}"
        print(f"  -> Nút chuyển thành công sang: '{btn_text_after}'")

        # Xác nhận Sticky Bottom Bar xuất hiện với 1 media
        sticky_bar = page.locator("#stickyBottomBar")
        assert sticky_bar.is_visible(), "Sticky Bottom Bar không xuất hiện sau khi thêm vào hàng đợi!"
        sticky_count = page.locator("#stickyQueueCount").inner_text()
        assert "1 media" in sticky_count, f"Số lượng trong sticky bar sai: {sticky_count}"
        print(f"  -> Sticky Bottom Bar hiển thị chính xác: {sticky_count}")

        # Xác nhận badge 'Hàng đợi' xuất hiện trên thumbnail #1
        queue_badge_1 = page.locator("#product-card-10324646690873 .group").nth(0).locator("text=Hàng đợi")
        assert queue_badge_1.is_visible(), "Thumbnail #1 không hiển thị badge 'Hàng đợi'!"
        print("  -> Badge 'Hàng đợi' hiển thị trên thumbnail #1.")

        page.screenshot(path="test_results/10_queue_1_item.png")

        # 6. Chọn Media #2 và thêm tiếp vào hàng đợi
        print("  5. Mở Media #2 và thêm vào hàng đợi...")
        thumbs.nth(1).click()
        page.wait_for_timeout(800)

        # Media #2 chưa có trong hàng đợi nên nút phải là "Chọn để cập nhật"
        btn_text_m2 = page.locator("#btnAddToQueueText").inner_text()
        assert "Chọn để cập nhật" in btn_text_m2, f"Nút Media #2 ban đầu không đúng: {btn_text_m2}"

        btn_add.click()
        page.wait_for_timeout(500)

        sticky_count_2 = page.locator("#stickyQueueCount").inner_text()
        assert "2 media" in sticky_count_2, f"Số lượng trong sticky bar sai: {sticky_count_2}"
        print(f"  -> Sticky Bottom Bar đã cập nhật lên: {sticky_count_2}")

        # Xác nhận nút 1 trong Sticky Bar & Canvas Editor đồng bộ
        sticky_btn1_text = page.locator("#stickyBackupText").inner_text()
        editor_btn1_text = page.locator("#backupPhaseText").inner_text()
        assert "2 media" in sticky_btn1_text, f"Text nút 1 sticky bar sai: {sticky_btn1_text}"
        assert "2 media" in editor_btn1_text, f"Text nút 1 editor sai: {editor_btn1_text}"
        print(f"  -> Nút 1 đồng bộ: '{sticky_btn1_text}'")

        # Kiểm tra logic hiển thị nút 2 dựa trên trạng thái backup:
        btn2 = page.locator("#btnApplyPhase")
        if "Đã sao lưu" in sticky_btn1_text:
            print(f"  -> Cả 2 media đều đã có bản backup hợp lệ trên VPS: Nút 2 hiển thị sẵn sàng ({sticky_btn1_text}).")
            assert btn2.is_visible(), "Nút 2 phải hiển thị khi 100% media đã được sao lưu!"
        else:
            print(f"  -> Có media chưa sao lưu ({sticky_btn1_text}): Nút 2 ẩn an toàn.")
            assert not btn2.is_visible(), "Nút 2 không được hiển thị khi chưa sao lưu!"

        page.screenshot(path="test_results/11_queue_2_items.png")

        # 7. Mở Modal "Xem danh sách" từ Sticky Bottom Bar
        print("  6. Mở Modal 'Xem danh sách'...")
        page.click("button:has-text('Xem danh sách')")
        page.wait_for_selector("#queueModal:not(.hidden)", timeout=5000)
        modal_items = page.locator("#queueModalItems > div")
        assert modal_items.count() == 2, f"Modal phải hiển thị 2 items, nhưng có: {modal_items.count()}"
        print("  -> Modal hiển thị đúng 2 items trong hàng đợi.")
        page.screenshot(path="test_results/12_queue_modal.png")

        # Đóng Modal
        page.click("#queueModal button:has-text('Đóng')")
        page.wait_for_timeout(300)

        # 8. Kiểm tra nút Xóa tất cả
        print("  7. Kiểm tra tính năng 'Xóa tất cả' hàng đợi...")
        page.on("dialog", lambda dialog: dialog.accept())
        page.click("button:has-text('Xóa tất cả')")
        page.wait_for_timeout(500)

        # Sau khi xóa tất cả, sticky bar phải ẩn đi
        assert not sticky_bar.is_visible(), "Sticky Bottom Bar phải ẩn sau khi xóa toàn bộ hàng đợi!"
        print("  -> Sau khi xóa tất cả, Sticky Bottom Bar tự động ẩn đi. ĐẠT!")

        page.screenshot(path="test_results/13_queue_cleared.png")
        browser.close()
        print("\n=== KIỂM THỬ PLAYWRIGHT BATCH QUEUE THÀNH CÔNG 100%! ===")

if __name__ == "__main__":
    test_batch_media_api()
    test_playwright_batch_queue()
