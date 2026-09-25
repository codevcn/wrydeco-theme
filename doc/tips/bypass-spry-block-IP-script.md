# Kỹ thuật Bypass Cơ chế Chặn IP Việt Nam của Spry Interior (`spryinterior.com`)

> **Tài liệu kỹ thuật nội bộ:** Dành cho Developers và AI Agents phục vụ công tác nghiên cứu UI/UX, phân tích sản phẩm và tham chiếu chính sách của đối thủ Spry Interior mà không cần sử dụng VPN thương mại trả phí.

---

## 1. Hiện tượng & Bối cảnh

- **Trang web mục tiêu:** `https://www.spryinterior.com` (Đặc biệt là các trang chính sách, sản phẩm, bộ sưu tập, ví dụ: `/pages/modify-cancel-order`).
- **Hiện tượng khi truy cập từ Việt Nam:**
  Người dùng khi mở liên kết từ bất kỳ trình duyệt nào tại Việt Nam sẽ thấy trang chớp nháy trong khoảng 0.5–1 giây, sau đó lập tức bị chuyển hướng (**Client-side Redirect**) sang `https://www.google.com/`.

---

## 2. Phân tích Bản chất Kỹ thuật (Technical Breakdown)

Khi phân tích sâu luồng mạng và mã nguồn trả về từ máy chủ Shopify của Spry:

### 2.1 Không bị chặn ở tầng Máy chủ / Mạng (CDN Edge WAF)

- Khi dùng các công cụ HTTP thuần như `curl`, `Postman`, hoặc thư viện Python (`requests` / `urllib`), máy chủ Shopify vẫn trả về mã trạng thái **`HTTP 200 OK`**.
- Toàn bộ nội dung SSR (Server-Side Rendered) HTML của trang vẫn tồn tại đầy đủ trong phản hồi ban đầu.
- **Kết luận:** Spry **không** dùng Cloudflare WAF chặn IP ở tầng biên (Edge), mà chặn ở tầng trình duyệt (**Client-Side**).

### 2.2 App Shopify gây ra chuyển hướng

Kiểm tra danh sách script trong HTML của Spry, phát hiện một Theme App Extension được nhúng:

```html
<script src="https://cdn.shopify.com/extensions/01a0d199-b261-7efe-8209-db120e77811f/region-restrictions-376/assets/ip-blocker-embed.min.js" type="text/javascript"></script>
```

Kèm theo cấu hình Metafield trong DOM:

```json
{
  "shopIdentifier": "f6bf1c-d7.myshopify.com",
  "ipBlockerMetafields": "{\"showOverlayByPass\":true,\"disableSpyExtensions\":true,\"blockUnknownBots\":true,\"activeApp\":true,\"blockByMetafield\":false,\"visitorAnalytic\":true...}"
}
```

### 2.3 Luồng thực thi mã độc lập (Execution Flow)

1. Trình duyệt tải về mã HTML của trang Spry.
2. Trình duyệt bắt đầu tải và thực thi file `ip-blocker-embed.min.js`.
3. Script này kiểm tra IP / Quốc gia của người dùng qua API định vị địa lý hoặc headers của Shopify.
4. Phát hiện người dùng đến từ lãnh thổ bị hạn chế (Việt Nam) $\rightarrow$ Script thực hiện lệnh:
   ```javascript
   window.location.replace("https://www.google.com/");
   ```
5. Trình duyệt bị buộc chuyển hướng sang Google, ngăn người dùng đọc nội dung trang.

---

## 3. Các Phương pháp Vượt qua (Bypass Methods)

Do cơ chế chặn hoàn toàn phụ thuộc vào việc thực thi file `ip-blocker-embed.min.js`, **nguyên lý cốt lõi để bypass là chặn trình duyệt tải file script này về**.

---

### Phương pháp 1: Sử dụng Playwright / Playwright CLI (Tự động hóa / Crawl dữ liệu)

Playwright cung cấp tính năng **Network Interception** (`page.route()`), cho phép hủy bỏ (`abort`) request đến các script chỉ định trước khi chúng kịp tải.

#### Script Node.js mẫu hoàn chỉnh:

```javascript
const { chromium } = require('playwright'); // hoặc dùng đường dẫn tới playwright-core

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  // BƯỚC QUAN TRỌNG: Chặn triệt để app IP Blocker
  await page.route('**/*ip-blocker*', route => route.abort());
  await page.route('**/region-restrictions*/**', route => route.abort());

  console.log('Đang truy cập trang Spry với script chặn IP đã bị vô hiệu hóa...');
  await page.goto('https://www.spryinterior.com/pages/modify-cancel-order', {
    waitUntil: 'domcontentloaded'
  });

  // Chờ 3 giây để xác nhận không bị redirect
  await page.waitForTimeout(3000);

  console.log('URL hiện tại:', page.url());
  console.log('Tiêu đề trang:', await page.title());

  // Trích xuất nội dung văn bản
  const content = await page.evaluate(() => {
    const main = document.querySelector('main') || document.body;
    return main.innerText;
  });

  console.log('Nội dung trang đã lấy thành công:');
  console.log(content.slice(0, 500));

  // Chụp ảnh màn hình bằng chứng
  await page.screenshot({ path: 'spry-bypassed.png', fullPage: false });

  await browser.close();
})();
```

#### Sử dụng nhanh với `playwright-cli`:

```bash
playwright-cli open about:blank
playwright-cli run-code "async (page) => { await page.route('**/*ip-blocker*', r => r.abort()); await page.goto('https://www.spryinterior.com/pages/modify-cancel-order'); }"
```

---

### Phương pháp 2: Duyệt web thủ công trên Chrome / Edge / Brave

Nếu bạn là Developer/Designer cần lướt web Spry trực tiếp trên trình duyệt cá nhân:

#### Cách A: Dùng DevTools "Network Request Blocking" (Không cần cài extension)

1. Mở trang bất kỳ (ví dụ `about:blank` hoặc mở sẵn trang Spry).
2. Nhấn phím `F12` để mở **Chrome DevTools**.
3. Nhấn tổ hợp phím `Ctrl + Shift + P` (Command Palette) $\rightarrow$ gõ `Show Network request blocking` và nhấn `Enter`.
4. Tích chọn **Enable network request blocking**.
5. Nhấn nút dấu cộng `+` và thêm 2 mẫu pattern sau:
   - `*ip-blocker*`
   - `*region-restrictions*`
6. Truy cập vào `https://www.spryinterior.com` $\rightarrow$ Trang sẽ tải bình thường 100%, không còn bị redirect.

#### Cách B: Sử dụng uBlock Origin / AdGuard / Requestly

1. Cài đặt tiện ích mở rộng **uBlock Origin** (hoặc AdGuard).
2. Vào phần **Cài đặt (Settings)** $\rightarrow$ Tab **Bộ lọc của tôi (My Filters)**.
3. Thêm quy tắc sau vào cuối danh sách:
   ```adblock
   ||cdn.shopify.com/extensions/*/assets/ip-blocker-embed.min.js$script
   ||spryinterior.com/*region-restrictions*
   ```
4. Nhấn **Áp dụng thay đổi (Apply changes)**.
5. Bây giờ bạn có thể duyệt toàn bộ website Spry bình thường như người dùng tại Mỹ.

---

### Phương pháp 3: Lấy dữ liệu nhanh qua cURL hoặc Python (Không cần giả lập trình duyệt)

Vì máy chủ Shopify không chặn request HTTP thuần từ IP Việt Nam, bạn có thể lấy toàn bộ nội dung HTML thô mà không sợ bị JS redirect:

```bash
# Lấy HTML trực tiếp qua cURL
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" "https://www.spryinterior.com/pages/modify-cancel-order" > spry-page.html
```

Hoặc qua Python script:

```python
import requests

url = "https://www.spryinterior.com/pages/modify-cancel-order"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

response = requests.get(url, headers=headers, timeout=10)
if response.status_code == 200:
    print("Tải thành công, kích thước HTML:", len(response.text))
    with open("spry_content.html", "w", encoding="utf-8") as f:
        f.write(response.text)
```

---

## 4. Đánh giá Kỹ thuật & Khuyến nghị cho WRYDECO

1. **Điểm yếu của việc dùng Client-side App để chặn IP:**

   - **Bảo mật lỏng lẻo:** Bất kỳ ai có kiến thức cơ bản về DevTools, extension chặn script hoặc tool tự động hóa (Playwright, Puppeteer) đều có thể vô hiệu hóa trong vòng 30 giây.
   - **Tổn hại hiệu năng (Core Web Vitals):** Trình duyệt phải tải thêm script JS từ CDN extension của bên thứ ba, làm chậm chỉ số LCP, FID/INP và TTI.
   - **Nguy cơ lỗi SEO (SEO Leak):** Nếu cấu hình app không chuẩn, bot của công cụ tìm kiếm (Googlebot, Bingbot) có thể bị chuyển hướng nhầm sang Google.com, làm rớt index toàn bộ các trang trên website.
2. **Bài học cho Store WRYDECO:**

   - Tuyệt đối **không** cài đặt các ứng dụng chặn IP dạng Client-side tương tự lên WRYDECO.
   - Nếu cần phân chia thị trường hoặc quản lý nội dung đa quốc gia, phải sử dụng cơ chế chính quy **Shopify Markets** kết hợp tính năng định tuyến đa tiền tệ/ngôn ngữ gốc từ nền tảng để bảo đảm SEO và trải nghiệm người dùng cao cấp chuẩn Gallery Art.
