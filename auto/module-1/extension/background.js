/**
 * Background Service Worker for Wrydeco Amazon Scraper
 * Chrome Extension Manifest V3
 */

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

chrome.runtime.onInstalled.addListener(() => {
  console.log("[Wrydeco Scraper] Extension installed successfully.");

  // Thiết lập cấu hình mặc định trong storage nếu chưa có
  chrome.storage.local.get(
    ["mode", "furnitureType", "priceTier", "priceRangeStrategy", "timeoutMs", "ignoreTypes"],
    (result) => {
      const defaults = {};

      if (!result.mode) defaults.mode = "preset";
      if (!result.furnitureType) defaults.furnitureType = "corner";
      if (!result.priceTier) defaults.priceTier = "LUXURY";
      if (!result.priceRangeStrategy) defaults.priceRangeStrategy = "error";
      if (!result.timeoutMs) defaults.timeoutMs = 30000;
      if (result.ignoreTypes === undefined) {
        defaults.ignoreTypes = DEFAULT_IGNORE_TYPES.join("\n");
      }

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
