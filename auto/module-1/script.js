const aplus = document
  .getElementById("aplus_feature_div")
  .querySelector(".aplus-v2 .aplus-content-wrapper")
  .querySelectorAll(".aplus-module-wrapper img");
const htmlString = Array.from(aplus)
  .map((node) => node.outerHTML)
  .join(" ");
const desc_root = `<div class="description-root">${htmlString}</div>`;
console.log("=====================");
console.log("=====================");
console.log(desc_root);
console.log("=====================");
console.log("=====================\n\n\n");

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

      console.log("=====================");
      console.log(largeImageUrl);
      console.log("=====================");
    } else {
      console.log(`Bỏ qua URL trùng: ${largeImageUrl}`);
    }

    await sleep(300);
  }

  const result = {
    links,
  };

  console.log(`Hoàn tất: lấy được ${links.length}/${thumbnailItems.length} URL ảnh.`);

  console.log("Kết quả:", result);
  console.log(JSON.stringify(result, null, 2));

  try {
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));

    console.log("Đã copy kết quả JSON vào clipboard.");
  } catch {
    console.warn("Không thể tự động copy. Hãy copy kết quả trong Console.");
  }

  return result;
})();
