function showCopyJsonButton(json) {
  const oldButton = document.getElementById("amazon-product-json-copy-button");

  if (oldButton) {
    oldButton.remove();
  }

  const button = document.createElement("button");

  button.id = "amazon-product-json-copy-button";
  button.type = "button";
  button.textContent = "Copy product JSON";

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
  });

  button.addEventListener("mouseenter", () => {
    button.style.background = "#232f3e";
  });

  button.addEventListener("mouseleave", () => {
    button.style.background = "#131921";
  });

  button.addEventListener("click", async () => {
    const originalText = button.textContent;

    button.disabled = true;
    button.textContent = "Copying...";

    try {
      const copied = await copyToClipboard(json);

      if (!copied) {
        throw new Error("Trình duyệt từ chối thao tác copy.");
      }

      button.textContent = "Copied successfully";
    } catch (error) {
      console.warn(">>> Không thể copy JSON vào clipboard.", error);

      button.textContent = "Copy failed — try again";
      button.disabled = false;

      setTimeout(() => {
        button.textContent = originalText;
      }, 2000);
    }
  });

  document.body.appendChild(button);
}

async function copyToClipboard(text) {
  if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Chuyển sang fallback bên dưới.
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
}

(async () => {
  /**
   * ============================================================
   * CUSTOMIZATION CONFIG
   * ============================================================
   *
   * Chỉ cần thay 2 biến này để chọn loại sản phẩm
   * và bảng giá muốn sử dụng.
   *
   * FURNITURE_TYPE:
   *
   * "standing"
   * "corner"
   * "floating"
   *
   * PRICE_TIER:
   *
   * standing:
   *   "PREM"
   *   "LOW"
   *
   * corner:
   *   "LUXURY"
   *   "PREM"
   *   "LOW"
   *
   * floating:
   *   "PREM"
   *   "LOW"
   */

  const FURNITURE_TYPE = "corner";
  const PRICE_TIER = "LUXURY";

  /**
   * ============================================================
   * SIZE CONFIG
   * ============================================================
   *
   * Không lấy customization Size từ Amazon nữa.
   *
   * Các giá bên dưới được lấy từ cột "Giá".
   *
   * Không sử dụng:
   *
   * - Discount 10%
   * - Voucher
   * - Giá sau khuyến mãi
   * - Label
   *
   * Giá được lưu trực tiếp vào:
   *
   * additional_price
   */

  const SIZE_CONFIG = {
    /**
     * ==========================================================
     * STANDING BOOKSHELF
     * ==========================================================
     */
    standing: {
      PREM: [
        {
          value: '50"W x 45"H x 8"D',
          additional_price: 3906,
        },
        {
          value: '65"W x 60"H x 9"D',
          additional_price: 4426,
        },
        {
          value: '75"W x 65"H x 10"D',
          additional_price: 4947,
        },
        {
          value: '89"W x 80"H x 10-12"D',
          additional_price: 5468,
        },
      ],

      LOW: [
        {
          value: '45"W x 45"H x 8"D',
          additional_price: 2343,
        },
        {
          value: '59"W x 50"H x 9"D',
          additional_price: 2864,
        },
        {
          value: '75"W x 65"H x 10"D',
          additional_price: 3385,
        },
        {
          value: '89"W x 80"H x 10-12"D',
          additional_price: 3906,
        },
      ],
    },

    /**
     * ==========================================================
     * CORNER BOOKSHELF
     * ==========================================================
     */
    corner: {
      LUXURY: [
        {
          value: '49"W x 55"H x 8"D',
          additional_price: 4687,
        },
        {
          value: '60"W x 60"H x 10"D',
          additional_price: 5128,
        },
        {
          value: '75"W x 69"H x 12"D',
          additional_price: 5581,
        },
        {
          value: '90"W x 82"H x 12"D',
          additional_price: 6034,
        },
      ],

      PREM: [
        {
          value: '49"W x 55"H x 8"D',
          additional_price: 2983,
        },
        {
          value: '60"W x 60"H x 10"D',
          additional_price: 3783,
        },
        {
          value: '75"W x 69"H x 12"D',
          additional_price: 4583,
        },
        {
          value: '90"W x 82"H x 12"D',
          additional_price: 5483,
        },
      ],

      LOW: [
        {
          value: '49"W x 55"H x 8"D',
          additional_price: 2391,
        },
        {
          value: '60"W x 60"H x 10"D',
          additional_price: 2991,
        },
        {
          value: '75"W x 69"H x 12"D',
          additional_price: 3783,
        },
        {
          value: '90"W x 82"H x 12"D',
          additional_price: 4591,
        },
      ],
    },

    /**
     * ==========================================================
     * FLOATING BOOKSHELF
     * ==========================================================
     */
    floating: {
      PREM: [
        {
          value: '45"W x 45"H x 8"D',
          additional_price: 1653,
        },
        {
          value: '55"W x 55"H x 8"D',
          additional_price: 1953,
        },
        {
          value: '65"W x 65"H x 10"D',
          additional_price: 2245,
        },
        {
          value: '80"W x 80"H x 10-12"D',
          additional_price: 2675,
        },
      ],

      LOW: [
        {
          value: '45"W x 45"H x 8"D',
          additional_price: 1553,
        },
        {
          value: '55"W x 55"H x 8"D',
          additional_price: 1653,
        },
        {
          value: '65"W x 65"H x 10"D',
          additional_price: 2045,
        },
        {
          value: '80"W x 80"H x 10-12"D',
          additional_price: 2375,
        },
      ],
    },
  };

  /**
   * ============================================================
   * PRODUCT DATA
   * ============================================================
   *
   * Tất cả field mặc định là null.
   *
   * Field chỉ được gán khi lấy dữ liệu thành công.
   */

  const product = {
    product_title: null,
    product_description: null,
    product_images: null,
    base_price: null,
    variant_data: null,
    product_rich_description: null,
    product_amazon_link: null,
  };

  /**
   * Chuẩn hóa text.
   *
   * @param {unknown} value
   * @returns {string}
   */

  const normalizeText = (value) =>
    String(value ?? "")
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim();

  /**
   * Tạm dừng.
   *
   * @param {number} milliseconds
   * @returns {Promise<void>}
   */

  const sleep = (milliseconds) =>
    new Promise((resolve) => {
      setTimeout(resolve, milliseconds);
    });

  /**
   * Chuyển error thành message.
   *
   * @param {unknown} error
   * @returns {string}
   */

  const getErrorMessage = (error) => {
    if (error instanceof Error) {
      return error.message;
    }

    return String(error);
  };

  /**
   * In warning khi không lấy được field.
   *
   * Field vẫn giữ nguyên là null.
   *
   * @param {keyof typeof product} field
   * @param {unknown} error
   */

  const warnFieldError = (field, error) => {
    console.warn(`>>> Không thể lấy field "${field}". ` + "Field này được giữ nguyên là null.", {
      field,
      error: getErrorMessage(error),
    });
  };

  /**
   * Chờ condition trả về giá trị truthy.
   *
   * Hàm này vẫn cần cho phần lấy ảnh Amazon.
   *
   * Không còn liên quan tới customization.
   *
   * @param {() => unknown} condition
   * @param {number} timeout
   * @param {number} interval
   * @returns {Promise<unknown>}
   */

  const waitFor = async (condition, timeout = 5000, interval = 100) => {
    const startedAt = Date.now();

    while (Date.now() - startedAt < timeout) {
      try {
        const result = condition();

        if (result) {
          return result;
        }
      } catch {
        // Amazon có thể đang render lại DOM.
      }

      await sleep(interval);
    }

    return null;
  };

  /**
   * ============================================================
   * PRICE
   * ============================================================
   */

  /**
   * Parse giá từ một Amazon .a-price element.
   *
   * Ví dụ:
   *
   * <span class="a-price">
   *   <span class="a-price-whole">14,995.</span>
   *   <span class="a-price-fraction">65</span>
   * </span>
   *
   * => 14995.65
   *
   * @param {Element | null} priceElement
   * @returns {number}
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
   * Lấy base price.
   *
   * Giữ nguyên logic script cũ:
   *
   * 1. Ưu tiên giá chính trên trang sản phẩm.
   * 2. Nếu không có thì fallback sang giá footer.
   *
   * @returns {number}
   */

  const getBasePrice = () => {
    return 0;
    // const mainPriceElement = document.querySelector(
    //   "#corePriceDisplay_desktop_feature_div .a-price",
    // );

    // if (mainPriceElement) {
    //   return parseAmazonPriceElement(mainPriceElement);
    // }

    // const customizationPriceElement = document.querySelector(
    //   "#gc-desktop-footer-wrapper " + '.a-price[data-a-size="xl"][data-a-color="base"]',
    // );

    // if (customizationPriceElement) {
    //   return parseAmazonPriceElement(customizationPriceElement);
    // }

    // throw new Error("Không tìm thấy giá ở cả khu vực giá chính " + "và customization footer.");
  };

  /**
   * ============================================================
   * PRODUCT IMAGES
   * ============================================================
   */

  /**
   * Lấy URL ảnh lớn hiện tại
   * trong Amazon image viewer.
   *
   * @returns {string | null}
   */

  const getLargeImageUrl = () => {
    const image = document.querySelector("#ivLargeImage img");

    if (!image) {
      return null;
    }

    return image.currentSrc || image.src || image.getAttribute("src") || null;
  };

  /**
   * Lấy danh sách thumbnail hợp lệ.
   *
   * @returns {Element[]}
   */

  const getThumbnailItems = () =>
    [...document.querySelectorAll('#ivThumbs .ivThumb[id^="ivImage_"]')].filter(
      (thumbnail) =>
        !thumbnail.classList.contains("placeholder") &&
        Boolean(thumbnail.querySelector(".ivThumbImage")),
    );

  /**
   * Click từng thumbnail và lấy ảnh lớn.
   *
   * @returns {Promise<string[]>}
   */

  const extractProductImages = async () => {
    const thumbnailItems = getThumbnailItems();

    if (thumbnailItems.length === 0) {
      throw new Error('Không tìm thấy thumbnail ảnh trong selector "#ivThumbs".');
    }

    const links = [];

    for (let index = 0; index < thumbnailItems.length; index++) {
      const thumbnail = thumbnailItems[index];

      const thumbnailId = thumbnail.id || `thumbnail-${index}`;

      try {
        thumbnail.scrollIntoView({
          behavior: "auto",
          block: "nearest",
          inline: "nearest",
        });

        await sleep(200);

        const previousImageUrl = getLargeImageUrl();

        thumbnail.dispatchEvent(
          new MouseEvent("click", {
            bubbles: true,
            cancelable: true,
            view: window,
          }),
        );

        const largeImageUrl = await waitFor(
          () => {
            const selected =
              thumbnail.classList.contains("selected") ||
              thumbnail.getAttribute("aria-pressed") === "true";

            const currentImageUrl = getLargeImageUrl();

            if (!currentImageUrl) {
              return null;
            }

            /**
             * Thumbnail đầu tiên
             * có thể đã được chọn sẵn.
             *
             * Vì vậy URL ảnh lớn
             * không nhất thiết phải đổi.
             */

            if (selected || currentImageUrl !== previousImageUrl) {
              const imageElement = document.querySelector("#ivLargeImage img");

              if (imageElement?.complete && imageElement.naturalWidth > 0) {
                return currentImageUrl;
              }
            }

            return null;
          },
          7000,
          100,
        );

        if (!largeImageUrl) {
          console.warn(`>>> Không lấy được URL ảnh lớn ` + `của thumbnail "${thumbnailId}".`);

          continue;
        }

        if (!links.includes(largeImageUrl)) {
          links.push(largeImageUrl);
        }
      } catch (error) {
        console.warn(`>>> Có lỗi khi xử lý thumbnail ` + `"${thumbnailId}".`, error);
      }

      await sleep(300);
    }

    if (links.length === 0) {
      throw new Error("Không lấy được URL ảnh lớn hợp lệ " + "từ bất kỳ thumbnail nào.");
    }

    return links;
  };

  /**
   * ============================================================
   * A+ CONTENT V2
   * ============================================================
   *
   * Mục tiêu:
   *
   * - Không phụ thuộc vào một cấu trúc DOM cố định.
   * - Hỗ trợ nhiều kiểu A+ Content khác nhau.
   * - Chờ Amazon render/lazy-load A+.
   * - Không lấy ảnh poster / ảnh thuộc video module.
   * - Deduplicate ảnh.
   * - Có fallback nếu Amazon thay đổi A+ container.
   *
   * @returns {Promise<string>}
   */
  const extractProductRichDescription = async () => {
    const emptyRichDescription = '<div class="description-root"></div>';

    /**
     * ==========================================================
     * HELPER: LẤY URL ẢNH TỐT NHẤT
     * ==========================================================
     */

    const getBestImageUrl = (image) => {
      if (!image) {
        return null;
      }

      /**
       * Amazon có thể lưu ảnh ở nhiều attribute khác nhau
       * tùy cơ chế lazy loading / A+ module.
       */

      const directCandidates = [
        image.getAttribute("data-src"),
        image.getAttribute("data-a-hires"),
        image.getAttribute("src"),
        image.currentSrc,
      ];

      for (const candidate of directCandidates) {
        const url = normalizeText(candidate);

        if (url && !url.startsWith("data:")) {
          return url;
        }
      }

      /**
       * Fallback sang srcset.
       */

      const srcset = image.getAttribute("data-srcset") || image.getAttribute("srcset");

      if (srcset) {
        const candidates = srcset
          .split(",")
          .map((item) => normalizeText(item))
          .filter(Boolean);

        /**
         * Thường candidate cuối cùng là ảnh resolution cao nhất.
         */

        for (let index = candidates.length - 1; index >= 0; index--) {
          const candidate = candidates[index];

          const url = normalizeText(candidate.split(/\s+/)[0]);

          if (url && !url.startsWith("data:")) {
            return url;
          }
        }
      }

      return null;
    };

    /**
     * ==========================================================
     * HELPER: KIỂM TRA ẢNH CÓ NẰM TRONG VIDEO MODULE KHÔNG
     * ==========================================================
     *
     * Loại:
     *
     * - Premium A+ hero video
     * - VSE video player
     * - video container
     *
     * Không lấy thumbnail/poster/video-related image.
     */

    const isInsideVideoModule = (image) => {
      return Boolean(
        image.closest(
          [
            ".premium-module-8-hero-video",
            '[cel_widget_id*="video"]',
            ".premium-aplus-module-8-video",
            ".video-container",
            ".video-placeholder",
            ".vse-player-container",
            '[data-csa-c-component="aplus-vse-video-widget"]',
          ].join(","),
        ),
      );
    };

    /**
     * ==========================================================
     * HELPER: URL CÓ ĐẶC TRƯNG A+ MEDIA KHÔNG
     * ==========================================================
     */

    const isAplusMediaUrl = (url) => {
      if (!url) {
        return false;
      }

      return url.includes("aplus-media-library-service-media") || url.includes("/aplus-media/");
    };

    /**
     * ==========================================================
     * HELPER: ẢNH CÓ NẰM TRONG A+ MODULE KHÔNG
     * ==========================================================
     */

    const isInsideAplusModule = (image) => {
      return Boolean(
        image.closest(
          [
            ".aplus-module",
            ".aplus-content-wrapper",
            '[cel_widget_id^="aplus-"]',
            "#aplus",
            "#aplus_feature_div",
          ].join(","),
        ),
      );
    };

    /**
     * ==========================================================
     * 1. CHỜ AMAZON RENDER A+ CONTENT
     * ==========================================================
     *
     * Không bắt buộc phải có đúng một selector.
     */

    await waitFor(
      () =>
        document.querySelector(
          [".aplus-content-wrapper", "#aplus_feature_div", "#aplus", ".aplus-module"].join(","),
        ),
      7000,
      150,
    );

    /**
     * ==========================================================
     * 2. TÌM TẤT CẢ A+ ROOT CÓ THỂ CÓ
     * ==========================================================
     */

    const roots = [];

    const addRoot = (element) => {
      if (element && !roots.includes(element)) {
        roots.push(element);
      }
    };

    /**
     * Ưu tiên wrapper cụ thể nhất trước.
     */

    document.querySelectorAll(".aplus-content-wrapper").forEach(addRoot);

    addRoot(document.getElementById("aplus_feature_div"));

    addRoot(document.getElementById("aplus"));

    /**
     * Nếu các wrapper phổ biến không tồn tại,
     * thử lấy parent của A+ modules.
     */

    if (roots.length === 0) {
      document.querySelectorAll('.aplus-module, [cel_widget_id^="aplus-"]').forEach((module) => {
        addRoot(module.closest(".aplus-content-wrapper") || module.parentElement);
      });
    }

    /**
     * ==========================================================
     * 3. THU THẬP CANDIDATE IMAGES
     * ==========================================================
     */

    const candidateImages = [];

    const addCandidate = (image) => {
      if (image && !candidateImages.includes(image)) {
        candidateImages.push(image);
      }
    };

    for (const root of roots) {
      root.querySelectorAll("img").forEach(addCandidate);
    }

    /**
     * ==========================================================
     * 4. FALLBACK TOÀN DOCUMENT
     * ==========================================================
     *
     * Nếu Amazon thay đổi toàn bộ container A+,
     * tìm dựa trên URL đặc trưng của A+ Media Library.
     */

    if (candidateImages.length === 0) {
      document
        .querySelectorAll(
          [
            'img[src*="aplus-media-library-service-media"]',
            'img[data-src*="aplus-media-library-service-media"]',
            'img[data-a-hires*="aplus-media-library-service-media"]',
          ].join(","),
        )
        .forEach(addCandidate);
    }

    /**
     * ==========================================================
     * 5. FILTER + NORMALIZE + DEDUPLICATE
     * ==========================================================
     */

    const imageMap = new Map();

    for (const image of candidateImages) {
      /**
       * Bỏ toàn bộ ảnh thuộc video module.
       */

      if (isInsideVideoModule(image)) {
        continue;
      }

      const imageUrl = getBestImageUrl(image);

      if (!imageUrl) {
        continue;
      }

      /**
       * Candidate phải thỏa ít nhất một:
       *
       * 1. Nằm trong A+ module
       * 2. URL rõ ràng là A+ Media Library
       */

      const validAplusImage = isInsideAplusModule(image) || isAplusMediaUrl(imageUrl);

      if (!validAplusImage) {
        continue;
      }

      /**
       * Bỏ các ảnh rất nhỏ nếu browser đã load
       * và biết kích thước thực.
       *
       * Tránh icon / pixel / tracking image.
       */

      if (
        image.complete &&
        image.naturalWidth > 0 &&
        image.naturalHeight > 0 &&
        image.naturalWidth <= 50 &&
        image.naturalHeight <= 50
      ) {
        continue;
      }

      /**
       * Deduplicate theo URL.
       */

      if (imageMap.has(imageUrl)) {
        continue;
      }

      /**
       * Clone chỉ chính thẻ IMG,
       * không mang theo DOM Amazon xung quanh.
       */

      const clonedImage = image.cloneNode(false);

      /**
       * Đảm bảo src chính xác và có thể sử dụng
       * bên ngoài cơ chế lazy-load của Amazon.
       */

      clonedImage.setAttribute("src", imageUrl);

      /**
       * Xóa các attribute lazy-loading của Amazon
       * để tránh ảnh không load khi HTML được sử dụng
       * ở nơi khác.
       */

      clonedImage.removeAttribute("data-src");

      clonedImage.removeAttribute("data-a-hires");

      clonedImage.removeAttribute("data-srcset");

      clonedImage.removeAttribute("srcset");

      clonedImage.removeAttribute("loading");

      clonedImage.removeAttribute("decoding");

      imageMap.set(imageUrl, clonedImage.outerHTML);
    }

    /**
     * ==========================================================
     * 6. FALLBACK LẦN CUỐI
     * ==========================================================
     *
     * Có root A+ nhưng selector bên trong thay đổi mạnh,
     * hoặc candidate ban đầu bị filter hết.
     *
     * Tìm trực tiếp A+ Media Library trên document.
     */

    if (imageMap.size === 0) {
      const fallbackImages = document.querySelectorAll(
        [
          'img[src*="aplus-media-library-service-media"]',
          'img[data-src*="aplus-media-library-service-media"]',
          'img[data-a-hires*="aplus-media-library-service-media"]',
        ].join(","),
      );

      for (const image of fallbackImages) {
        if (isInsideVideoModule(image)) {
          continue;
        }

        const imageUrl = getBestImageUrl(image);

        if (!imageUrl || !isAplusMediaUrl(imageUrl) || imageMap.has(imageUrl)) {
          continue;
        }

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
    }

    /**
     * ==========================================================
     * 7. OUTPUT
     * ==========================================================
     */

    const images = Array.from(imageMap.values());

    if (images.length === 0) {
      console.warn(
        ">>> Không tìm thấy ảnh A+ Content hợp lệ. " + "Đang sử dụng rich description rỗng.",
      );

      return emptyRichDescription;
    }

    console.log(`>>> A+ Content: lấy được ${images.length} ảnh.`);

    return '<div class="description-root">' + images.join(" ") + "</div>";
  };

  /**
   * ============================================================
   * VARIANT DATA
   * ============================================================
   *
   * Đây là phần thay thế toàn bộ customization crawler cũ.
   *
   * Không còn:
   *
   * - #gc-iframe
   * - .gc-OptionChooserComponent
   * - .gc-toggle-list-option
   * - .gc-toggle-list-toggle-button
   * - .gc-swatch-label
   * - .gc-swatch-price
   * - IGNORE_TYPES
   * - PRICE_RANGE_STRATEGY
   * - removeDefaultOption
   * - Cartesian product
   * - đọc additional price từ Amazon
   */

  /**
   * Tạo variant_data trực tiếp
   * từ FURNITURE_TYPE + PRICE_TIER.
   *
   * Chỉ có 1 option type:
   *
   * Size
   *
   * Giữ nguyên cấu trúc variant_data cũ:
   *
   * [
   *   {
   *     options: [
   *       {
   *         name: "Size",
   *         value: "..."
   *       }
   *     ],
   *     additional_price: 3906
   *   }
   * ]
   *
   * @returns {Array<{
   *   options: Array<{
   *     name: string,
   *     value: string
   *   }>,
   *   additional_price: number
   * }>}
   */

  const buildVariantData = () => {
    /**
     * Validate FURNITURE_TYPE.
     */

    const furnitureConfig = SIZE_CONFIG[FURNITURE_TYPE];

    if (!furnitureConfig) {
      throw new Error(
        `Invalid FURNITURE_TYPE: ${FURNITURE_TYPE}. ` +
          'Allowed values: "standing", "corner", "floating".',
      );
    }

    /**
     * Validate PRICE_TIER.
     */

    const sizeOptions = furnitureConfig[PRICE_TIER];

    if (!sizeOptions) {
      const allowedTiers = Object.keys(furnitureConfig).join(", ");

      throw new Error(
        `Invalid PRICE_TIER "${PRICE_TIER}" ` +
          `for FURNITURE_TYPE "${FURNITURE_TYPE}". ` +
          `Allowed values: ${allowedTiers}.`,
      );
    }

    /**
     * Mỗi bảng phải có đúng 4 Size.
     */

    if (!Array.isArray(sizeOptions) || sizeOptions.length !== 4) {
      throw new Error(
        `SIZE_CONFIG.${FURNITURE_TYPE}.${PRICE_TIER} ` + "phải có chính xác 4 Size option.",
      );
    }

    /**
     * Chuyển từng Size
     * thành một variant combination.
     */

    return sizeOptions.map((sizeOption, index) => {
      const value = normalizeText(sizeOption?.value);

      const additionalPrice = Number(sizeOption?.additional_price);

      if (!value) {
        throw new Error(
          `Size option tại index ${index} ` +
            `của ${FURNITURE_TYPE}/${PRICE_TIER} ` +
            "không có value hợp lệ.",
        );
      }

      if (!Number.isFinite(additionalPrice)) {
        throw new Error(
          `Size option "${value}" ` +
            `của ${FURNITURE_TYPE}/${PRICE_TIER} ` +
            "không có additional_price hợp lệ.",
        );
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

  /**
   * ============================================================
   * PRODUCT TITLE
   * ============================================================
   */

  try {
    const productTitleElement = document.getElementById("productTitle");

    if (!productTitleElement) {
      throw new Error('Không tìm thấy element "#productTitle".');
    }

    const productTitle = normalizeText(productTitleElement.textContent);

    if (!productTitle) {
      throw new Error("Element product title không có nội dung.");
    }

    product.product_title = productTitle;
  } catch (error) {
    warnFieldError("product_title", error);
  }

  /**
   * ============================================================
   * PRODUCT DESCRIPTION
   * ============================================================
   */

  try {
    const productDescription = Array.from(
      document.querySelectorAll(
        "ul.a-unordered-list.a-vertical.a-spacing-mini " + "> li .a-list-item",
      ),
    )
      .map((element) => normalizeText(element.textContent))
      .filter(Boolean);

    if (productDescription.length === 0) {
      throw new Error("Không tìm thấy mô tả sản phẩm hợp lệ.");
    }

    product.product_description = productDescription;
  } catch (error) {
    warnFieldError("product_description", error);
  }

  /**
   * ============================================================
   * PRODUCT IMAGES
   * ============================================================
   */

  try {
    const productImages = await extractProductImages();

    if (productImages.length === 0) {
      throw new Error("Danh sách ảnh sản phẩm rỗng.");
    }

    product.product_images = productImages;
  } catch (error) {
    warnFieldError("product_images", error);
  }

  /**
   * ============================================================
   * BASE PRICE
   * ============================================================
   */

  try {
    const basePrice = getBasePrice();

    if (!Number.isFinite(basePrice)) {
      throw new Error("Base price không phải số hợp lệ.");
    }

    product.base_price = basePrice;
  } catch (error) {
    warnFieldError("base_price", error);
  }

  /**
   * ============================================================
   * VARIANT DATA
   * ============================================================
   */

  try {
    const variantData = buildVariantData();

    if (variantData.length === 0) {
      throw new Error("Danh sách variant data rỗng.");
    }

    product.variant_data = variantData;
  } catch (error) {
    warnFieldError("variant_data", error);
  }

  /**
   * ============================================================
   * PRODUCT RICH DESCRIPTION
   * ============================================================
   */

  try {
    product.product_rich_description = await extractProductRichDescription();
  } catch (error) {
    console.warn(">>> Có lỗi khi lấy A+ Content. " + "Đang sử dụng rich description rỗng.", error);

    product.product_rich_description = '<div class="description-root"></div>';
  }

  /**
   * ============================================================
   * AMAZON PRODUCT LINK
   * ============================================================
   */

  try {
    const amazonLink = normalizeText(window.location.href);

    if (!amazonLink) {
      throw new Error("Không thể đọc window.location.href.");
    }

    product.product_amazon_link = amazonLink;
  } catch (error) {
    warnFieldError("product_amazon_link", error);
  }

  /**
   * ============================================================
   * OUTPUT
   * ============================================================
   */

  const output = {
    product,
  };

  const json = JSON.stringify(output, null, 2);

  /**
   * Chỉ console.log đúng một lần.
   */

  console.log(json);

  /**
   * Hiển thị nút Copy JSON.
   *
   * Không auto-copy vì Clipboard API
   * có thể yêu cầu thao tác trực tiếp
   * từ người dùng.
   */

  showCopyJsonButton(json);

  return output;
})();
