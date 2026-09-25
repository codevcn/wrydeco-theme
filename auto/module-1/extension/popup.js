/**
 * Wrydeco Amazon Scraper - Popup Controller
 * Chrome Extension Manifest V3
 */

document.addEventListener("DOMContentLoaded", async () => {
  // Elements
  const statusBadge = document.getElementById("statusBadge");
  const tabBtns = document.querySelectorAll(".tab-btn");
  const presetPanel = document.getElementById("presetPanel");
  const dynamicPanel = document.getElementById("dynamicPanel");

  // Navigation & Sections
  const btnToolsToggle = document.getElementById("btnToolsToggle");
  const scraperSection = document.getElementById("scraperSection");
  const toolsSection = document.getElementById("toolsSection");
  const scraperBottomBar = document.getElementById("scraperBottomBar");
  const btnBackToScraper = document.getElementById("btnBackToScraper");

  // Tools: ASINs Crawler Elements
  const btnCrawlAsins = document.getElementById("btnCrawlAsins");
  const asinsSpinner = document.getElementById("asinsSpinner");
  const asinsBtnText = document.getElementById("asinsBtnText");
  const asinsResultPanel = document.getElementById("asinsResultPanel");
  const asinsCountBadge = document.getElementById("asinsCountBadge");
  const asinsOutputTextarea = document.getElementById("asinsOutputTextarea");
  const btnCopyAsinsLines = document.getElementById("btnCopyAsinsLines");
  const btnCopyAsinsComma = document.getElementById("btnCopyAsinsComma");
  const btnCopyAsinsJson = document.getElementById("btnCopyAsinsJson");
  const btnCopyAsinsCommaMain = document.getElementById("btnCopyAsinsCommaMain");
  const btnCopyAsinsIcon = document.getElementById("btnCopyAsinsIcon");
  const btnCopyAsinsText = document.getElementById("btnCopyAsinsText");
  const toolsStatusBox = document.getElementById("toolsStatusBox");

  const furnitureTypeSelect = document.getElementById("furnitureType");
  const priceTierSelect = document.getElementById("priceTier");
  const tierPreviewList = document.getElementById("tierPreviewList");

  const priceRangeStrategySelect = document.getElementById("priceRangeStrategy");
  const timeoutMsInput = document.getElementById("timeoutMs");
  const ignoreTypesInput = document.getElementById("ignoreTypes");
  const btnResetIgnoreTypes = document.getElementById("btnResetIgnoreTypes");

  const btnScrape = document.getElementById("btnScrape");
  const scrapeSpinner = document.getElementById("scrapeSpinner");
  const scrapeBtnText = document.getElementById("scrapeBtnText");

  const btnCopyJson = document.getElementById("btnCopyJson");
  const btnDownloadJson = document.getElementById("btnDownloadJson");
  const btnClearLogs = document.getElementById("btnClearLogs");

  const summaryBar = document.getElementById("summaryBar");
  const statTitle = document.getElementById("statTitle");
  const statBullets = document.getElementById("statBullets");
  const statImages = document.getElementById("statImages");
  const statVariants = document.getElementById("statVariants");
  const statAplus = document.getElementById("statAplus");

  const logBox = document.getElementById("logBox");
  const jsonPreview = document.getElementById("jsonPreview");
  const jsonDetails = document.getElementById("jsonDetails");

  // State
  let currentMode = "preset";
  let currentSection = "scraper";
  let lastScrapedOutput = null;
  let lastCrawledAsins = [];

  // Danh sách Customization Types mặc định cần bỏ qua trong Dynamic Mode
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

  const parseIgnoreTypes = (text) => {
    if (typeof text !== "string") return [];
    const lines = text
      .split(/\r?\n/)
      .map((line) => line.trim().replace(/^["']/, "").replace(/["'],?$/, "").trim())
      .filter((line) => line.length > 0);
    return Array.from(new Set(lines));
  };

  // Bảng giá xem trước
  const PREVIEW_SIZES = {
    standing: {
      PREM: [
        { size: '50"W x 45"H x 8"D', price: '$3,906' },
        { size: '65"W x 60"H x 9"D', price: '$4,426' },
        { size: '75"W x 65"H x 10"D', price: '$4,947' },
        { size: '89"W x 80"H x 10-12"D', price: '$5,468' },
      ],
      LOW: [
        { size: '45"W x 45"H x 8"D', price: '$2,343' },
        { size: '59"W x 50"H x 9"D', price: '$2,864' },
        { size: '75"W x 65"H x 10"D', price: '$3,385' },
        { size: '89"W x 80"H x 10-12"D', price: '$3,906' },
      ],
    },
    corner: {
      LUXURY: [
        { size: '49"W x 55"H x 8"D', price: '$4,687' },
        { size: '60"W x 60"H x 10"D', price: '$5,128' },
        { size: '75"W x 69"H x 12"D', price: '$5,581' },
        { size: '90"W x 82"H x 12"D', price: '$6,034' },
      ],
      PREM: [
        { size: '49"W x 55"H x 8"D', price: '$2,983' },
        { size: '60"W x 60"H x 10"D', price: '$3,783' },
        { size: '75"W x 69"H x 12"D', price: '$4,583' },
        { size: '90"W x 82"H x 12"D', price: '$5,483' },
      ],
      LOW: [
        { size: '49"W x 55"H x 8"D', price: '$2,391' },
        { size: '60"W x 60"H x 10"D', price: '$2,991' },
        { size: '75"W x 69"H x 12"D', price: '$3,783' },
        { size: '90"W x 82"H x 12"D', price: '$4,591' },
      ],
    },
    floating: {
      PREM: [
        { size: '45"W x 45"H x 8"D', price: '$1,653' },
        { size: '55"W x 55"H x 8"D', price: '$1,953' },
        { size: '65"W x 65"H x 10"D', price: '$2,245' },
        { size: '80"W x 80"H x 10-12"D', price: '$2,675' },
      ],
      LOW: [
        { size: '45"W x 45"H x 8"D', price: '$1,553' },
        { size: '55"W x 55"H x 8"D', price: '$1,653' },
        { size: '65"W x 65"H x 10"D', price: '$2,045' },
        { size: '80"W x 80"H x 10-12"D', price: '$2,375' },
      ],
    },
  };

  const TIER_OPTIONS = {
    corner: [
      { value: "LUXURY", label: "LUXURY ($4,687 - $6,034)" },
      { value: "PREM", label: "PREM ($2,983 - $5,483)" },
      { value: "LOW", label: "LOW ($2,391 - $4,591)" },
    ],
    standing: [
      { value: "PREM", label: "PREM ($3,906 - $5,468)" },
      { value: "LOW", label: "LOW ($2,343 - $3,906)" },
    ],
    floating: [
      { value: "PREM", label: "PREM ($1,653 - $2,675)" },
      { value: "LOW", label: "LOW ($1,553 - $2,375)" },
    ],
  };

  // Helper log box
  const addLog = (message, level = "info") => {
    const timeStr = new Date().toLocaleTimeString();
    const item = document.createElement("div");
    item.className = `log-item log-${level}`;

    const timeSpan = document.createElement("span");
    timeSpan.className = "log-time";
    timeSpan.textContent = timeStr;

    const msgSpan = document.createElement("span");
    msgSpan.className = "log-msg";
    msgSpan.textContent = message;

    item.appendChild(timeSpan);
    item.appendChild(msgSpan);
    logBox.appendChild(item);
    logBox.scrollTop = logBox.scrollHeight;
  };

  const setStatus = (status, text) => {
    statusBadge.className = `status-badge status-${status}`;
    statusBadge.textContent = text;
  };

  // Update Price Tier dropdown & Preview
  const updatePriceTiers = (selectedType, preferredTier = null) => {
    const tiers = TIER_OPTIONS[selectedType] || [];
    priceTierSelect.innerHTML = "";

    tiers.forEach((tier) => {
      const opt = document.createElement("option");
      opt.value = tier.value;
      opt.textContent = tier.label;
      priceTierSelect.appendChild(opt);
    });

    if (preferredTier && tiers.some((t) => t.value === preferredTier)) {
      priceTierSelect.value = preferredTier;
    } else if (tiers.length > 0) {
      priceTierSelect.value = tiers[0].value;
    }

    updateTierPreview(selectedType, priceTierSelect.value);
  };

  const updateTierPreview = (type, tier) => {
    const items = PREVIEW_SIZES[type]?.[tier] || [];
    tierPreviewList.innerHTML = "";

    items.forEach((item) => {
      const li = document.createElement("li");
      li.className = "preview-item";

      const sizeSpan = document.createElement("span");
      sizeSpan.className = "preview-size";
      sizeSpan.textContent = item.size;

      const priceSpan = document.createElement("span");
      priceSpan.className = "preview-price";
      priceSpan.textContent = item.price;

      li.appendChild(sizeSpan);
      li.appendChild(priceSpan);
      tierPreviewList.appendChild(li);
    });
  };

  // Event: Change furniture type
  furnitureTypeSelect.addEventListener("change", () => {
    updatePriceTiers(furnitureTypeSelect.value);
    saveSettings();
  });

  // Event: Change price tier
  priceTierSelect.addEventListener("change", () => {
    updateTierPreview(furnitureTypeSelect.value, priceTierSelect.value);
    saveSettings();
  });

  // Event: Mode tab click
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      currentMode = btn.dataset.mode;
      if (currentMode === "preset") {
        presetPanel.classList.add("active");
        dynamicPanel.classList.remove("active");
      } else {
        presetPanel.classList.remove("active");
        dynamicPanel.classList.add("active");
      }

      saveSettings();
    });
  });

  // Section Navigation (Scraper vs Tools)
  const switchSection = (sectionName) => {
    currentSection = sectionName;
    if (sectionName === "tools") {
      btnToolsToggle?.classList.add("active");
      if (btnToolsToggle) btnToolsToggle.title = "Quay lại Scraper";
      scraperSection?.classList.add("hidden");
      scraperSection?.classList.remove("active");
      scraperBottomBar?.classList.add("hidden");
      toolsSection?.classList.remove("hidden");
      toolsSection?.classList.add("active");
      addLog("Đã chuyển sang mục Công cụ hỗ trợ (Tools).", "info");
    } else {
      btnToolsToggle?.classList.remove("active");
      if (btnToolsToggle) btnToolsToggle.title = "Chuyển sang mục Tools";
      scraperSection?.classList.remove("hidden");
      scraperSection?.classList.add("active");
      scraperBottomBar?.classList.remove("hidden");
      toolsSection?.classList.add("hidden");
      toolsSection?.classList.remove("active");
    }
  };

  btnToolsToggle?.addEventListener("click", () => {
    switchSection(currentSection === "scraper" ? "tools" : "scraper");
  });

  btnBackToScraper?.addEventListener("click", () => {
    switchSection("scraper");
  });

  const showToolsStatus = (msg, type = "info") => {
    if (!toolsStatusBox) return;
    toolsStatusBox.className = `tools-status-box ${type}`;
    toolsStatusBox.textContent = msg;
    toolsStatusBox.classList.remove("hidden");
  };

  let isStorageLoaded = false;

  // Khởi tạo ngay giá trị mặc định cho textarea nếu DOM chưa có giá trị
  if (ignoreTypesInput && !ignoreTypesInput.value.trim()) {
    ignoreTypesInput.value = DEFAULT_IGNORE_TYPES.join("\n");
  }

  const saveSettings = () => {
    if (!isStorageLoaded) return;
    chrome.storage.local.set({
      mode: currentMode,
      furnitureType: furnitureTypeSelect.value,
      priceTier: priceTierSelect.value,
      priceRangeStrategy: priceRangeStrategySelect.value,
      timeoutMs: timeoutMsInput.value,
      ignoreTypes: ignoreTypesInput ? ignoreTypesInput.value : "",
    });
  };

  // Event listeners for Dynamic Mode settings
  priceRangeStrategySelect.addEventListener("change", saveSettings);
  timeoutMsInput.addEventListener("input", saveSettings);

  if (ignoreTypesInput) {
    ignoreTypesInput.addEventListener("input", saveSettings);
  }

  if (btnResetIgnoreTypes && ignoreTypesInput) {
    btnResetIgnoreTypes.addEventListener("click", () => {
      ignoreTypesInput.value = DEFAULT_IGNORE_TYPES.join("\n");
      saveSettings();
      addLog("Đã khôi phục danh sách IGNORE_TYPES mặc định.", "info");
    });
  }

  // Load saved state
  chrome.storage.local.get(
    [
      "mode",
      "furnitureType",
      "priceTier",
      "priceRangeStrategy",
      "timeoutMs",
      "ignoreTypes",
      "lastScrapedOutput",
    ],
    (data) => {
      if (data.mode) {
        currentMode = data.mode;
        tabBtns.forEach((b) => {
          b.classList.toggle("active", b.dataset.mode === currentMode);
        });
        presetPanel.classList.toggle("active", currentMode === "preset");
        dynamicPanel.classList.toggle("active", currentMode === "dynamic");
      }

      const fType = data.furnitureType || "corner";
      furnitureTypeSelect.value = fType;
      updatePriceTiers(fType, data.priceTier);

      if (data.priceRangeStrategy) {
        priceRangeStrategySelect.value = data.priceRangeStrategy;
      }
      if (data.timeoutMs) {
        timeoutMsInput.value = data.timeoutMs;
      }

      if (ignoreTypesInput) {
        if (typeof data.ignoreTypes === "string") {
          ignoreTypesInput.value = data.ignoreTypes;
        } else if (Array.isArray(data.ignoreTypes)) {
          ignoreTypesInput.value = data.ignoreTypes.join("\n");
        } else {
          ignoreTypesInput.value = DEFAULT_IGNORE_TYPES.join("\n");
        }
      }

      if (data.lastScrapedOutput) {
        renderScrapeResult(data.lastScrapedOutput);
        addLog("Đã khôi phục dữ liệu cào lần gần nhất.", "info");
      }

      isStorageLoaded = true;
    }
  );

  // Render Result in UI
  const renderScrapeResult = (output) => {
    lastScrapedOutput = output;
    const p = output?.product || {};

    statTitle.textContent = p.product_title || "(Chưa có)";
    statBullets.textContent = p.product_description?.length || 0;
    statImages.textContent = p.product_images?.length || 0;
    statVariants.textContent = p.variant_data?.length || 0;

    const aplusCount = (p.product_rich_description?.match(/<img /g) || []).length;
    statAplus.textContent = `${aplusCount} ảnh`;

    summaryBar.classList.remove("hidden");

    const jsonStr = JSON.stringify(output, null, 2);
    jsonPreview.textContent = jsonStr;
    jsonDetails.open = false;

    btnCopyJson.disabled = false;
    btnDownloadJson.disabled = false;
  };

  // Lắng nghe log thời gian thực từ content.js
  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === "SCRAPE_LOG") {
      addLog(message.message, message.level || "info");
    }
  });

  // Helper: Đảm bảo content script đã được nạp vào tab
  const ensureContentScriptReady = async (tabId) => {
    let ready = false;
    try {
      const ping = await chrome.tabs.sendMessage(tabId, { action: "PING" }, { frameId: 0 });
      if (ping?.status === "PONG") ready = true;
    } catch {
      ready = false;
    }

    if (!ready) {
      addLog("Đang nạp bộ cào dữ liệu (content script) vào trang...", "info");
      await chrome.scripting.executeScript({
        target: { tabId, allFrames: true },
        files: ["content.js"],
      });
      await new Promise((r) => setTimeout(r, 400));
    }
  };

  // Action: Scrape
  btnScrape.addEventListener("click", async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.id) {
        addLog("Không tìm thấy tab trình duyệt đang hoạt động.", "error");
        return;
      }

      if (!tab.url || !tab.url.includes("amazon.com")) {
        addLog("Vui lòng mở trang sản phẩm Amazon (*.amazon.com) trước khi cào dữ liệu.", "warn");
        setStatus("error", "Sai trang web");
        return;
      }

      // UI state: Running
      setStatus("running", "Đang cào...");
      btnScrape.disabled = true;
      scrapeSpinner.classList.remove("hidden");
      scrapeBtnText.textContent = "Đang xử lý...";
      addLog(`🚀 Khởi động cào dữ liệu (Chế độ: ${currentMode.toUpperCase()})...`, "info");

      // Đảm bảo content script đã sẵn sàng
      await ensureContentScriptReady(tab.id);

      saveSettings();

      // Cấu hình cào
      const ignoreTypesList = parseIgnoreTypes(ignoreTypesInput ? ignoreTypesInput.value : "");

      if (currentMode === "dynamic") {
        addLog(
          `⚡ Dynamic Mode: Áp dụng ${ignoreTypesList.length} customization types cần bỏ qua.`,
          "info"
        );
      }

      const scrapeConfig = {
        mode: currentMode,
        furnitureType: furnitureTypeSelect.value,
        priceTier: priceTierSelect.value,
        priceRangeStrategy: priceRangeStrategySelect.value,
        timeoutMs: Number(timeoutMsInput.value) || 30000,
        ignoreTypes: ignoreTypesList,
      };

      // Gửi lệnh cào đến content script (chỉ định frameId: 0 để giao tiếp trực tiếp với top frame)
      const response = await chrome.tabs.sendMessage(
        tab.id,
        {
          action: "START_SCRAPE",
          config: scrapeConfig,
        },
        { frameId: 0 }
      );

      if (!response || !response.success) {
        throw new Error(response?.error || "Không nhận được phản hồi từ trang Amazon.");
      }

      // Thành công!
      setStatus("success", "Thành công");
      renderScrapeResult(response.data);
      chrome.storage.local.set({ lastScrapedOutput: response.data });

      // Tự động sao chép JSON vào clipboard
      const jsonStr = JSON.stringify(response.data, null, 2);
      try {
        await navigator.clipboard.writeText(jsonStr);
        addLog("✅ Đã tự động sao chép JSON vào Clipboard!", "success");
      } catch {
        addLog("⚠️ Trình duyệt chặn auto-copy. Vui lòng bấm nút 'Sao chép JSON'.", "warn");
      }
    } catch (err) {
      console.error(err);
      setStatus("error", "Có lỗi");
      addLog(`❌ Thất bại: ${err.message}`, "error");
    } finally {
      btnScrape.disabled = false;
      scrapeSpinner.classList.add("hidden");
      scrapeBtnText.textContent = "🚀 Bắt đầu cào dữ liệu";
    }
  });

  // Action: Copy JSON
  btnCopyJson.addEventListener("click", async () => {
    if (!lastScrapedOutput) return;
    try {
      const jsonStr = JSON.stringify(lastScrapedOutput, null, 2);
      await navigator.clipboard.writeText(jsonStr);
      const originalText = btnCopyJson.textContent;
      btnCopyJson.textContent = "✅ Đã sao chép!";
      setTimeout(() => {
        btnCopyJson.textContent = originalText;
      }, 2000);
      addLog("Đã sao chép JSON vào clipboard.", "success");
    } catch (err) {
      addLog(`Lỗi sao chép: ${err.message}`, "error");
    }
  });

  // Action: Download JSON (config.prepare.json)
  btnDownloadJson.addEventListener("click", () => {
    if (!lastScrapedOutput) return;
    const jsonStr = JSON.stringify(lastScrapedOutput, null, 2);
    const filename = "config.prepare.json";

    try {
      // Dùng chrome.downloads nếu khả dụng
      if (chrome.downloads && typeof chrome.downloads.download === "function") {
        const blobUrl = "data:application/json;charset=utf-8," + encodeURIComponent(jsonStr);
        chrome.downloads.download(
          {
            url: blobUrl,
            filename: filename,
            saveAs: true,
          },
          (downloadId) => {
            if (chrome.runtime.lastError) {
              fallbackBlobDownload(jsonStr, filename);
            } else {
              addLog(`💾 Đã tải file: ${filename}`, "success");
            }
          }
        );
      } else {
        fallbackBlobDownload(jsonStr, filename);
      }
    } catch {
      fallbackBlobDownload(jsonStr, filename);
    }
  });

  const fallbackBlobDownload = (text, filename) => {
    const blob = new Blob([text], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    addLog(`💾 Đã lưu file: ${filename}`, "success");
  };

  // Action: Clear logs
  btnClearLogs.addEventListener("click", () => {
    logBox.innerHTML = "";
    addLog("Đã xóa nhật ký.", "info");
  });

  // ============================================================
  // Tools Action: Crawl Unordered-List ASINs
  // ============================================================
  btnCrawlAsins?.addEventListener("click", async () => {
    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.id) {
        showToolsStatus("❌ Không tìm thấy tab trình duyệt đang hoạt động.", "error");
        return;
      }

      if (!tab.url || !tab.url.includes("amazon.com")) {
        showToolsStatus("⚠️ Vui lòng mở trang sản phẩm Amazon (*.amazon.com) trước khi cào ASINs.", "warn");
        return;
      }

      btnCrawlAsins.disabled = true;
      asinsSpinner?.classList.remove("hidden");
      if (asinsBtnText) asinsBtnText.textContent = "Đang cào ASINs...";
      toolsStatusBox?.classList.add("hidden");
      addLog("🔍 Đang quét danh sách .a-unordered-list.dimension-values-list.dimension-values-carousel...", "info");

      await ensureContentScriptReady(tab.id);

      const response = await chrome.tabs.sendMessage(
        tab.id,
        { action: "CRAWL_UNORDERED_LIST_ASINS" },
        { frameId: 0 }
      );

      if (!response || !response.success) {
        throw new Error(response?.error || "Không nhận được phản hồi từ trang Amazon.");
      }

      lastCrawledAsins = response.asins || [];
      if (lastCrawledAsins.length > 0) {
        asinsResultPanel?.classList.remove("hidden");
        if (asinsCountBadge) asinsCountBadge.textContent = `${lastCrawledAsins.length} ASINs`;
        if (asinsOutputTextarea) asinsOutputTextarea.value = lastCrawledAsins.join("\n");
        showToolsStatus(`✅ Đã cào thành công ${lastCrawledAsins.length} mã ASIN từ swatch carousel.`, "success");
        addLog(`✅ Đã trích xuất ${lastCrawledAsins.length} mã ASIN từ danh sách dimension-values.`, "success");

        // Tự động sao chép danh sách ASINs (cách nhau bởi dấu phẩy) vào clipboard
        const commaSeparated = lastCrawledAsins.join(", ");
        try {
          await navigator.clipboard.writeText(commaSeparated);
          addLog("📋 Đã tự động sao chép danh sách ASINs (dấu phẩy) vào Clipboard!", "success");
          triggerMainCopyIndicator(2000);
        } catch (clipErr) {
          console.warn("Auto copy clipboard failed:", clipErr);
        }
      } else {
        asinsResultPanel?.classList.add("hidden");
        showToolsStatus("⚠️ Không tìm thấy element .a-unordered-list.dimension-values-list.dimension-values-carousel hoặc không có mã ASIN nào trong các phần tử con .inline-twister-swatch.", "warn");
        addLog("⚠️ Không tìm thấy element carousel hoặc không có mã ASIN nào.", "warn");
      }
    } catch (err) {
      console.error(err);
      showToolsStatus(`❌ Lỗi: ${err.message}`, "error");
      addLog(`❌ Thất bại khi cào ASINs: ${err.message}`, "error");
    } finally {
      btnCrawlAsins.disabled = false;
      asinsSpinner?.classList.add("hidden");
      if (asinsBtnText) asinsBtnText.textContent = "🔍 Crawl Unordered-List ASINs";
    }
  });

  let mainCopyTimer = null;
  const triggerMainCopyIndicator = (duration = 2000) => {
    if (!btnCopyAsinsCommaMain) return;
    if (mainCopyTimer) clearTimeout(mainCopyTimer);

    btnCopyAsinsCommaMain.classList.add("copied-success");
    if (btnCopyAsinsIcon) btnCopyAsinsIcon.textContent = "✅";
    if (btnCopyAsinsText) btnCopyAsinsText.textContent = "Đã sao chép vào Clipboard (2s)!";

    mainCopyTimer = setTimeout(() => {
      btnCopyAsinsCommaMain.classList.remove("copied-success");
      if (btnCopyAsinsIcon) btnCopyAsinsIcon.textContent = "📋";
      if (btnCopyAsinsText) btnCopyAsinsText.textContent = "Sao chép ASINs (dấu phẩy)";
    }, duration);
  };

  const handleCopyFeedback = (btn, originalText) => {
    btn.classList.add("btn-copied");
    btn.textContent = "✅ Đã copy!";
    setTimeout(() => {
      btn.classList.remove("btn-copied");
      btn.textContent = originalText;
    }, 2000);
  };

  // Nút chính: Sao chép ASINs cách nhau bởi dấu phẩy với 2s indicator
  btnCopyAsinsCommaMain?.addEventListener("click", async () => {
    if (!lastCrawledAsins.length) return;
    try {
      const commaSeparated = lastCrawledAsins.join(", ");
      await navigator.clipboard.writeText(commaSeparated);
      triggerMainCopyIndicator(2000);
      addLog("Đã sao chép danh sách ASINs (cách nhau bởi dấu phẩy).", "success");
    } catch (err) {
      addLog(`Lỗi sao chép: ${err.message}`, "error");
    }
  });

  btnCopyAsinsLines?.addEventListener("click", async () => {
    if (!lastCrawledAsins.length) return;
    try {
      await navigator.clipboard.writeText(lastCrawledAsins.join("\n"));
      handleCopyFeedback(btnCopyAsinsLines, "📋 Dòng");
      addLog("Đã sao chép danh sách ASINs (mỗi mã 1 dòng).", "success");
    } catch (err) {
      addLog(`Lỗi sao chép: ${err.message}`, "error");
    }
  });

  btnCopyAsinsComma?.addEventListener("click", async () => {
    if (!lastCrawledAsins.length) return;
    try {
      const commaSeparated = lastCrawledAsins.join(", ");
      await navigator.clipboard.writeText(commaSeparated);
      handleCopyFeedback(btnCopyAsinsComma, "📋 Phẩy");
      triggerMainCopyIndicator(2000);
      addLog("Đã sao chép danh sách ASINs (cách nhau bởi dấu phẩy).", "success");
    } catch (err) {
      addLog(`Lỗi sao chép: ${err.message}`, "error");
    }
  });

  btnCopyAsinsJson?.addEventListener("click", async () => {
    if (!lastCrawledAsins.length) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(lastCrawledAsins, null, 2));
      handleCopyFeedback(btnCopyAsinsJson, "📋 JSON");
      addLog("Đã sao chép danh sách ASINs dạng JSON Array.", "success");
    } catch (err) {
      addLog(`Lỗi sao chép: ${err.message}`, "error");
    }
  });
});
