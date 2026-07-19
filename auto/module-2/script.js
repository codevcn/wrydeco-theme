try {
  console.log("======================================");
  console.log("======================================");
  console.log("======================================");
  console.log("Tiêu đề sản phẩm:");
  console.log("======================================");
  console.log(document.getElementById("productTitle").textContent.trim());
  console.log("======================================");
  console.log("======================================");
  console.log("======================================");
} catch (error) {
  console.warn(">>> Không tìm thấy tiêu đề sản phẩm.");
}

try {
  const productDescription = Array.from(
    document.querySelectorAll("ul.a-unordered-list.a-vertical.a-spacing-mini > li .a-list-item"),
  )
    .map((element) => element.textContent.replace(/\s+/g, " ").trim())
    .filter(Boolean);

  const result = {
    product_description: productDescription,
  };

  console.log("======================================");
  console.log("======================================");
  console.log("======================================");
  console.log("Mô tả sản phẩm:");
  console.log("======================================");
  console.log(result);
  console.log("======================================");
  console.log("======================================");
  console.log("======================================");
} catch (error) {
  console.warn(">>> Không tìm thấy mô tả sản phẩm.");
  throw error;
}

(async () => {
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

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

  const getLargeImageUrl = () => {
    const image = document.querySelector("#ivLargeImage img");

    if (!image) {
      return null;
    }

    return image.currentSrc || image.src || image.getAttribute("src") || null;
  };

  const getThumbnailItems = () => {
    return [...document.querySelectorAll('#ivThumbs .ivThumb[id^="ivImage_"]')].filter(
      (thumbnail) => {
        return (
          !thumbnail.classList.contains("placeholder") && thumbnail.querySelector(".ivThumbImage")
        );
      },
    );
  };

  const thumbnailItems = getThumbnailItems();

  if (thumbnailItems.length === 0) {
    console.warn("Không tìm thấy thumbnail nào trong #ivThumbs.");

    return {
      links: [],
    };
  }

  console.log(`Tìm thấy ${thumbnailItems.length} thumbnail.`);

  const links = [];

  for (let index = 0; index < thumbnailItems.length; index++) {
    const thumbnail = thumbnailItems[index];
    const thumbnailId = thumbnail.id || `thumbnail-${index}`;

    console.log(`Đang xử lý ${index + 1}/${thumbnailItems.length}: ${thumbnailId}`);

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
         * Với thumbnail đầu tiên, URL ảnh lớn có thể không đổi vì
         * ảnh đó đã được chọn sẵn. Vì vậy chỉ cần thumbnail được
         * selected hoặc ảnh lớn đã đổi.
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
      console.warn(`Không lấy được ảnh lớn của ${thumbnailId}.`);

      continue;
    }

    if (!links.includes(largeImageUrl)) {
      links.push(largeImageUrl);
      console.log(largeImageUrl);
    } else {
      console.log(`Bỏ qua URL trùng: ${largeImageUrl}`);
    }

    await sleep(300);
  }

  const result = {
    product_images: links,
  };

  console.log(`Hoàn tất: lấy được ${links.length}/${thumbnailItems.length} URL ảnh.`);

  console.log("======================================");
  console.log("======================================");
  console.log("======================================");
  console.log("Danh sách URL ảnh sản phẩm:");
  console.log("======================================");
  console.log(result);
  console.log(JSON.stringify(result, null, 2));
  console.log("======================================");
  console.log("======================================");
  console.log("======================================");

  try {
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));

    console.log("Đã copy kết quả JSON vào clipboard.");
  } catch {
    console.warn("Không thể tự động copy. Hãy copy kết quả trong Console.");
  }

  return result;
})().catch((error) => {
  console.error("Không thể lấy URL ảnh sản phẩm:", error);
});

try {
  const aplusImages = document
    .getElementById("aplus_feature_div")
    .querySelector(".aplus-v2 .aplus-content-wrapper")
    .querySelectorAll(".aplus-module-wrapper img");
  const htmlString = Array.from(aplusImages)
    .map((node) => node.outerHTML)
    .join(" ");
  const aplus_content = `<div class="description-root">${htmlString}</div>`;
  console.log("======================================");
  console.log("======================================");
  console.log("======================================");
  console.log("A+ Content:");
  console.log("======================================");
  console.log(aplus_content);
  console.log("======================================");
  console.log("======================================");
  console.log("======================================\n\n");
} catch (error) {
  console.warn(">>> Không tìm thấy A+ Content.");
}

try {
  const result = {
    amazon_link: window.location.href,
  };

  console.log("======================================");
  console.log("======================================");
  console.log("======================================");
  console.log("Link sản phẩm:");
  console.log("======================================");
  console.log(result);
  console.log("======================================");
  console.log("======================================");
  console.log("======================================");
} catch (error) {
  console.warn(">>> Không tìm thấy link sản phẩm.");
}

try {
  const priceElement = document.querySelector(
    '#gc-desktop-footer-wrapper .a-price[data-a-size="xl"][data-a-color="base"]',
  );

  if (!priceElement) {
    throw new Error("Không tìm thấy phần tử base price.");
  }

  const wholeText = priceElement.querySelector(".a-price-whole")?.textContent;
  const fractionText = priceElement.querySelector(".a-price-fraction")?.textContent;

  const whole = String(wholeText ?? "").replace(/[^\d]/g, "");

  const fraction = String(fractionText ?? "00")
    .replace(/[^\d]/g, "")
    .padEnd(2, "0")
    .slice(0, 2);

  if (!whole) {
    throw new Error("Không thể đọc phần nguyên của base price.");
  }

  const basePrice = Number(`${whole}.${fraction}`);

  const result = {
    base_price: basePrice,
  };

  console.log("======================================");
  console.log("======================================");
  console.log("======================================");
  console.log("Giá gốc của sản phẩm:");
  console.log("======================================");
  console.log(result);
  console.log("======================================");
  console.log("======================================");
  console.log("======================================");
} catch (error) {
  console.warn(">>> Không tìm thấy base price.");
}
(async () => {
  /**
   * Customization type cần bỏ qua.
   * So sánh không phân biệt chữ hoa/chữ thường.
   *
   * @type {string}
   */
  const IGNORE_TYPE = "Customization Confirmation";

  /**
   * Cách xử lý giá dạng khoảng, ví dụ "$10.00 - $20.00".
   *
   * - "error": dừng script
   * - "min": lấy mức thấp nhất
   * - "max": lấy mức cao nhất
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
   * Thời gian chờ sau khi click "See all options".
   *
   * @type {number}
   */
  const EXPAND_WAIT_MS = 1000;

  const IFRAME_SELECTOR = "#gc-iframe";
  const TYPE_SELECTOR = ".gc-OptionChooserComponent";
  const OPTION_SELECTOR = '.gc-toggle-list-option[role="radio"]';

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
   * Chuẩn hóa để so sánh không phân biệt hoa thường.
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
   * Tìm document của customization form.
   *
   * Hỗ trợ:
   * - Console đang chạy trực tiếp trong iframe
   * - Console đang chạy ở trang cha
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
      /**
       * Trường hợp document hiện tại đã chính là DOM
       * của customization iframe.
       */
      const currentDocumentComponents = document.querySelectorAll(contentSelector);

      if (currentDocumentComponents.length > 0) {
        console.log(
          `Đang sử dụng document hiện tại. Tìm thấy ${currentDocumentComponents.length} customization component.`,
        );

        return document;
      }

      /**
       * Trường hợp Console đang ở trang cha.
       */
      const iframeElement = document.querySelector(iframeSelector);

      if (iframeElement) {
        lastIframeInfo = {
          id: iframeElement.id || null,
          name: iframeElement.name || null,
          src: iframeElement.src || null,
        };

        /**
         * Kích hoạt lazy loading bằng cách đưa iframe
         * vào vùng nhìn thấy.
         */
        try {
          iframeElement.scrollIntoView({
            block: "center",
            inline: "nearest",
          });
        } catch {
          // Không ảnh hưởng tới việc đọc iframe.
        }

        try {
          const iframeDocument =
            iframeElement.contentDocument || iframeElement.contentWindow?.document;

          if (iframeDocument) {
            const iframeComponents = iframeDocument.querySelectorAll(contentSelector);

            if (iframeComponents.length > 0) {
              console.log(
                `Đã truy cập #gc-iframe và tìm thấy ${iframeComponents.length} customization component.`,
              );

              return iframeDocument;
            }
          }
        } catch (error) {
          lastError = error;

          /**
           * Không throw ngay vì iframe có thể đang chuyển
           * từ about:blank sang URL thật.
           */
        }
      }

      await sleep(200);
    }

    console.table(
      [...document.querySelectorAll("iframe")].map((iframe, index) => ({
        index,
        id: iframe.id || null,
        name: iframe.name || null,
        src: iframe.src || null,
      })),
    );

    throw new Error(
      `Không lấy được customization document sau ${timeoutMs}ms. ` +
        `Context: ${JSON.stringify(getCurrentContextInfo())}. ` +
        `Iframe gần nhất: ${JSON.stringify(lastIframeInfo)}. ` +
        `Lỗi gần nhất: ${lastError?.message || "không có"}. ` +
        "Nếu iframe khác origin hoặc Console context không đúng, hãy chuyển execution context sang gc-iframe rồi chạy lại.",
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

    const warningMessage =
      `Phát hiện nhiều mức giá trong "${normalizedPrice}" ` +
      `của option "${option}" thuộc type "${type}".`;

    if (PRICE_RANGE_STRATEGY === "min") {
      const selectedPrice = Math.min(...prices);

      console.warn(`${warningMessage} Đang lấy giá nhỏ nhất: ${selectedPrice}.`);

      return selectedPrice;
    }

    if (PRICE_RANGE_STRATEGY === "max") {
      const selectedPrice = Math.max(...prices);

      console.warn(`${warningMessage} Đang lấy giá lớn nhất: ${selectedPrice}.`);

      return selectedPrice;
    }

    throw new Error(
      `${warningMessage} Script đã dừng để tránh mất dữ liệu. ` +
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

    /**
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
   * Không dùng options.slice(1) một cách âm thầm.
   *
   * Quy tắc:
   * 1. Nếu chỉ có một option không tăng giá,
   *    loại option đó.
   * 2. Nếu có nhiều option không tăng giá và option
   *    đầu DOM nằm trong số đó, loại option đầu DOM
   *    và ghi cảnh báo.
   * 3. Nếu không xác định được, dừng script.
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
      optionToRemove = zeroPriceOptions.find((option) => option.dom_index === 0);

      console.warn(
        `Type size "${type}" có nhiều option không tăng giá. ` +
          `Đang loại option đầu tiên trong DOM: "${optionToRemove.value}".`,
        zeroPriceOptions,
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

    console.warn(`Đã loại option mặc định của type size "${type}":`, {
      value: optionToRemove.value,
      additional_price: optionToRemove.additional_price,
      dom_index: optionToRemove.dom_index,
    });

    return options.filter((option) => option !== optionToRemove);
  };

  console.log("Execution context ban đầu:", getCurrentContextInfo());

  /**
   * Tìm document thực sự chứa customization form.
   */
  const customizationDocument = await getCustomizationDocument();

  /**
   * Mở tất cả nút "See all ... options".
   *
   * Quan trọng: sử dụng customizationDocument,
   * không dùng document của trang cha.
   */
  const collapsedButtons = [
    ...customizationDocument.querySelectorAll(
      '.gc-toggle-list-toggle-button[aria-expanded="false"]',
    ),
  ];

  if (collapsedButtons.length > 0) {
    console.log(`Đang mở ${collapsedButtons.length} danh sách option bị thu gọn.`);

    collapsedButtons.forEach((button) => {
      try {
        button.click();
      } catch (error) {
        console.warn("Không thể click nút mở rộng:", button, error);
      }
    });

    await sleep(EXPAND_WAIT_MS);
  }

  /**
   * Query lại sau khi expand vì Amazon có thể
   * render thêm option.
   */
  const typeElements = [...customizationDocument.querySelectorAll(TYPE_SELECTOR)];

  if (typeElements.length === 0) {
    throw new Error(
      `Không tìm thấy "${TYPE_SELECTOR}" trong customization iframe. ` +
        "DOM có thể vừa thay đổi hoặc iframe vừa reload.",
    );
  }

  console.log(`Đã tìm thấy ${typeElements.length} customization type.`);

  const normalizedIgnoreType = normalizeForComparison(IGNORE_TYPE);

  const ignoredTypes = [];
  const emptyTypes = [];
  const detectedTypes = [];
  const invalidComponents = [];

  /**
   * Đọc từng customization type.
   */
  const customizationTypes = typeElements
    .map((typeElement, typeIndex) => {
      const type = getCustomizationTypeName(typeElement);

      const normalizedType = normalizeForComparison(type);

      if (!type) {
        invalidComponents.push({
          type_index: typeIndex,
          reason: "Không tìm thấy tên type",
        });

        console.warn(
          `Customization component tại index ${typeIndex} không có tên hợp lệ.`,
          typeElement,
        );

        return null;
      }

      detectedTypes.push(type);

      /**
       * Ignore type không phân biệt hoa thường.
       */
      if (normalizedIgnoreType && normalizedType === normalizedIgnoreType) {
        ignoredTypes.push(type);
        return null;
      }

      const optionElements = [...typeElement.querySelectorAll(OPTION_SELECTOR)];

      if (optionElements.length === 0) {
        console.warn(
          `Không tìm thấy option theo selector ` + `"${OPTION_SELECTOR}" trong type "${type}".`,
          typeElement,
        );
      }

      let options = optionElements
        .filter((optionElement) => optionElement.getAttribute("aria-disabled") !== "true")
        .map((optionElement, domIndex) => {
          const value =
            normalizeText(optionElement.querySelector(".gc-swatch-label")?.textContent) ||
            normalizeText(optionElement.getAttribute("aria-label"));

          if (!value) {
            console.warn(`Bỏ option không có value trong type "${type}".`, optionElement);

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
        })
        .filter(Boolean);

      /**
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

      /**
       * Xử lý type Size.
       */
      if (isSizeType(normalizedType)) {
        options = removeDefaultSizeOption(type, options);
      }

      /**
       * Theo dõi type bị rỗng.
       */
      if (options.length === 0) {
        emptyTypes.push(type);
        return null;
      }

      return {
        type,
        options,
      };
    })
    .filter(Boolean);

  /**
   * Cảnh báo khi IGNORE_TYPE không match.
   */
  if (normalizedIgnoreType && ignoredTypes.length === 0) {
    console.warn(`IGNORE_TYPE="${IGNORE_TYPE}" không khớp customization type nào.`, {
      detected_types: detectedTypes,
    });
  }

  /**
   * Cảnh báo type bị bỏ vì không còn option.
   */
  if (emptyTypes.length > 0) {
    console.warn("Các customization type bị bỏ vì không còn option hợp lệ:", emptyTypes);
  }

  /**
   * Cảnh báo component không đọc được tên.
   */
  if (invalidComponents.length > 0) {
    console.warn("Các customization component không hợp lệ:", invalidComponents);
  }

  /**
   * Dừng nếu không còn type hợp lệ.
   */
  if (customizationTypes.length === 0) {
    throw new Error(
      "Không còn customization type hợp lệ sau khi xử lý. " +
        `Detected: ${JSON.stringify(detectedTypes)}. ` +
        `Ignored: ${JSON.stringify(ignoredTypes)}. ` +
        `Empty: ${JSON.stringify(emptyTypes)}. ` +
        `Invalid: ${JSON.stringify(invalidComponents)}.`,
    );
  }

  /**
   * Tạo Cartesian product.
   */
  const combinations = customizationTypes.reduce(
    (currentCombinations, customizationType) =>
      currentCombinations.flatMap((currentCombination) =>
        customizationType.options.map((option) => ({
          options: [...currentCombination.options, option.value],
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

  /**
   * JSON cuối cùng.
   */
  const result = combinations.map((combination) => ({
    options: combination.options,
    additional_price: combination.additional_price,
  }));

  const json = JSON.stringify(result, null, 2);

  console.log("======================================");
  console.log("======================================");
  console.log("======================================");
  console.log("CUSTOMIZATION EXTRACTION RESULT");
  console.log("======================================");

  console.table(
    customizationTypes.map((item) => ({
      type: item.type,
      option_count: item.options.length,
    })),
  );

  console.log("Detected types:", detectedTypes);

  console.log("Ignored types:", ignoredTypes);

  console.log("Empty types:", emptyTypes);

  console.log(`Đã tạo ${result.length} tổ hợp customization.`);

  console.log(result);

  console.log("=======================================");
  console.log("=======================================");
  console.log("=======================================");

  /**
   * Sao chép JSON vào clipboard.
   */
  if (typeof copy === "function") {
    copy(json);

    console.log("Đã sao chép JSON vào clipboard bằng copy().");
  } else {
    try {
      await navigator.clipboard.writeText(json);

      console.log("Đã sao chép JSON vào clipboard.");
    } catch (error) {
      console.warn(
        "Không thể tự động sao chép JSON. " + "Kết quả vẫn được in trong Console.",
        error,
      );
    }
  }

  return result;
})().catch((error) => {
  console.error(">>> Không thể lấy customization:", error);

  /**
   * Không throw lại để tránh xuất hiện thêm
   * "Uncaught (in promise)".
   */
  return null;
});
