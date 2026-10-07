(function (root) {
  "use strict";

  function cleanUrl(value) {
    if (!value) return "";
    try {
      const url = new URL(String(value), document.baseURI);
      url.search = "";
      url.hash = "";
      if (/media-amazon\.com$/i.test(url.hostname)) {
        url.pathname = url.pathname.replace(/\._[^/]+(?=\.(?:jpe?g|png|webp)$)/i, "");
      }
      return url.href;
    } catch (_) {
      return "";
    }
  }

  function useful(value) {
    const text = String(value || "").toLowerCase();
    return Boolean(text) && !/(?:loadindicator|loading-|\/loading|spinner|ajax-loader|play-button|sprite|transparent-pixel|transparent-1x1|gr[ae]y-pixel|pixel\.gif|1x1\.gif)/.test(text);
  }

  function bestFromSrcset(value) {
    return String(value || "").split(",").map(part => part.trim().split(/\s+/)[0]).filter(Boolean).pop() || "";
  }

  function pushUnique(output, seen, value) {
    const url = cleanUrl(value);
    if (useful(url) && !seen.has(url)) {
      seen.add(url);
      output.push(url);
    }
  }

  function extractGalleryUrls(doc) {
    const output = [];
    const seen = new Set();
    const main = doc.querySelector("#landingImage, #imgTagWrapperId img");
    if (main) {
      const dynamic = main.getAttribute("data-a-dynamic-image");
      if (dynamic) {
        try {
          Object.keys(JSON.parse(dynamic)).forEach(url => pushUnique(output, seen, url));
        } catch (_) {}
      }
      [main.getAttribute("data-old-hires"), main.currentSrc, main.src].forEach(url => pushUnique(output, seen, url));
    }
    const scripts = [...doc.scripts].map(script => script.textContent || "").join("\n");
    const colorMatch = scripts.match(/'colorImages'\s*:\s*(\{[\s\S]*?\})\s*,\s*'colorToAsin'/);
    if (colorMatch) {
      try {
        const parsed = Function('"use strict";return (' + colorMatch[1] + ')')();
        Object.values(parsed).flat().forEach(item => {
          if (!item || typeof item !== "object") return;
          [item.hiRes, item.large, item.mainUrl].forEach(url => pushUnique(output, seen, url));
        });
      } catch (_) {}
    }
    doc.querySelectorAll("#altImages li:not(.videoThumbnail) img").forEach(img => {
      [img.getAttribute("data-old-hires"), img.getAttribute("data-a-hires"), img.src].forEach(url => pushUnique(output, seen, url));
    });
    return output;
  }

  function extractAplusUrls(container) {
    const output = [];
    const seen = new Set();
    container.querySelectorAll("img").forEach(img => {
      [img.dataset.src, img.getAttribute("data-a-hires"), bestFromSrcset(img.getAttribute("srcset")), img.currentSrc, img.src]
        .forEach(url => pushUnique(output, seen, url));
    });
    return output;
  }

  root.WRYDECO_SCRAPER_SHARED = { cleanUrl, extractGalleryUrls, extractAplusUrls };
})(globalThis);
