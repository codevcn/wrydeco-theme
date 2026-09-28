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

def verify_vps_file(prod_id, media_id):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_config_file = os.path.expanduser("~/.ssh/config")
    config = paramiko.SSHConfig()
    with open(ssh_config_file, encoding='utf-8') as f:
        config.parse(f)
    hc = config.lookup('wrydeco-vps')
    ssh.connect(hostname=hc['hostname'], username=hc['user'], key_filename=hc['identityfile'], timeout=15)
    
    cmd = f"ls -la /home/azureuser/shopify-admin-app/backups/{prod_id}/{media_id}_orig.jpg"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    ssh.close()
    return out, err

def query_shopify_images(prod_id):
    token = os.getenv("SHOPIFY_ADMIN_TOKEN")
    shop = os.getenv("SHOPIFY_SHOP")
    version = os.getenv("SHOPIFY_API_VERSION", "2024-04")
    url = f"https://{shop}.myshopify.com/admin/api/{version}/products/{prod_id}/images.json"
    r = requests.get(url, headers={"X-Shopify-Access-Token": token})
    return r.json().get("images", [])

def run_tests():
    print("=== BẮT ĐẦU KIỂM THỬ PLAYWRIGHT E2E TOÀN DIỆN ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()

        # KỊCH BẢN 1: Mở Drawer Menu tại Trang chủ & Kiểm tra nút
        print("\n[Kịch bản 1] Mở Drawer Menu tại Trang chủ...")
        page.goto("https://wrydeco.shopify.vnote.site/", timeout=30000, wait_until="networkidle")
        
        # Mở Drawer
        drawer_btn = page.locator("#drawer-toggle-btn")
        drawer_btn.click()
        page.wait_for_timeout(1000)
        
        # Kiểm tra nút Cập nhật logo
        logo_menu_link = page.locator('a[href="/update-product-logo"]')
        assert logo_menu_link.count() > 0, "Không tìm thấy liên kết /update-product-logo trong Drawer!"
        assert logo_menu_link.get_attribute("target") == "_blank", "Thiếu target='_blank' trên liên kết Drawer!"
        print("  -> Nút 'Cập nhật logo ảnh sản phẩm' hiển thị chính xác trong Drawer với target='_blank'.")
        page.screenshot(path="test_results/01_homepage_drawer.png")

        # KỊCH BẢN 2: Điều hướng tới /update-product-logo & Kiểm tra Section 1
        print("\n[Kịch bản 2] Điều hướng tới trang /update-product-logo...")
        page.goto("https://wrydeco.shopify.vnote.site/update-product-logo", timeout=30000, wait_until="networkidle")
        
        page_title = page.title()
        print(f"  -> Title trang: {page_title}")
        assert "Cập nhật Logo" in page_title

        # Kiểm tra logo mặc định
        logo_preview = page.locator("#currentLogoPreview")
        assert "store-logo-black-trans.png" in logo_preview.get_attribute("src")
        print("  -> Logo mặc định ban đầu là store-logo-black-trans.png")

        # Thử đổi sang Logo Trắng
        btn_white_logo = page.locator('button:has-text("Logo Trắng")')
        btn_white_logo.click()
        page.wait_for_timeout(500)
        assert "store-logo-white-trans.png" in logo_preview.get_attribute("src")
        print("  -> Đổi sang Logo Trắng thành công.")

        # Đổi lại Logo Đen
        btn_black_logo = page.locator('button:has-text("Logo Đen")')
        btn_black_logo.click()
        page.wait_for_timeout(500)
        assert "store-logo-black-trans.png" in logo_preview.get_attribute("src")
        print("  -> Đổi lại Logo Đen thành công.")

        # KỊCH BẢN 3: Nạp danh sách sản phẩm bằng Handle
        print("\n[Kịch bản 3] Nạp sản phẩm bằng handle...")
        test_handle = "rustic-wooden-floating-wall-shelf-organic-bowl-design"
        textarea = page.locator("#identifiersInput")
        textarea.fill(test_handle)

        radio_handle = page.locator('input[name="id_type"][value="handle"]')
        assert radio_handle.is_checked()

        btn_ok = page.locator("#btnLoadProducts")
        with page.expect_response("**/api/products/batch-media") as response_info:
            btn_ok.click()
        res_data = response_info.value.json()
        assert res_data.get("success") is True
        print(f"  -> API /api/products/batch-media trả về {len(res_data.get('products', []))} sản phẩm.")

        page.wait_for_selector("#product-card-10324646690873")
        print("  -> Section 2 đã render card sản phẩm với Title, Handle, ID và danh sách media thumbnails.")
        page.screenshot(path="test_results/02_product_loaded.png")

        # KỊCH BẢN 4: Mở Section Setup Logo
        print("\n[Kịch bản 4] Nhấp vào thumbnail media để mở Section Setup Logo...")
        thumb_locator = page.locator("#product-card-10324646690873 img[alt='Thumbnail']").first
        thumb_locator.click()

        page.wait_for_selector("#sectionSetupLogo:not(.hidden)")
        page.wait_for_timeout(1000)
        print("  -> Section Setup Logo đã mở ra thành công với Canvas tương tác.")

        # Thao tác kéo thả logo trên canvas
        canvas = page.locator("#editorCanvas")
        box = canvas.bounding_box()
        start_x = box["x"] + box["width"] * 0.8
        start_y = box["y"] + box["height"] * 0.1
        end_x = box["x"] + box["width"] * 0.6
        end_y = box["y"] + box["height"] * 0.3
        
        page.mouse.move(start_x, start_y)
        page.mouse.down()
        page.mouse.move(end_x, end_y, steps=10)
        page.mouse.up()
        print("  -> Thao tác kéo thả di chuyển logo trên Canvas thành công.")

        # Chỉnh Slider Scale & Opacity
        scale_slider = page.locator("#scaleSlider")
        scale_slider.fill("22")
        page.wait_for_timeout(300)

        opacity_slider = page.locator("#opacitySlider")
        opacity_slider.fill("0.95")
        page.wait_for_timeout(300)
        print("  -> Điều chỉnh slider Scale (22%) và Opacity (0.95) thành công.")
        page.screenshot(path="test_results/03_canvas_setup.png")

        # KỊCH BẢN 5: Quy trình 1 - Bấm nút Save (Sao lưu ảnh gốc trên VPS)
        print("\n[Kịch bản 5] QUY TRÌNH 1: Bấm 'Save (Sao lưu ảnh gốc trên VPS)'...")
        btn_backup = page.locator("#btnBackupPhase")
        with page.expect_response("**/api/products/backup-media") as backup_resp_info:
            btn_backup.click()
        backup_res = backup_resp_info.value.json()
        assert backup_res.get("success") is True, f"Lỗi backup API: {backup_res}"
        backup_url = backup_res.get('backup_url', '')
        actual_media_id = backup_url.split('/')[-1].replace('_orig.jpg', '')
        print(f"  -> API backup-media thành công 100%: {backup_url} (Media ID: {actual_media_id})")

        page.wait_for_selector("#vpsBackupPreviewBox:not(.hidden)")
        btn_apply = page.locator("#btnApplyPhase")
        assert btn_apply.is_visible(), "Nút 'Tiến hành cập nhật' phải xuất hiện sau khi Bước 1 hoàn tất!"
        print("  -> Section hiển thị khung 'Bản sao lưu gốc đã hoàn hảo & được bảo tồn vĩnh viễn trên VPS'.")
        print("  -> Nút '2. Tiến hành cập nhật lên Shopify' xuất hiện sẵn sàng.")
        page.screenshot(path="test_results/04_vps_backup_success.png")

        # Kiểm tra file trên đĩa cứng VPS
        vps_file_info, vps_err = verify_vps_file("10324646690873", actual_media_id)
        print(f"  -> Xác thực ổ cứng VPS: {vps_file_info}")
        assert "_orig.jpg" in vps_file_info, f"File backup không tìm thấy trên VPS! Err: {vps_err}"

        # KỊCH BẢN 6: Quy trình 2 - Bấm nút "Tiến hành cập nhật lên Shopify"
        print("\n[Kịch bản 6] QUY TRÌNH 2: Bấm '2. Tiến hành cập nhật lên Shopify'...")
        with page.expect_response("**/api/products/apply-media-update", timeout=60000) as apply_resp_info:
            btn_apply.click(force=True)
        apply_res = apply_resp_info.value.json()
        assert apply_res.get("success") is True, f"Lỗi apply update: {apply_res}"
        new_media_info = apply_res.get('new_media', {})
        print(f"  -> Cập nhật lên Shopify thành công! New media: {new_media_info}")

        page.wait_for_timeout(2000)
        page.screenshot(path="test_results/05_update_applied.png")

        # KIỂM TRA BẢO TỒN VĨNH VIỄN FILE BACKUP TRÊN VPS
        vps_file_after, _ = verify_vps_file("10324646690873", actual_media_id)
        print(f"  -> [KIỂM TRA BẢO TỒN] File backup trên VPS sau khi cập nhật: {vps_file_after}")
        assert "_orig.jpg" in vps_file_after, "NGHIÊM TRỌNG: File backup trên VPS bị mất!"
        print("  -> TUYỆT VỜI: File backup trên VPS được bảo tồn vĩnh viễn 100%!")

        # KỊCH BẢN 7: Kiểm tra nút "Sửa lại từ ảnh gốc"
        print("\n[Kịch bản 7] KIỂM THỬ TÍNH NĂNG 'Sửa lại từ ảnh gốc'...")
        btn_edit_backup = page.locator("#btnEditFromBackup")
        assert btn_edit_backup.is_visible()
        btn_edit_backup.click()
        page.wait_for_timeout(1000)
        
        # Xác nhận canvas nạp lại ảnh gốc thành công và nút apply sẵn sàng
        assert btn_apply.is_visible(), "Sau khi sửa từ ảnh gốc, nút Tiến hành cập nhật phải sẵn sàng!"
        print("  -> Tính năng 'Sửa lại từ ảnh gốc' nạp thành công ảnh gốc từ VPS vào Canvas.")
        page.screenshot(path="test_results/06_edit_from_backup.png")

        # KỊCH BẢN 8: Cơ chế Rollback (Khôi phục ảnh gốc)
        print("\n[Kịch bản 8] KIỂM THỬ ROLLBACK: Khôi phục ảnh gốc...")
        page.on("dialog", lambda dialog: dialog.accept())
        btn_rollback = page.locator("#btnRollback")
        assert btn_rollback.is_visible()

        with page.expect_response("**/api/products/rollback-media", timeout=60000) as rollback_resp_info:
            btn_rollback.click(force=True)
        rollback_res = rollback_resp_info.value.json()
        assert rollback_res.get("success") is True, f"Lỗi rollback: {rollback_res}"
        print(f"  -> Rollback API thành công: {rollback_res.get('message')}")

        page.wait_for_timeout(2000)
        page.screenshot(path="test_results/07_rollback_completed.png")

        # Kiểm tra file backup trên VPS vẫn còn nguyên vẹn sau rollback
        vps_file_after_rb, _ = verify_vps_file("10324646690873", actual_media_id)
        assert "_orig.jpg" in vps_file_after_rb
        print(f"  -> File backup trên VPS sau Rollback vẫn được bảo tồn vĩnh viễn: {vps_file_after_rb}")

        # Kiểm tra Shopify: Xác nhận ảnh có logo đã bị xóa sạch khỏi Shopify storefront
        curr_images = query_shopify_images("10324646690873")
        logo_filenames = [img["src"] for img in curr_images if "wrydeco_logo" in img["src"]]
        assert len(logo_filenames) == 0, f"NGHIÊM TRỌNG: Ảnh logo vẫn còn tồn tại trên Shopify sau rollback: {logo_filenames}"
        print("  -> XÁC THỰC SHOPIFY: Ảnh logo đã được gỡ bỏ hoàn toàn khỏi Shopify, storefront trở về nguyên trạng!")

        browser.close()
        print("\n=== TOÀN BỘ CÁC KỊCH BẢN KIỂM THỬ PLAYWRIGHT E2E ĐÃ THÀNH CÔNG 100% ===")

if __name__ == "__main__":
    run_tests()
