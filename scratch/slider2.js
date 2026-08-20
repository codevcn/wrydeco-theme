const fs = require('fs');

const path = 'sections/workshop-evidence.liquid';
let content = fs.readFileSync(path, 'utf8');
content = content.replace(/\r\n/g, '\n');

// 1. Desktop 3 columns fix (< 1199px)
const cssTarget = `  @media screen and (max-width: 1180px) {
    .workshop-evidence {
      padding-inline: var(--layout-padding-tablet);
    }

    .workshop-evidence__media-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .workshop-evidence__packaging {
      grid-column: 1 / -1;
      max-width: 560px;
      width: 100%;
      margin-inline: auto;
    }
  }`;

const cssReplacement = `  @media screen and (max-width: 1199px) {
    .workshop-evidence {
      padding-inline: var(--layout-padding-tablet);
    }

    .workshop-evidence__media-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: var(--sp-3);
    }

    .workshop-evidence__caption {
      margin-block-start: var(--sp-3);
      font-size: clamp(var(--font-size-body-sm), 1.2vw, var(--font-size-body-md));
      gap: var(--sp-2);
    }

    .workshop-evidence__caption-icon {
      width: var(--sp-6);
    }
    
    .workshop-evidence__play {
      width: clamp(var(--sp-7), 4vw, var(--sp-9));
    }
  }`;
content = content.replace(cssTarget, cssReplacement);

// 2. Mobile horizontal rail (< 767px)
const mobileCssTarget = `  @media screen and (max-width: 720px) {
    .workshop-evidence {
      padding: var(--sp-7) var(--layout-padding-mobile) var(--sp-6);
    }

    .workshop-evidence__media-grid {
      grid-template-columns: minmax(0, 1fr);
      gap: var(--sp-6);
    }

    .workshop-evidence__video-frame,
    .workshop-evidence__package-frame {
      aspect-ratio: 4 / 5;
      border-radius: var(--radius-lg);
    }

    .workshop-evidence__caption {
      justify-content: flex-start;
      margin-inline: auto;
      max-width: 360px;
    }

    .workshop-evidence__package-nav--prev {
      left: var(--sp-2);
    }

    .workshop-evidence__package-nav--next {
      right: var(--sp-2);
    }

    .workshop-evidence__lightbox {
      padding: var(--sp-4);
    }
  }`;

const mobileCssReplacement = `  @media screen and (max-width: 767px) {
    .workshop-evidence {
      padding: var(--sp-7) 0 var(--sp-6);
    }

    .workshop-evidence__media-grid {
      display: flex;
      flex-wrap: nowrap;
      overflow-x: auto;
      scroll-snap-type: x proximity;
      scroll-behavior: smooth;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: none;
      gap: var(--sp-4);
      padding-inline: var(--layout-padding-mobile);
      scroll-padding-inline: var(--layout-padding-mobile);
      cursor: grab;
    }
    
    .workshop-evidence__media-grid.is-dragging {
      cursor: grabbing;
      user-select: none;
      scroll-snap-type: none;
      scroll-behavior: auto;
    }

    .workshop-evidence__media-grid::-webkit-scrollbar {
      display: none;
    }

    .workshop-evidence__video-card,
    .workshop-evidence__packaging {
      flex: 0 0 auto;
      width: clamp(270px, 78vw, 360px);
      scroll-snap-align: start;
    }

    .workshop-evidence__video-frame,
    .workshop-evidence__package-frame {
      aspect-ratio: 4 / 5;
      border-radius: 14px;
    }
    
    .workshop-evidence__package-frame {
      touch-action: pan-y;
    }

    .workshop-evidence__caption {
      justify-content: flex-start;
      margin-inline: auto;
      max-width: 100%;
      margin-block-start: 16px;
      font-size: var(--font-size-body-lg);
      gap: 12px;
    }

    .workshop-evidence__caption-icon {
      width: var(--sp-8);
    }

    .workshop-evidence__package-nav--prev {
      left: var(--sp-2);
    }

    .workshop-evidence__package-nav--next {
      right: var(--sp-2);
    }

    .workshop-evidence__lightbox {
      padding: var(--sp-4);
    }
  }`;
content = content.replace(mobileCssTarget, mobileCssReplacement);

// 3. JS Changes for Dragging and Packaging slider touch
const jsTarget = `    document.addEventListener('keydown', function (event) {`;
const jsReplacement = `    var touchStartX = 0;
    var touchEndX = 0;
    document.addEventListener('touchstart', function(e) {
      var track = e.target.closest('[data-workshop-package-track]');
      if (track && e.changedTouches && e.changedTouches.length > 0) {
        touchStartX = e.changedTouches[0].screenX;
      }
    }, {passive: true});

    document.addEventListener('touchend', function(e) {
      var packaging = e.target.closest('[data-workshop-packaging]');
      if (packaging && e.changedTouches && e.changedTouches.length > 0) {
        touchEndX = e.changedTouches[0].screenX;
        var diff = touchStartX - touchEndX;
        if (Math.abs(diff) > 40) {
          var currentIndex = Number(packaging.dataset.workshopPackageIndex || 0);
          if (diff > 0) {
            setPackageIndex(packaging, currentIndex + 1);
          } else {
            setPackageIndex(packaging, currentIndex - 1);
          }
        }
      }
    }, {passive: true});

    document.querySelectorAll('.workshop-evidence__media-grid').forEach(function(slider) {
      var isDown = false;
      var startX;
      var scrollLeft;

      slider.addEventListener('mousedown', function(e) {
        // Prevent drag on packaging controls
        if (e.target.closest('.workshop-evidence__package-nav') || e.target.closest('.workshop-evidence__package-dot')) {
          return;
        }
        isDown = true;
        slider.classList.add('is-dragging');
        startX = e.pageX - slider.offsetLeft;
        scrollLeft = slider.scrollLeft;
      });
      slider.addEventListener('mouseleave', function() {
        isDown = false;
        slider.classList.remove('is-dragging');
      });
      slider.addEventListener('mouseup', function() {
        isDown = false;
        slider.classList.remove('is-dragging');
      });
      slider.addEventListener('mousemove', function(e) {
        if (!isDown) return;
        e.preventDefault();
        var x = e.pageX - slider.offsetLeft;
        var walk = (x - startX) * 2;
        slider.scrollLeft = scrollLeft - walk;
      });
    });

    document.addEventListener('keydown', function (event) {`;
content = content.replace(jsTarget, jsReplacement);

fs.writeFileSync(path, content);
console.log("Successfully updated workshop-evidence.liquid");
