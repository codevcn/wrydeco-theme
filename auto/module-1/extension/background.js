/**
 * Background Service Worker for Wrydeco Amazon Scraper
 * Chrome Extension Manifest V3
 */

chrome.runtime.onInstalled.addListener(() => {
  console.log("[Wrydeco Scraper] Extension installed successfully.");

  // Thiết lập cấu hình mặc định trong storage nếu chưa có
  chrome.storage.local.get(
    ["mode", "furnitureType", "priceTier", "priceRangeStrategy", "timeoutMs"],
    (result) => {
      const defaults = {};

      if (!result.mode) defaults.mode = "preset";
      if (!result.furnitureType) defaults.furnitureType = "corner";
      if (!result.priceTier) defaults.priceTier = "LUXURY";
      if (!result.priceRangeStrategy) defaults.priceRangeStrategy = "error";
      if (!result.timeoutMs) defaults.timeoutMs = 30000;

      if (Object.keys(defaults).length > 0) {
        chrome.storage.local.set(defaults);
      }
    }
  );
});

// Lắng nghe messages hỗ trợ download nếu cần
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "DOWNLOAD_JSON") {
    try {
      const jsonString = request.jsonString;
      const filename = request.filename || "config.prepare.json";
      const blobUrl =
        "data:application/json;charset=utf-8," +
        encodeURIComponent(jsonString);

      chrome.downloads.download(
        {
          url: blobUrl,
          filename: filename,
          saveAs: true,
        },
        (downloadId) => {
          if (chrome.runtime.lastError) {
            sendResponse({ success: false, error: chrome.runtime.lastError.message });
          } else {
            sendResponse({ success: true, downloadId });
          }
        }
      );
      return true; // async sendResponse
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }
  }
});
