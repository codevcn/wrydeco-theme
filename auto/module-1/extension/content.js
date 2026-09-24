/**
 * Wrydeco Amazon Scraper - Content Script
 * Compatible with Chrome Extension Manifest V3
 *
 * Supports:
 * 1. Preset Tier Mode (Bảng giá kích thước cố định theo phân loại đồ gỗ & phân cấp giá)
 * 2. Dynamic Mode (Cào động từ Customization form/iframe của Amazon)
 */

(() => {
  const isTopFrame = window === window.top;

  /**
   * Cấu hình bảng kích thước cố định cho Preset Tier Mode
   * (Được giữ nguyên chính xác từ script.fixed.js)
   */
  const SIZE_CONFIG = {
    standing: {
      PREM: [
        { value: '50"W x 45"H x 8"D', additional_price: 3906 },
        { value: '65"W x 60"H x 9"D', additional_price: 4426 },
        { value: '75"W x 65"H x 10"D', additional_price: 4947 },
        { value: '89"W x 80"H x 10-12"D', additional_price: 5468 },
      ],
      LOW: [
        { value: '45"W x 45"H x 8"D', additional_price: 2343 },
        { value: '59"W x 50"H x 9"D', additional_price: 2864 },
        { value: '75"W x 65"H x 10"D', additional_price: 3385 },
        { value: '89"W x 80"H x 10-12"D', additional_price: 3906 },
      ],
    },
    corner: {
      LUXURY: [
        { value: '49"W x 55"H x 8"D', additional_price: 4687 },
        { value: '60"W x 60"H x 10"D', additional_price: 5128 },
        { value: '75"W x 69"H x 12"D', additional_price: 5581 },
        { value: '90"W x 82"H x 12"D', additional_price: 6034 },
      ],
      PREM: [
        { value: '49"W x 55"H x 8"D', additional_price: 2983 },
        { value: '60"W x 60"H x 10"D', additional_price: 3783 },
        { value: '75"W x 69"H x 12"D', additional_price: 4583 },
        { value: '90"W x 82"H x 12"D', additional_price: 5483 },
      ],
      LOW: [
        { value: '49"W x 55"H x 8"D', additional_price: 2391 },
        { value: '60"W x 60"H x 10"D', additional_price: 2991 },
        { value: '75"W x 69"H x 12"D', additional_price: 3783 },
        { value: '90"W x 82"H x 12"D', additional_price: 4591 },
      ],
    },
    floating: {
      PREM: [
        { value: '45"W x 45"H x 8"D', additional_price: 1653 },
        { value: '55"W x 55"H x 8"D', additional_price: 1953 },
        { value: '65"W x 65"H x 10"D', additional_price: 2245 },
        { value: '80"W x 80"H x 10-12"D', additional_price: 2675 },
      ],
      LOW: [
        { value: '45"W x 45"H x 8"D', additional_price: 1553 },
        { value: '55"W x 55"H x 8"D', additional_price: 1653 },
        { value: '65"W x 65"H x 10"D', additional_price: 2045 },
        { value: '80"W x 80"H x 10-12"D', additional_price: 2375 },
      ],
    },
  };

  /**
   * Danh sách customization types cần bỏ qua trong Dynamic Mode
   */
  const DEFAULT_IGNORE_TYPES = [
    "Customization Confirmation",
    "Note to seller (Optional)",
    "Other requirements",
    "Review Photo Before Final Finish",
    "Additional Note for Seller",
    "Custom Tier Size Confirmation",
    "Driftwood may differ from photos. We'll message the best raw piece. Check messages?",
    "Select Package",
    "Communication",
    "Comunication",
    "Product will slightly different as shown in pictures, please check your MESSAGES to confirm order!",
    "Live edge wood may differ from photos. We'll message the best raw piece. Check messages?",
  ];

  /**
   * Danh sách customization type cần bỏ option mặc định không tăng giá
   */
  const DEFAULT_VARIANT_FOR_DEFAULT_OPTION_TO_IGNORE = ["size", "select width"];

  // Utility helpers
  const normalizeText = (value) =>
    String(value ?? "")
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim();

  const normalizeForComparison = (value) =>
    normalizeText(value)
      .toLocaleLowerCase()
      .replace(/[\u2018\u2019]/g, "'")
      .replace(/[\u201C\u201D]/g, '"')
      .replace(/:\s*$/, "");

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const getErrorMessage = (error) =>
    error instanceof Error ? error.message : String(error);

  const roundPrice = (value) =>
    Math.round((value + Number.EPSILON) * 100) / 100;

  const waitFor = async (condition, timeout = 5000, interval = 100) => {
    const startedAt = Date.now();
    while (Date.now() - startedAt < timeout) {
      try {
        const result = await condition();
        if (result) return result;
      } catch {
        // Retry
      }
      await sleep(interval);
    }
    return null;
  };

  /**
   * Gửi log tiến trình về Extension Popup & console
   */
  const sendLog = (message, level = "info") => {
    const timestamp = new Date().toLocaleTimeString();
    console.log(`[Wrydeco Scraper][${level.toUpperCase()}] ${message}`);

    try {
      chrome.runtime
        .sendMessage({
          type: "SCRAPE_LOG",
          level,
          message,
          timestamp,
        })
        .catch(() => {
          // Popup có thể đã đóng, bỏ qua
        });
    } catch {
      // Bỏ qua lỗi kết nối
    }
  };

  /**
   * Hiển thị nút "Copy product JSON" nổi ở góc màn hình Amazon
   */
  const showCopyJsonButton = (json) => {
    const existing = document.getElementById("amazon-product-json-copy-button");
    if (existing) existing.remove();

    const button = document.createElement("button");
    button.id = "amazon-product-json-copy-button";
    button.type = "button";
    button.textContent = "📋 Copy product JSON (Wrydeco)";

    Object.assign(button.style, {
      position: "fixed",
      right: "24px",
      bottom: "24px",
      zIndex: "2147483647",
      padding: "14px 20px",
      border: "none",
      borderRadius: "8px",
      background: "#131921",
      color: "#ffffff",
      fontSize: "14px",
      fontWeight: "700",
      fontFamily: "Arial, sans-serif",
      cursor: "pointer",
      boxShadow: "0 6px 24px rgba(0, 0, 0, 0.3)",
      display: "flex",
      alignItems: "center",
      gap: "8px",
    });

    button.addEventListener("mouseenter", () => {
      button.style.background = "#232f3e";
    });
    button.addEventListener("mouseleave", () => {
      button.style.background = "#131921";
    });

    button.addEventListener("click", async () => {
      button.disabled = true;
      button.textContent = "⏳ Copying...";

      try {
        const copied = await copyToClipboard(json);
        if (!copied) throw new Error("Clipboard write failed");
        button.textContent = "✅ Copied successfully!";
      } catch (err) {
        console.warn("Could not copy JSON to clipboard:", err);
        button.textContent = "❌ Copy failed - Try again";
      } finally {
        button.disabled = false;
      }
    });

    document.body.appendChild(button);
  };

  const copyToClipboard = async (text) => {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch {
        // Fallback
      }
    }

    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.top = "0";

    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length);

    let copied = false;
    try {
      copied = document.execCommand("copy");
    } finally {
      textarea.remove();
    }
    return copied;
  };

  // ============================================================
  // CÁC HÀM CÀO DỮ LIỆU TỔNG QUÁT
  // ============================================================

  /**
   * 1. Cào tiêu đề sản phẩm
   */
  const extractProductTitle = () => {
    const titleElem =
      document.getElementById("productTitle") ||
      document.querySelector("#title span") ||
      document.querySelector("h1.a-size-large");

    if (!titleElem) {
      throw new Error("Không tìm thấy phần tử tiêu đề sản phẩm (#productTitle).");
    }

    const title = normalizeText(titleElem.textContent);
    if (!title) {
      throw new Error("Tiêu đề sản phẩm trống.");
    }
    return title;
  };

  /**
   * 2. Cào danh sách mô tả bullet points
   */
  const extractProductDescription = () => {
    const selectors = [
      "ul.a-unordered-list.a-vertical.a-spacing-mini > li .a-list-item",
      "#feature-bullets ul li:not(#replacementPartsFitmentBullet) .a-list-item",
      "#featurebullets_feature_div ul li .a-list-item",
    ];

    for (const selector of selectors) {
      const items = Array.from(document.querySelectorAll(selector))
        .map((el) => normalizeText(el.textContent))
        .filter((text) => {
          if (!text) return false;
          if (/^make sure this fits/i.test(text)) return false;
          return true;
        });

      if (items.length > 0) {
        return items;
      }
    }

    // Fallback sang #productDescription nếu sản phẩm không có bullet points (dạng handmade/custom)
    const descContainer = document.querySelector("#productDescription");
    if (descContainer) {
      const paragraphs = Array.from(descContainer.querySelectorAll("p, span"))
        .map((el) => normalizeText(el.textContent))
        .filter((text) => text.length > 20);
      if (paragraphs.length > 0) {
        return paragraphs;
      }
    }

    throw new Error("Không tìm thấy danh sách mô tả (bullet points) hợp lệ.");
  };

  /**
   * 3. Cào ảnh Gallery kích thước lớn
   */
  const extractProductImages = async () => {
    const links = [];

    const addLink = (url) => {
      if (!url || typeof url !== "string") return;
      let cleanUrl = url.trim();
      if (!cleanUrl || cleanUrl.startsWith("data:") || cleanUrl.includes("play-button")) return;
      // Loại bỏ tham số crop/resize động của Amazon để lấy ảnh gốc độ phân giải cao nhất
      cleanUrl = cleanUrl.replace(/\._[^/]+?_\./, ".");
      if (!links.includes(cleanUrl)) {
        links.push(cleanUrl);
      }
    };

    // Tier 1: Trích xuất trực tiếp từ metadata colorImages trong script tag của Amazon
    try {
      const scripts = document.querySelectorAll("script:not([src])");
      for (const script of scripts) {
        const content = script.textContent;
        if (content.includes("'colorImages'") || content.includes('"colorImages"')) {
          const match =
            content.match(/'colorImages':\s*(\{[^;]+?\})\s*,\s*'colorToAsin'/s) ||
            content.match(/"colorImages":\s*(\{[^;]+?\})\s*,\s*"colorToAsin"/s) ||
            content.match(/'colorImages':\s*(\{[^;]+?\})\s*;/s);
          if (match) {
            try {
              const data = JSON.parse(match[1]);
              const initial = data.initial || [];
              for (const item of initial) {
                const hiRes = item.hiRes || item.large;
                if (hiRes) addLink(hiRes);
              }
              if (links.length > 0) {
                sendLog(`Đã trích xuất ${links.length} ảnh chất lượng cao từ metadata sản phẩm.`, "success");
                return links;
              }
            } catch {}
          }
        }
      }
    } catch {}

    // Tier 2: Quét từ Gallery Viewer #ivThumbs
    const getLargeImageUrl = () => {
      const img = document.querySelector("#ivLargeImage img");
      if (!img) return null;
      return img.currentSrc || img.src || img.getAttribute("src") || null;
    };

    let thumbnailItems = [
      ...document.querySelectorAll('#ivThumbs .ivThumb[id^="ivImage_"]'),
    ].filter(
      (thumb) =>
        !thumb.classList.contains("placeholder") &&
        Boolean(thumb.querySelector(".ivThumbImage"))
    );

    // Nếu viewer chưa mở, thử mở viewer bằng cách click vào ảnh chính landingImage
    if (thumbnailItems.length === 0) {
      const landingImage =
        document.querySelector("#landingImage") ||
        document.querySelector("#imgTagWrapperId img") ||
        document.querySelector("#imageBlock .image.item img");

      if (landingImage) {
        sendLog("Viewer ảnh chưa mở. Đang kích hoạt mở viewer ảnh...", "info");
        try {
          landingImage.click();
          await sleep(600);
          thumbnailItems = [
            ...document.querySelectorAll('#ivThumbs .ivThumb[id^="ivImage_"]'),
          ].filter(
            (thumb) =>
              !thumb.classList.contains("placeholder") &&
              Boolean(thumb.querySelector(".ivThumbImage"))
          );
        } catch {}
      }
    }

    if (thumbnailItems.length > 0) {
      sendLog(`Tìm thấy ${thumbnailItems.length} thumbnails trong gallery viewer.`, "info");
      for (let index = 0; index < thumbnailItems.length; index++) {
        const thumbnail = thumbnailItems[index];
        const thumbnailId = thumbnail.id || `thumbnail-${index}`;

        try {
          thumbnail.scrollIntoView({
            behavior: "auto",
            block: "nearest",
            inline: "nearest",
          });
          await sleep(100);

          const previousImageUrl = getLargeImageUrl();

          thumbnail.dispatchEvent(
            new MouseEvent("click", {
              bubbles: true,
              cancelable: true,
              view: window,
            })
          );

          const largeImageUrl = await waitFor(
            () => {
              const selected =
                thumbnail.classList.contains("selected") ||
                thumbnail.getAttribute("aria-pressed") === "true";
              const currentImageUrl = getLargeImageUrl();

              if (!currentImageUrl) return null;

              if (selected || currentImageUrl !== previousImageUrl) {
                const imgEl = document.querySelector("#ivLargeImage img");
                if (imgEl?.complete && imgEl.naturalWidth > 0) {
                  return currentImageUrl;
                }
              }
              return null;
            },
            4000,
            100
          );

          if (largeImageUrl) addLink(largeImageUrl);
        } catch (err) {
          console.warn(`Lỗi khi đọc thumbnail ${thumbnailId}:`, err);
        }
        await sleep(150);
      }

      if (links.length > 0) {
        return links;
      }
    }

    // Tier 3: Trích xuất ảnh gallery từ #altImages và #landingImage
    sendLog("Đang trích xuất ảnh gallery từ danh sách #altImages...", "info");
    const altThumbnails = document.querySelectorAll(
      "#altImages ul li:not(.videoThumbnail):not(.video) img, #altImages ul li.imageThumbnail img"
    );

    for (const img of altThumbnails) {
      if (img.closest(".videoThumbnail, .video, .a-carousel-card.video")) continue;
      const rawSrc =
        img.getAttribute("data-old-hires") ||
        img.getAttribute("src") ||
        img.currentSrc;
      if (rawSrc) addLink(rawSrc);
    }

    // Thêm ảnh từ #landingImage (kiểm tra cả data-a-dynamic-image độ phân giải cao)
    const mainLandingImg = document.querySelector("#landingImage");
    if (mainLandingImg) {
      const dynamicData = mainLandingImg.getAttribute("data-a-dynamic-image");
      if (dynamicData) {
        try {
          const parsed = JSON.parse(dynamicData);
          Object.keys(parsed).forEach(addLink);
        } catch {}
      }
      const hires = mainLandingImg.getAttribute("data-old-hires") || mainLandingImg.src;
      if (hires) addLink(hires);
    }

    if (links.length > 0) {
      return links;
    }

    throw new Error("Không tìm thấy ảnh sản phẩm hợp lệ trong gallery.");
  };

  /**
   * 4. Cào A+ Content (Rich Description)
   */
  const extractProductRichDescription = async () => {
    const emptyRichDescription = '<div class="description-root"></div>';

    const getBestImageUrl = (image) => {
      if (!image) return null;
      const directCandidates = [
        image.getAttribute("data-src"),
        image.getAttribute("data-a-hires"),
        image.getAttribute("src"),
        image.currentSrc,
      ];

      for (const candidate of directCandidates) {
        const url = normalizeText(candidate);
        if (url && !url.startsWith("data:")) return url;
      }

      const srcset =
        image.getAttribute("data-srcset") || image.getAttribute("srcset");
      if (srcset) {
        const candidates = srcset
          .split(",")
          .map((item) => normalizeText(item))
          .filter(Boolean);

        for (let index = candidates.length - 1; index >= 0; index--) {
          const candidate = candidates[index];
          const url = normalizeText(candidate.split(/\s+/)[0]);
          if (url && !url.startsWith("data:")) return url;
        }
      }
      return null;
    };

    const isInsideVideoModule = (image) =>
      Boolean(
        image.closest(
          [
            ".premium-module-8-hero-video",
            '[cel_widget_id*="video"]',
            ".premium-aplus-module-8-video",
            ".video-container",
            ".video-placeholder",
            ".vse-player-container",
            '[data-csa-c-component="aplus-vse-video-widget"]',
          ].join(",")
        )
      );

    const isAplusMediaUrl = (url) => {
      if (!url) return false;
      return (
        url.includes("aplus-media-library-service-media") ||
        url.includes("/aplus-media/")
      );
    };

    const isInsideAplusModule = (image) =>
      Boolean(
        image.closest(
          [
            ".aplus-module",
            ".aplus-content-wrapper",
            '[cel_widget_id^="aplus-"]',
            "#aplus",
            "#aplus_feature_div",
          ].join(",")
        )
      );

    // Chờ A+ Content render
    await waitFor(
      () =>
        document.querySelector(
          [
            ".aplus-content-wrapper",
            "#aplus_feature_div",
            "#aplus",
            ".aplus-module",
          ].join(",")
        ),
      6000,
      150
    );

    const roots = [];
    const addRoot = (element) => {
      if (element && !roots.includes(element)) {
        roots.push(element);
      }
    };

    document.querySelectorAll(".aplus-content-wrapper").forEach(addRoot);
    addRoot(document.getElementById("aplus_feature_div"));
    addRoot(document.getElementById("aplus"));

    if (roots.length === 0) {
      document
        .querySelectorAll('.aplus-module, [cel_widget_id^="aplus-"]')
        .forEach((module) => {
          addRoot(module.closest(".aplus-content-wrapper") || module.parentElement);
        });
    }

    const candidateImages = [];
    const addCandidate = (image) => {
      if (image && !candidateImages.includes(image)) {
        candidateImages.push(image);
      }
    };

    for (const root of roots) {
      root.querySelectorAll("img").forEach(addCandidate);
    }

    // Fallback toàn document nếu Amazon thay đổi container
    if (candidateImages.length === 0) {
      document
        .querySelectorAll(
          [
            'img[src*="aplus-media-library-service-media"]',
            'img[data-src*="aplus-media-library-service-media"]',
            'img[data-a-hires*="aplus-media-library-service-media"]',
          ].join(",")
        )
        .forEach(addCandidate);
    }

    const imageMap = new Map();
    for (const image of candidateImages) {
      if (isInsideVideoModule(image)) continue;

      const imageUrl = getBestImageUrl(image);
      if (!imageUrl) continue;

      const validAplusImage =
        isInsideAplusModule(image) || isAplusMediaUrl(imageUrl);
      if (!validAplusImage) continue;

      // Bỏ ảnh nhỏ <= 50x50
      if (
        image.complete &&
        image.naturalWidth > 0 &&
        image.naturalHeight > 0 &&
        image.naturalWidth <= 50 &&
        image.naturalHeight <= 50
      ) {
        continue;
      }

      if (imageMap.has(imageUrl)) continue;

      const clonedImage = image.cloneNode(false);
      clonedImage.setAttribute("src", imageUrl);
      clonedImage.removeAttribute("data-src");
      clonedImage.removeAttribute("data-a-hires");
      clonedImage.removeAttribute("data-srcset");
      clonedImage.removeAttribute("srcset");
      clonedImage.removeAttribute("loading");
      clonedImage.removeAttribute("decoding");

      imageMap.set(imageUrl, clonedImage.outerHTML);
    }

    const images = Array.from(imageMap.values());
    if (images.length === 0) {
      sendLog("Không tìm thấy ảnh A+ Content. Dùng rich description rỗng.", "warn");
      return emptyRichDescription;
    }

    sendLog(`A+ Content: Lấy thành công ${images.length} ảnh.`, "success");
    return '<div class="description-root">' + images.join(" ") + "</div>";
  };

  /**
   * 5. Parse Amazon Price Element
   */
  const parseAmazonPriceElement = (priceElement) => {
    if (!priceElement) {
      throw new Error("Không tìm thấy phần tử giá sản phẩm.");
    }

    const wholeText = priceElement.querySelector(".a-price-whole")?.textContent;
    const fractionText = priceElement.querySelector(".a-price-fraction")?.textContent;

    const whole = String(wholeText ?? "").replace(/[^\d]/g, "");
    const fraction = String(fractionText ?? "00")
      .replace(/[^\d]/g, "")
      .padEnd(2, "0")
      .slice(0, 2);

    if (!whole) {
      throw new Error("Không thể đọc phần nguyên của giá sản phẩm.");
    }

    const price = Number(`${whole}.${fraction}`);
    if (!Number.isFinite(price)) {
      throw new Error("Giá sản phẩm không hợp lệ.");
    }
    return price;
  };

  /**
   * Lấy Base Price từ trang Amazon (kiểm tra cả trang chính và footer customization)
   */
  const getBasePriceFromAmazon = (customizationDoc = null) => {
    const selectors = [
      "#corePriceDisplay_desktop_feature_div .a-price",
      "#corePrice_desktop .a-price",
      "#priceblock_ourprice",
      "#priceblock_dealprice",
      "#apex_desktop .a-price",
    ];

    for (const selector of selectors) {
      const el = document.querySelector(selector);
      if (el) {
        try {
          return parseAmazonPriceElement(el);
        } catch {
          // Thử selector kế tiếp
        }
      }
    }

    const customizationPriceEl = document.querySelector(
      '#gc-desktop-footer-wrapper .a-price[data-a-size="xl"][data-a-color="base"]'
    );
    if (customizationPriceEl) {
      try {
        return parseAmazonPriceElement(customizationPriceEl);
      } catch {}
    }

    // Kiểm tra trong customizationDoc nếu có (trường hợp iframe)
    if (customizationDoc) {
      try {
        const iframeFooterEl = customizationDoc.querySelector(
          '#gc-desktop-footer-wrapper .a-price[data-a-size="xl"][data-a-color="base"]'
        );
        if (iframeFooterEl) {
          return parseAmazonPriceElement(iframeFooterEl);
        }
      } catch {}
    }

    throw new Error("Không tìm thấy giá ở khu vực giá chính và customization footer.");
  };

  /**
   * Làm sạch URL sản phẩm Amazon, loại bỏ tracking query params
   */
  const getCleanAmazonUrl = () => {
    try {
      const url = new URL(window.location.href);
      const match =
        url.pathname.match(/\/dp\/([A-Z0-9]{10})/i) ||
        url.pathname.match(/\/gp\/product\/([A-Z0-9]{10})/i);
      if (match) {
        return `https://${url.hostname}/dp/${match[1]}`;
      }
      return `${url.origin}${url.pathname}`;
    } catch {
      return normalizeText(window.location.href);
    }
  };

  // ============================================================
  // PRESET TIER MODE LOGIC
  // ============================================================

  const buildPresetVariantData = (furnitureType, priceTier) => {
    const furnitureConfig = SIZE_CONFIG[furnitureType];
    if (!furnitureConfig) {
      throw new Error(
        `Loại sản phẩm không hợp lệ: "${furnitureType}". Cho phép: standing, corner, floating.`
      );
    }

    const sizeOptions = furnitureConfig[priceTier];
    if (!sizeOptions) {
      const allowedTiers = Object.keys(furnitureConfig).join(", ");
      throw new Error(
        `Phân cấp giá "${priceTier}" không hợp lệ cho "${furnitureType}". Cho phép: ${allowedTiers}.`
      );
    }

    if (!Array.isArray(sizeOptions) || sizeOptions.length !== 4) {
      throw new Error(
        `Bảng giá SIZE_CONFIG.${furnitureType}.${priceTier} phải có chính xác 4 kích thước.`
      );
    }

    return sizeOptions.map((sizeOption, index) => {
      const value = normalizeText(sizeOption?.value);
      const additionalPrice = Number(sizeOption?.additional_price);

      if (!value) {
        throw new Error(`Kích thước tại index ${index} không có value hợp lệ.`);
      }

      return {
        options: [
          {
            name: "Size",
            value,
          },
        ],
        additional_price: additionalPrice,
      };
    });
  };

  // ============================================================
  // DYNAMIC MODE LOGIC (CÀO TỪ CUSTOMIZATION POPUP / IFRAME)
  // ============================================================

  const isSizeType = (normalizedType) => {
    const compactType = normalizedType.replace(/[\s_-]+/g, "");
    return /\bsize\b/i.test(normalizedType) || compactType.includes("customsize");
  };

  const shouldRemoveDefaultOption = (
    normalizedType,
    variantsToIgnore = DEFAULT_VARIANT_FOR_DEFAULT_OPTION_TO_IGNORE
  ) => {
    const configured = variantsToIgnore
      .map((t) => normalizeForComparison(t))
      .filter(Boolean);

    return configured.some((t) => {
      if (t === "size") return isSizeType(normalizedType);
      return normalizedType === t;
    });
  };

  const removeDefaultOption = (type, options) => {
    if (options.length <= 1) {
      throw new Error(
        `Type "${type}" chỉ có ${options.length} option. Không thể bỏ option mặc định.`
      );
    }

    const zeroPriceOptions = options.filter(
      (opt) => opt.additional_price === 0 && !opt.has_explicit_price
    );

    let optionToRemove = null;
    if (zeroPriceOptions.length === 1) {
      optionToRemove = zeroPriceOptions[0];
    } else if (
      zeroPriceOptions.length > 1 &&
      zeroPriceOptions.some((opt) => opt.dom_index === 0)
    ) {
      optionToRemove = zeroPriceOptions.find((opt) => opt.dom_index === 0) || null;
      sendLog(`Type "${type}" có nhiều option 0đ. Đang loại bỏ option đầu tiên trong DOM.`, "warn");
    } else {
      throw new Error(
        `Không thể xác định an toàn option mặc định cần bỏ trong type "${type}".`
      );
    }

    return options.filter((opt) => opt !== optionToRemove);
  };

  const parseAdditionalPrice = (priceText, { type, option, strategy = "error" }) => {
    const normalizedPrice = normalizeText(priceText);
    if (!normalizedPrice) return 0;

    const matches = normalizedPrice.match(/\d[\d,]*(?:\.\d+)?/g) ?? [];
    const prices = matches
      .map((v) => Number(v.replace(/,/g, "")))
      .filter(Number.isFinite);

    if (prices.length === 0) {
      throw new Error(
        `Không thể parse giá "${normalizedPrice}" của option "${option}" trong type "${type}".`
      );
    }

    if (prices.length === 1) {
      const isNegative =
        /^-\s*\$?/.test(normalizedPrice) || /\(\s*\$?[\d,]/.test(normalizedPrice);
      return isNegative ? -prices[0] : prices[0];
    }

    if (strategy === "min") return Math.min(...prices);
    if (strategy === "max") return Math.max(...prices);

    throw new Error(
      `Phát hiện nhiều mức giá trong "${normalizedPrice}" của option "${option}" thuộc type "${type}". ` +
        `Chiến lược hiện tại là "error". Hãy chọn "min" hoặc "max" trong tùy chọn.`
    );
  };

  const getOptionPrice = (optionElement, type, optionValue, strategy = "error") => {
    const priceEl = optionElement.querySelector(".gc-swatch-price");
    if (priceEl) {
      const rawPriceText = normalizeText(priceEl.textContent);
      return {
        additionalPrice: parseAdditionalPrice(rawPriceText, {
          type,
          option: optionValue,
          strategy,
        }),
        hasExplicitPrice: true,
        rawPriceText,
      };
    }

    const ariaLabel = normalizeText(optionElement.getAttribute("aria-label"));
    const priceMatch = ariaLabel.match(
      /(?:,\s*)?([+-]\s*\$?\s*\d[\d,]*(?:\.\d+)?(?:\s*[-–—]\s*\$?\s*\d[\d,]*(?:\.\d+)?)?)\s*$/
    );

    if (!priceMatch) {
      return {
        additionalPrice: 0,
        hasExplicitPrice: false,
        rawPriceText: "",
      };
    }

    const rawPriceText = normalizeText(priceMatch[1]);
    return {
      additionalPrice: parseAdditionalPrice(rawPriceText, {
        type,
        option: optionValue,
        strategy,
      }),
      hasExplicitPrice: true,
      rawPriceText,
    };
  };

  /**
   * Trích xuất các tùy biến và tính tích Descartes từ một document cụ thể (top doc hoặc iframe doc)
   */
  const extractCustomizationFromDoc = async (
    customizationDoc,
    {
      priceRangeStrategy = "error",
      ignoreTypes = DEFAULT_IGNORE_TYPES,
    } = {}
  ) => {
    // Mở các danh sách option đang thu gọn
    const collapsedButtons = [
      ...customizationDoc.querySelectorAll(
        '.gc-toggle-list-toggle-button[aria-expanded="false"]'
      ),
    ];

    if (collapsedButtons.length > 0) {
      sendLog(`Đang mở rộng ${collapsedButtons.length} mục tùy biến bị thu gọn...`, "info");
      collapsedButtons.forEach((btn) => {
        try {
          btn.click();
          btn.dispatchEvent(
            new MouseEvent("click", { bubbles: true, cancelable: true, view: window })
          );
        } catch {}
      });
      await sleep(1000);
    }

    const TYPE_SELECTOR = ".gc-OptionChooserComponent";
    const OPTION_SELECTOR = '.gc-toggle-list-option[role="radio"]';

    const typeElements = [...customizationDoc.querySelectorAll(TYPE_SELECTOR)];
    if (typeElements.length === 0) {
      throw new Error(`Không tìm thấy "${TYPE_SELECTOR}" trong Customization document.`);
    }

    const effectiveIgnoreTypes = Array.isArray(ignoreTypes)
      ? ignoreTypes
      : DEFAULT_IGNORE_TYPES;

    const normalizedIgnoreTypes = effectiveIgnoreTypes
      .map((t) => normalizeForComparison(t))
      .filter(Boolean);

    const customizationTypes = typeElements
      .map((typeElement, typeIndex) => {
        const labelEl = typeElement.querySelector(".gc-component-label");
        if (!labelEl) return null;

        const clonedLabel = labelEl.cloneNode(true);
        clonedLabel
          .querySelectorAll(".gc-component-label-required")
          .forEach((el) => el.remove());
        const type = normalizeText(clonedLabel.textContent);
        const normalizedType = normalizeForComparison(type);

        if (!type || normalizedIgnoreTypes.includes(normalizedType)) {
          if (type && normalizedIgnoreTypes.includes(normalizedType)) {
            sendLog(
              `[Dynamic Mode] Bỏ qua customization type: "${type}" (trùng khớp danh sách IGNORE_TYPES).`,
              "info"
            );
          }
          return null;
        }

        const optionElements = [...typeElement.querySelectorAll(OPTION_SELECTOR)];
        if (optionElements.length === 0) return null;

        let options = optionElements
          .filter((opt) => opt.getAttribute("aria-disabled") !== "true")
          .map((opt, domIndex) => {
            try {
              const value =
                normalizeText(opt.querySelector(".gc-swatch-label")?.textContent) ||
                normalizeText(opt.getAttribute("aria-label"));
              if (!value) return null;

              const { additionalPrice, hasExplicitPrice, rawPriceText } =
                getOptionPrice(opt, type, value, priceRangeStrategy);

              return {
                value,
                additional_price: additionalPrice,
                has_explicit_price: hasExplicitPrice,
                raw_price_text: rawPriceText,
                dom_index: domIndex,
              };
            } catch (err) {
              sendLog(`Lỗi đọc option index ${domIndex} trong "${type}": ${err.message}`, "warn");
              return null;
            }
          })
          .filter(Boolean);

        // Deduplicate
        options = Array.from(
          new Map(
            options.map((opt) => [
              `${normalizeForComparison(opt.value)}__${opt.additional_price}`,
              opt,
            ])
          ).values()
        );

        if (shouldRemoveDefaultOption(normalizedType)) {
          options = removeDefaultOption(type, options);
        }

        if (options.length === 0) return null;

        return {
          type,
          options,
        };
      })
      .filter(Boolean);

    if (customizationTypes.length === 0) {
      throw new Error("Không còn customization type hợp lệ sau khi lọc các loại bỏ qua.");
    }

    // Cartesian product
    const combinations = customizationTypes.reduce(
      (currentCombinations, customizationType) =>
        currentCombinations.flatMap((currentCombination) =>
          customizationType.options.map((option) => ({
            options: [
              ...currentCombination.options,
              {
                name: customizationType.type,
                value: option.value,
              },
            ],
            additional_price: roundPrice(
              currentCombination.additional_price + option.additional_price
            ),
          }))
        ),
      [
        {
          options: [],
          additional_price: 0,
        },
      ]
    );

    if (combinations.length === 0) {
      throw new Error("Không thể tạo Cartesian product combination nào.");
    }

    return combinations.map((c) => ({
      options: c.options,
      additional_price: c.additional_price,
    }));
  };

  // Lắng nghe yêu cầu cào dữ liệu từ Top Frame nếu script này đang chạy trong iframe (ví dụ #gc-iframe)
  if (!isTopFrame) {
    window.addEventListener("message", async (event) => {
      if (event.data?.type === "WRYDECO_EXTRACT_CUSTOMIZATION_REQ") {
        try {
          const TYPE_SELECTOR = ".gc-OptionChooserComponent";
          if (document.querySelectorAll(TYPE_SELECTOR).length === 0) {
            return;
          }

          const variantData = await extractCustomizationFromDoc(
            document,
            event.data.config || {}
          );

          // Cào footer base price nếu có trong iframe
          let footerPrice = null;
          try {
            const footerEl = document.querySelector(
              '#gc-desktop-footer-wrapper .a-price[data-a-size="xl"][data-a-color="base"]'
            );
            if (footerEl) {
              footerPrice = parseAmazonPriceElement(footerEl);
            }
          } catch {}

          if (event.source) {
            event.source.postMessage(
              {
                type: "WRYDECO_EXTRACT_CUSTOMIZATION_RES",
                success: true,
                variant_data: variantData,
                base_price: footerPrice,
              },
              "*"
            );
          }
        } catch (err) {
          if (event.source) {
            event.source.postMessage(
              {
                type: "WRYDECO_EXTRACT_CUSTOMIZATION_RES",
                success: false,
                error: getErrorMessage(err),
              },
              "*"
            );
          }
        }
      }
    });
  }

  const extractDynamicVariantData = async ({
    timeoutMs = 30000,
    priceRangeStrategy = "error",
    ignoreTypes = DEFAULT_IGNORE_TYPES,
  } = {}) => {
    const IFRAME_SELECTOR = "#gc-iframe";
    const TYPE_SELECTOR = ".gc-OptionChooserComponent";

    // 1. Kiểm tra trực tiếp trên document hiện tại (nếu customization nằm trên main page hoặc mở trực tiếp)
    if (document.querySelectorAll(TYPE_SELECTOR).length > 0) {
      sendLog("Tìm thấy Customization form trực tiếp trên trang.", "info");
      const variantData = await extractCustomizationFromDoc(document, {
        priceRangeStrategy,
        ignoreTypes,
      });
      return { variant_data: variantData, customizationDoc: document };
    }

    // 2. Thử tự động kích hoạt nút "Customize Now" nếu chưa mở modal
    const customButtons = [
      document.querySelector("#customization-button"),
      document.querySelector("#custom-actions-container a"),
      document.querySelector('input[name="submit.customize"]'),
      document.querySelector('a[href*="customization-dialog"]'),
      document.querySelector(".gc-customization-btn"),
    ];

    for (const btn of customButtons) {
      if (btn && btn.offsetParent !== null) {
        sendLog("Đã tìm thấy nút Customize Now. Đang kích hoạt mở modal...", "info");
        try {
          btn.click();
        } catch {}
        break;
      }
    }

    const startedAt = Date.now();

    while (Date.now() - startedAt < timeoutMs) {
      // Kiểm tra lại top document
      if (document.querySelectorAll(TYPE_SELECTOR).length > 0) {
        const variantData = await extractCustomizationFromDoc(document, {
          priceRangeStrategy,
          ignoreTypes,
        });
        return { variant_data: variantData, customizationDoc: document };
      }

      // Kiểm tra iframe #gc-iframe
      const iframeElement = document.querySelector(IFRAME_SELECTOR);
      if (iframeElement) {
        try {
          iframeElement.scrollIntoView({ block: "center", inline: "nearest" });
        } catch {}

        // Thử truy cập DOM trực tiếp nếu cùng origin
        let iframeDoc = null;
        try {
          iframeDoc =
            iframeElement.contentDocument || iframeElement.contentWindow?.document;
        } catch {}

        if (iframeDoc && iframeDoc.querySelectorAll(TYPE_SELECTOR).length > 0) {
          sendLog("Đã truy cập trực tiếp Customization DOM trong #gc-iframe.", "info");
          const variantData = await extractCustomizationFromDoc(iframeDoc, {
            priceRangeStrategy,
            ignoreTypes,
          });
          return { variant_data: variantData, customizationDoc: iframeDoc };
        }

        // Nếu DOM bị chặn (cross-origin / sandbox), gửi message tới content script trong iframe
        if (iframeElement.contentWindow) {
          try {
            const crossFrameResult = await new Promise((resolve) => {
              const timer = setTimeout(() => {
                window.removeEventListener("message", onMsg);
                resolve(null); // Timeout cho lần thăm dò này
              }, 2000);

              const onMsg = (event) => {
                if (event.data?.type === "WRYDECO_EXTRACT_CUSTOMIZATION_RES") {
                  clearTimeout(timer);
                  window.removeEventListener("message", onMsg);
                  resolve(event.data);
                }
              };

              window.addEventListener("message", onMsg);
              iframeElement.contentWindow.postMessage(
                {
                  type: "WRYDECO_EXTRACT_CUSTOMIZATION_REQ",
                  config: { priceRangeStrategy, ignoreTypes },
                },
                "*"
              );
            });

            if (crossFrameResult) {
              if (!crossFrameResult.success) {
                throw new Error(crossFrameResult.error || "Lỗi cào từ iframe");
              }

              sendLog(
                "Đã nhận thành công variant data từ #gc-iframe qua cross-frame messaging.",
                "success"
              );
              return {
                variant_data: crossFrameResult.variant_data,
                iframeBasePrice: crossFrameResult.base_price,
              };
            }
          } catch (err) {
            // Nếu là lỗi nghiệp vụ thực tế từ iframe trả về thì báo lỗi ngay lập tức, không chờ timeout vô ích
            if (err.message && !err.message.includes("postMessage")) {
              throw err;
            }
            sendLog(`Lỗi giao tiếp iframe: ${err.message}`, "warn");
          }
        }
      }

      await sleep(300);
    }

    throw new Error(
      `Không tìm thấy Customization form/iframe (#gc-iframe) sau ${timeoutMs}ms. ` +
        `Vui lòng đảm bảo bạn đã click "Customize Now" hoặc mở popup tùy biến trên trang Amazon.`
    );
  };

  // ============================================================
  // BỘ ĐIỀU PHỐI CÀO DỮ LIỆU CHÍNH
  // ============================================================

  const runScrape = async (config) => {
    sendLog(`Bắt đầu cào dữ liệu Amazon (Chế độ: ${config.mode.toUpperCase()})...`, "info");

    const product = {
      product_title: null,
      product_description: null,
      product_images: null,
      base_price: null,
      variant_data: null,
      product_rich_description: null,
      product_amazon_link: null,
    };

    // 1. Tiêu đề
    try {
      product.product_title = extractProductTitle();
      sendLog(`Đã lấy tiêu đề: "${product.product_title.slice(0, 60)}..."`, "success");
    } catch (err) {
      sendLog(`Lỗi lấy tiêu đề: ${err.message}`, "warn");
    }

    // 2. Mô tả (Bullet Points)
    try {
      product.product_description = extractProductDescription();
      sendLog(`Đã lấy ${product.product_description.length} bullet points mô tả.`, "success");
    } catch (err) {
      sendLog(`Lỗi lấy bullet points: ${err.message}`, "warn");
    }

    // 3. Ảnh sản phẩm Gallery
    try {
      product.product_images = await extractProductImages();
      sendLog(`Đã cào ${product.product_images.length} ảnh gallery chất lượng cao.`, "success");
    } catch (err) {
      sendLog(`Lỗi lấy ảnh gallery: ${err.message}`, "warn");
    }

    let customizationDoc = null;
    let iframeBasePrice = null;

    // 4. Variant Data
    try {
      if (config.mode === "preset") {
        sendLog(
          `Đang tạo variants theo Preset: ${config.furnitureType} / ${config.priceTier}...`,
          "info"
        );
        product.variant_data = buildPresetVariantData(
          config.furnitureType,
          config.priceTier
        );
        sendLog(
          `Đã tạo thành công ${product.variant_data.length} variants kích thước cố định.`,
          "success"
        );
      } else {
        sendLog("Đang cào variants từ Customization form/iframe...", "info");
        const dynamicResult = await extractDynamicVariantData({
          timeoutMs: config.timeoutMs || 30000,
          priceRangeStrategy: config.priceRangeStrategy || "error",
          ignoreTypes: Array.isArray(config.ignoreTypes)
            ? config.ignoreTypes
            : DEFAULT_IGNORE_TYPES,
        });
        product.variant_data = dynamicResult.variant_data;
        customizationDoc = dynamicResult.customizationDoc || null;
        iframeBasePrice = dynamicResult.iframeBasePrice || null;
        sendLog(`Đã tạo thành công ${product.variant_data.length} tổ hợp variants động.`, "success");
      }
    } catch (err) {
      sendLog(`Lỗi tạo variants: ${err.message}`, "error");
    }

    // 5. Base price
    if (config.mode === "preset") {
      product.base_price = 0;
      sendLog("Chế độ Preset Tier: Base price được đặt là 0.", "info");
    } else {
      if (typeof iframeBasePrice === "number" && Number.isFinite(iframeBasePrice)) {
        product.base_price = iframeBasePrice;
        sendLog(`Đã lấy Base Price từ Customization Footer: $${product.base_price}`, "success");
      } else {
        try {
          product.base_price = getBasePriceFromAmazon(customizationDoc);
          sendLog(`Đã lấy Base Price: $${product.base_price}`, "success");
        } catch (err) {
          sendLog(`Lỗi lấy Base Price: ${err.message}`, "warn");
        }
      }
    }

    // 6. A+ Content (Rich Description)
    try {
      sendLog("Đang cào A+ Content (Rich description)...", "info");
      product.product_rich_description = await extractProductRichDescription();
    } catch (err) {
      sendLog(`Lỗi lấy A+ Content: ${err.message}. Dùng thẻ rỗng.`, "warn");
      product.product_rich_description = '<div class="description-root"></div>';
    }

    // 7. Amazon Product Link (Chuẩn hóa URL sạch không query params)
    product.product_amazon_link = getCleanAmazonUrl();

    const output = { product };
    const jsonString = JSON.stringify(output, null, 2);

    // In console và hiển thị floating button copy trên trang Amazon
    console.log("[Wrydeco Scraper Output]:\n", jsonString);
    showCopyJsonButton(jsonString);

    sendLog("Hoàn tất cào dữ liệu! Đã tạo cấu trúc JSON hợp lệ cho Shopify.", "success");
    return output;
  };

  // ============================================================
  // MESSAGE LISTENER
  // ============================================================

  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "PING") {
      sendResponse({ status: "PONG", isTopFrame });
      return false;
    }

    if (request.action === "START_SCRAPE") {
      // Chỉ thực hiện trên top frame để tránh trùng lặp
      if (!isTopFrame) {
        return false;
      }

      runScrape(request.config)
        .then((result) => {
          sendResponse({ success: true, data: result });
        })
        .catch((err) => {
          sendLog(`Thất bại: ${err.message}`, "error");
          sendResponse({ success: false, error: err.message });
        });

      return true; // async sendResponse
    }
  });
})();
