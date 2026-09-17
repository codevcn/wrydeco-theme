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

  const furnitureTypeSelect = document.getElementById("furnitureType");
  const priceTierSelect = document.getElementById("priceTier");
  const tierPreviewList = document.getElementById("tierPreviewList");

  const priceRangeStrategySelect = document.getElementById("priceRangeStrategy");
  const timeoutMsInput = document.getElementById("timeoutMs");

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
  let lastScrapedOutput = null;

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

  const saveSettings = () => {
    chrome.storage.local.set({
      mode: currentMode,
      furnitureType: furnitureTypeSelect.value,
      priceTier: priceTierSelect.value,
      priceRangeStrategy: priceRangeStrategySelect.value,
      timeoutMs: timeoutMsInput.value,
    });
  };

  // Load saved state
  chrome.storage.local.get(
    [
      "mode",
      "furnitureType",
      "priceTier",
      "priceRangeStrategy",
      "timeoutMs",
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

      if (data.lastScrapedOutput) {
        renderScrapeResult(data.lastScrapedOutput);
        addLog("Đã khôi phục dữ liệu cào lần gần nhất.", "info");
      }
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

      // Kiểm tra và inject content script nếu trang chưa có listener
      let ready = false;
      try {
        const ping = await chrome.tabs.sendMessage(tab.id, { action: "PING" }, { frameId: 0 });
        if (ping?.status === "PONG") ready = true;
      } catch {
        ready = false;
      }

      if (!ready) {
        addLog("Đang nạp bộ cào dữ liệu (content script) vào trang...", "info");
        await chrome.scripting.executeScript({
          target: { tabId: tab.id, allFrames: true },
          files: ["content.js"],
        });
        await new Promise((r) => setTimeout(r, 400));
      }

      // Cấu hình cào
      const scrapeConfig = {
        mode: currentMode,
        furnitureType: furnitureTypeSelect.value,
        priceTier: priceTierSelect.value,
        priceRangeStrategy: priceRangeStrategySelect.value,
        timeoutMs: Number(timeoutMsInput.value) || 30000,
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
});
