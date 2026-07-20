/**
 * Danh sách customization type cần bỏ qua.
 * So sánh không phân biệt chữ hoa/chữ thường.
 *
 * @type {string[]}
 */
const IGNORE_TYPES = [
  "Customization Confirmation",
  "Note to seller (Optional)",
  "Other requirements",
  "Review Photo Before Final Finish",
];

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
   * Cách xử lý giá dạng khoảng, ví dụ "$10.00 - $20.00".
   *
   * - "error": dừng phần lấy customization
   * - "min": lấy mức giá thấp nhất
   * - "max": lấy mức giá cao nhất
   *
   * @type {"error" | "min" | "max"}
   */
  const PRICE_RANGE_STRATEGY = "error";

  /**
   * Thời gian tối đa chờ iframe và customization render.
   *
   * @type {number}
   */
  const DOM_WAIT_TIMEOUT_MS = 30000;

  /**
   * Thời gian chờ sau khi click nút mở rộng option.
   *
   * @type {number}
   */
  const EXPAND_WAIT_MS = 1000;

  const IFRAME_SELECTOR = "#gc-iframe";
  const TYPE_SELECTOR = ".gc-OptionChooserComponent";
  const OPTION_SELECTOR = '.gc-toggle-list-option[role="radio"]';

  /**
   * Tất cả field mặc định là null.
   *
   * Field chỉ được gán giá trị khi lấy dữ liệu thành công.
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
   * Chuẩn hóa text để so sánh không phân biệt chữ hoa/chữ thường.
   *
   * @param {unknown} value
   * @returns {string}
   */
  const normalizeForComparison = (value) => normalizeText(value).toLocaleLowerCase();

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
   * Chuyển lỗi thành message.
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
   * Không thay đổi giá trị của field.
   *
   * @param {keyof typeof product} field
   * @param {unknown} error
   */
  const warnFieldError = (field, error) => {
    console.warn(`>>> Không thể lấy field "${field}". Field này được giữ nguyên là null.`, {
      field,
      error: getErrorMessage(error),
    });
  };

  /**
   * Chờ condition trả về giá trị truthy.
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
   * Parse giá từ một Amazon .a-price element.
   *
   * Ví dụ:
   *
   * <span class="a-price">
   *   <span class="a-price-whole">14,995.</span>
   *   <span class="a-price-fraction">65</span>
   * </span>
   *
   * Kết quả:
   * 14995.65
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
   * Ưu tiên:
   * 1. Giá chính trên trang sản phẩm.
   * 2. Giá trong footer của customization form.
   *
   * @returns {number}
   */
  const getBasePrice = () => {
    const mainPriceElement = document.querySelector(
      "#corePriceDisplay_desktop_feature_div .a-price",
    );

    if (mainPriceElement) {
      return parseAmazonPriceElement(mainPriceElement);
    }

    const customizationPriceElement = document.querySelector(
      '#gc-desktop-footer-wrapper .a-price[data-a-size="xl"][data-a-color="base"]',
    );

    if (customizationPriceElement) {
      return parseAmazonPriceElement(customizationPriceElement);
    }

    throw new Error("Không tìm thấy giá ở cả khu vực giá chính và customization footer.");
  };

  /**
   * Lấy URL ảnh lớn hiện tại trong Amazon image viewer.
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
   * Lấy danh sách thumbnail ảnh hợp lệ.
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
   * Click lần lượt từng thumbnail và lấy URL ảnh lớn.
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

            /*
             * Thumbnail đầu tiên có thể đã được chọn sẵn,
             * vì vậy URL ảnh lớn không nhất thiết phải thay đổi.
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
          console.warn(`>>> Không lấy được URL ảnh lớn của thumbnail "${thumbnailId}".`);

          continue;
        }

        if (!links.includes(largeImageUrl)) {
          links.push(largeImageUrl);
        }
      } catch (error) {
        console.warn(`>>> Có lỗi khi xử lý thumbnail "${thumbnailId}".`, error);
      }

      await sleep(300);
    }

    if (links.length === 0) {
      throw new Error("Không lấy được URL ảnh lớn hợp lệ từ bất kỳ thumbnail nào.");
    }

    return links;
  };

  /**
   * Lấy A+ Content và ghép các thẻ img vào description-root.
   *
   * @returns {string}
   */
  /**
   * Lấy A+ Content và ghép các thẻ img vào description-root.
   *
   * Nếu không tìm thấy A+ Content hoặc không có ảnh,
   * trả về description-root rỗng.
   *
   * @returns {string}
   */
  const extractProductRichDescription = () => {
    const emptyRichDescription = '<div class="description-root"></div>';

    const aplusFeature = document.getElementById("aplus_feature_div");

    if (!aplusFeature) {
      console.warn(
        '>>> Không tìm thấy element "#aplus_feature_div". ' + "Đang sử dụng rich description rỗng.",
      );

      return emptyRichDescription;
    }

    const contentWrapper = aplusFeature.querySelector(".aplus-v2 .aplus-content-wrapper");

    if (!contentWrapper) {
      console.warn(
        ">>> Không tìm thấy A+ Content wrapper. " + "Đang sử dụng rich description rỗng.",
      );

      return emptyRichDescription;
    }

    const aplusImages = contentWrapper.querySelectorAll(".aplus-module-wrapper img");

    if (aplusImages.length === 0) {
      console.warn(
        ">>> Không tìm thấy ảnh trong A+ Content. " + "Đang sử dụng rich description rỗng.",
      );

      return emptyRichDescription;
    }

    const htmlString = Array.from(aplusImages)
      .map((image) => image.outerHTML)
      .join(" ");

    return `<div class="description-root">${htmlString}</div>`;
  };

  /**
   * Thông tin execution context hiện tại.
   */
  const getCurrentContextInfo = () => {
    let frameId = "top";

    try {
      frameId = window.frameElement?.id || "top";
    } catch {
      frameId = "unknown";
    }

    return {
      current_url: location.href,
      current_origin: location.origin,
      current_frame_id: frameId,
      customization_count_in_current_document: document.querySelectorAll(TYPE_SELECTOR).length,
      iframe_exists_in_current_document: Boolean(document.querySelector(IFRAME_SELECTOR)),
    };
  };

  /**
   * Kiểm tra type có phải type Size hay không.
   *
   * Match:
   * - Size
   * - Choose Size
   * - Custom Size
   * - CustomSize
   * - Mattress Size Options
   *
   * Không match:
   * - Sized Rug
   * - Oversized Design
   *
   * @param {string} normalizedType
   * @returns {boolean}
   */
  const isSizeType = (normalizedType) => {
    const compactType = normalizedType.replace(/[\s_-]+/g, "");

    return /\bsize\b/i.test(normalizedType) || compactType.includes("customsize");
  };

  /**
   * Tìm document chứa customization form.
   *
   * Hỗ trợ:
   * - Console đang chạy trực tiếp trong iframe.
   * - Console đang chạy ở trang cha.
   *
   * @param {{
   *   timeoutMs?: number,
   *   iframeSelector?: string,
   *   contentSelector?: string
   * }} options
   * @returns {Promise<Document>}
   */
  const getCustomizationDocument = async ({
    timeoutMs = DOM_WAIT_TIMEOUT_MS,
    iframeSelector = IFRAME_SELECTOR,
    contentSelector = TYPE_SELECTOR,
  } = {}) => {
    const startedAt = Date.now();

    let lastError = null;
    let lastIframeInfo = null;

    while (Date.now() - startedAt < timeoutMs) {
      /*
       * Trường hợp Console đang chạy trực tiếp trong iframe.
       */
      const currentDocumentComponents = document.querySelectorAll(contentSelector);

      if (currentDocumentComponents.length > 0) {
        return document;
      }

      /*
       * Trường hợp Console đang chạy ở trang cha.
       */
      const iframeElement = document.querySelector(iframeSelector);

      if (iframeElement) {
        lastIframeInfo = {
          id: iframeElement.id || null,
          name: iframeElement.name || null,
          src: iframeElement.src || null,
        };

        /*
         * Đưa iframe vào viewport để kích hoạt lazy loading.
         */
        try {
          iframeElement.scrollIntoView({
            block: "center",
            inline: "nearest",
          });
        } catch {
          // Không ảnh hưởng tới việc truy cập iframe.
        }

        try {
          const iframeDocument =
            iframeElement.contentDocument || iframeElement.contentWindow?.document;

          if (iframeDocument) {
            const iframeComponents = iframeDocument.querySelectorAll(contentSelector);

            if (iframeComponents.length > 0) {
              return iframeDocument;
            }
          }
        } catch (error) {
          /*
           * Iframe có thể đang chuyển từ about:blank
           * sang URL customization thật.
           */
          lastError = error;
        }
      }

      await sleep(200);
    }

    const iframeList = [...document.querySelectorAll("iframe")].map((iframe, index) => ({
      index,
      id: iframe.id || null,
      name: iframe.name || null,
      src: iframe.src || null,
    }));

    throw new Error(
      `Không lấy được customization document sau ${timeoutMs}ms. ` +
        `Context: ${JSON.stringify(getCurrentContextInfo())}. ` +
        `Iframe gần nhất: ${JSON.stringify(lastIframeInfo)}. ` +
        `Danh sách iframe: ${JSON.stringify(iframeList)}. ` +
        `Lỗi gần nhất: ${lastError?.message || "không có"}.`,
    );
  };

  /**
   * Lấy tên customization type và loại bỏ dấu "*".
   *
   * @param {Element} typeElement
   * @returns {string}
   */
  const getCustomizationTypeName = (typeElement) => {
    const labelElement = typeElement.querySelector(".gc-component-label");

    if (!labelElement) {
      return "";
    }

    const clonedLabel = labelElement.cloneNode(true);

    clonedLabel
      .querySelectorAll(".gc-component-label-required")
      .forEach((element) => element.remove());

    return normalizeText(clonedLabel.textContent);
  };

  /**
   * Trích xuất các giá trị số trong chuỗi giá.
   *
   * Ví dụ:
   * "+ $4,000.00"      => [4000]
   * "$10.00 - $20.00" => [10, 20]
   *
   * @param {string} priceText
   * @returns {number[]}
   */
  const extractPriceNumbers = (priceText) => {
    const matches = normalizeText(priceText).match(/\d[\d,]*(?:\.\d+)?/g) ?? [];

    return matches.map((value) => Number(value.replace(/,/g, ""))).filter(Number.isFinite);
  };

  /**
   * Parse additional price.
   *
   * @param {string} priceText
   * @param {{
   *   type: string,
   *   option: string
   * }} context
   * @returns {number}
   */
  const parseAdditionalPrice = (priceText, { type, option }) => {
    const normalizedPrice = normalizeText(priceText);

    if (!normalizedPrice) {
      return 0;
    }

    const prices = extractPriceNumbers(normalizedPrice);

    if (prices.length === 0) {
      throw new Error(
        `Không thể parse giá "${normalizedPrice}" ` +
          `của option "${option}" trong type "${type}".`,
      );
    }

    if (prices.length === 1) {
      const isNegative = /^-\s*\$?/.test(normalizedPrice) || /\(\s*\$?[\d,]/.test(normalizedPrice);

      return isNegative ? -prices[0] : prices[0];
    }

    if (PRICE_RANGE_STRATEGY === "min") {
      return Math.min(...prices);
    }

    if (PRICE_RANGE_STRATEGY === "max") {
      return Math.max(...prices);
    }

    throw new Error(
      `Phát hiện nhiều mức giá trong "${normalizedPrice}" ` +
        `của option "${option}" thuộc type "${type}". ` +
        'Đổi PRICE_RANGE_STRATEGY thành "min" hoặc "max" nếu cần.',
    );
  };

  /**
   * Đọc additional price của option.
   *
   * Ưu tiên:
   * 1. .gc-swatch-price
   * 2. Giá ở cuối aria-label
   *
   * @param {Element} optionElement
   * @param {string} type
   * @param {string} optionValue
   */
  const getOptionPrice = (optionElement, type, optionValue) => {
    const priceElement = optionElement.querySelector(".gc-swatch-price");

    if (priceElement) {
      const rawPriceText = normalizeText(priceElement.textContent);

      return {
        additionalPrice: parseAdditionalPrice(rawPriceText, {
          type,
          option: optionValue,
        }),
        hasExplicitPrice: true,
        rawPriceText,
      };
    }

    const ariaLabel = normalizeText(optionElement.getAttribute("aria-label"));

    /*
     * Match:
     * ", + $850.00"
     * ", - $100.00"
     * ", + $10.00 - $20.00"
     */
    const pricePartMatch = ariaLabel.match(
      /(?:,\s*)?([+-]\s*\$?\s*\d[\d,]*(?:\.\d+)?(?:\s*[-–—]\s*\$?\s*\d[\d,]*(?:\.\d+)?)?)\s*$/,
    );

    if (!pricePartMatch) {
      return {
        additionalPrice: 0,
        hasExplicitPrice: false,
        rawPriceText: "",
      };
    }

    const rawPriceText = normalizeText(pricePartMatch[1]);

    return {
      additionalPrice: parseAdditionalPrice(rawPriceText, {
        type,
        option: optionValue,
      }),
      hasExplicitPrice: true,
      rawPriceText,
    };
  };

  /**
   * Làm tròn tiền đến 2 chữ số thập phân.
   *
   * @param {number} value
   * @returns {number}
   */
  const roundPrice = (value) => Math.round((value + Number.EPSILON) * 100) / 100;

  /**
   * Bỏ option mặc định của type Size.
   *
   * Quy tắc:
   * 1. Nếu chỉ có một option không tăng giá, loại option đó.
   * 2. Nếu có nhiều option không tăng giá và option đầu DOM
   *    nằm trong số đó, loại option đầu DOM.
   * 3. Nếu không xác định được, dừng phần lấy variant.
   *
   * @param {string} type
   * @param {Array<{
   *   value: string,
   *   additional_price: number,
   *   has_explicit_price: boolean,
   *   raw_price_text: string,
   *   dom_index: number
   * }>} options
   */
  const removeDefaultSizeOption = (type, options) => {
    if (options.length <= 1) {
      throw new Error(
        `Type size "${type}" chỉ có ${options.length} option. ` +
          "Không thể bỏ option mặc định mà vẫn tạo tổ hợp hợp lệ.",
      );
    }

    const zeroPriceOptions = options.filter(
      (option) => option.additional_price === 0 && !option.has_explicit_price,
    );

    let optionToRemove = null;

    if (zeroPriceOptions.length === 1) {
      optionToRemove = zeroPriceOptions[0];
    } else if (
      zeroPriceOptions.length > 1 &&
      zeroPriceOptions.some((option) => option.dom_index === 0)
    ) {
      optionToRemove = zeroPriceOptions.find((option) => option.dom_index === 0) || null;

      console.warn(
        `>>> Type size "${type}" có nhiều option không tăng giá. ` +
          `Đang loại option đầu tiên trong DOM.`,
        {
          removed_option: optionToRemove,
          zero_price_options: zeroPriceOptions,
        },
      );
    } else {
      throw new Error(
        `Không thể xác định an toàn option mặc định ` +
          `cần bỏ trong type size "${type}". ` +
          `Các option: ${JSON.stringify(
            options.map((option) => ({
              value: option.value,
              additional_price: option.additional_price,
              has_explicit_price: option.has_explicit_price,
              raw_price_text: option.raw_price_text,
              dom_index: option.dom_index,
            })),
          )}`,
      );
    }

    if (!optionToRemove) {
      throw new Error(`Không xác định được option mặc định của type size "${type}".`);
    }

    return options.filter((option) => option !== optionToRemove);
  };

  /**
   * Lấy toàn bộ Cartesian product của customization options.
   *
   * @returns {Promise<Array<{
   *   options: string[],
   *   additional_price: number
   * }>>}
   */
  const extractVariantData = async () => {
    const customizationDocument = await getCustomizationDocument();

    /*
     * Mở tất cả danh sách option đang bị thu gọn.
     */
    const collapsedButtons = [
      ...customizationDocument.querySelectorAll(
        '.gc-toggle-list-toggle-button[aria-expanded="false"]',
      ),
    ];

    if (collapsedButtons.length > 0) {
      collapsedButtons.forEach((button, index) => {
        try {
          button.click();
        } catch (error) {
          console.warn(`>>> Không thể mở danh sách customization tại index ${index}.`, error);
        }
      });

      await sleep(EXPAND_WAIT_MS);
    }

    /*
     * Query lại sau khi expand vì Amazon có thể
     * render thêm option.
     */
    const typeElements = [...customizationDocument.querySelectorAll(TYPE_SELECTOR)];

    if (typeElements.length === 0) {
      throw new Error(`Không tìm thấy "${TYPE_SELECTOR}" trong customization iframe.`);
    }

    const normalizedIgnoreTypes = IGNORE_TYPES.map((type) => normalizeForComparison(type)).filter(
      Boolean,
    );

    const customizationTypes = typeElements
      .map((typeElement, typeIndex) => {
        const type = getCustomizationTypeName(typeElement);

        const normalizedType = normalizeForComparison(type);

        if (!type) {
          console.warn(
            `>>> Bỏ customization component tại index ${typeIndex} vì không tìm thấy tên type.`,
          );

          return null;
        }

        /*
         * Ignore nhiều type, không phân biệt chữ hoa/chữ thường.
         */
        if (normalizedIgnoreTypes.includes(normalizedType)) {
          return null;
        }

        const optionElements = [...typeElement.querySelectorAll(OPTION_SELECTOR)];

        if (optionElements.length === 0) {
          console.warn(`>>> Không tìm thấy option trong customization type "${type}".`);

          return null;
        }

        let options = optionElements
          .filter((optionElement) => optionElement.getAttribute("aria-disabled") !== "true")
          .map((optionElement, domIndex) => {
            try {
              const value =
                normalizeText(optionElement.querySelector(".gc-swatch-label")?.textContent) ||
                normalizeText(optionElement.getAttribute("aria-label"));

              if (!value) {
                console.warn(
                  `>>> Bỏ option tại index ${domIndex} trong type "${type}" vì không có value.`,
                );

                return null;
              }

              const { additionalPrice, hasExplicitPrice, rawPriceText } = getOptionPrice(
                optionElement,
                type,
                value,
              );

              return {
                value,
                additional_price: additionalPrice,
                has_explicit_price: hasExplicitPrice,
                raw_price_text: rawPriceText,
                dom_index: domIndex,
              };
            } catch (error) {
              console.warn(
                `>>> Không thể đọc option tại index ${domIndex} trong type "${type}".`,
                error,
              );

              return null;
            }
          })
          .filter(Boolean);

        /*
         * Loại option trùng do DOM render lặp.
         */
        options = Array.from(
          new Map(
            options.map((option) => [
              [normalizeForComparison(option.value), option.additional_price].join("__"),
              option,
            ]),
          ).values(),
        );

        /*
         * Xử lý type Size.
         */
        if (isSizeType(normalizedType)) {
          options = removeDefaultSizeOption(type, options);
        }

        if (options.length === 0) {
          console.warn(`>>> Bỏ customization type "${type}" vì không còn option hợp lệ.`);

          return null;
        }

        return {
          type,
          options,
        };
      })
      .filter(Boolean);

    if (customizationTypes.length === 0) {
      throw new Error("Không còn customization type hợp lệ sau khi xử lý.");
    }

    /*
     * Tạo Cartesian product.
     */
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
              currentCombination.additional_price + option.additional_price,
            ),
          })),
        ),
      [
        {
          options: [],
          additional_price: 0,
        },
      ],
    );

    if (combinations.length === 0) {
      throw new Error("Không tạo được customization combination nào.");
    }

    return combinations.map((combination) => ({
      options: combination.options,
      additional_price: combination.additional_price,
    }));
  };

  /**
   * Lấy product title.
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
   * Lấy product description.
   */
  try {
    const productDescription = Array.from(
      document.querySelectorAll("ul.a-unordered-list.a-vertical.a-spacing-mini > li .a-list-item"),
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
   * Lấy product images.
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
   * Lấy base price.
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
   * Lấy variant data.
   */
  try {
    const variantData = await extractVariantData();

    if (variantData.length === 0) {
      throw new Error("Danh sách variant data rỗng.");
    }

    product.variant_data = variantData;
  } catch (error) {
    warnFieldError("variant_data", error);
  }

  /**
   * Lấy product rich description.
   */
  try {
    product.product_rich_description = extractProductRichDescription();
  } catch (error) {
    console.warn(">>> Có lỗi khi lấy A+ Content. " + "Đang sử dụng rich description rỗng.", error);

    product.product_rich_description = '<div class="description-root"></div>';
  }

  /**
   * Lấy Amazon product link.
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
   * Tạo JSON cuối cùng.
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
   * Hiển thị nút để người dùng chủ động click copy.
   *
   * Clipboard API yêu cầu thao tác trực tiếp từ người dùng,
   * vì vậy không tự động copy sau chuỗi xử lý async dài.
   */
  showCopyJsonButton(json);

  return output;
})();
