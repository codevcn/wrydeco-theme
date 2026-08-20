const fs = require('fs');

const path = 'sections/workshop-evidence.liquid';
let content = fs.readFileSync(path, 'utf8');
content = content.replace(/\r\n/g, '\n');

// 1. Insert pagination HTML
const htmlTarget = `      </div>

      {% if packaging_image_count > 0 %}`;
const htmlReplacement = `      </div>

      <div class="workshop-evidence__slider-nav" aria-label="Process slider navigation">
        {% assign slide_index = 0 %}
        {% if handcraft_video_url != blank %}
          <button class="workshop-evidence__slider-dot is-active" type="button" aria-label="Slide to Handcrafting" data-process-slide="{{ slide_index }}"></button>
          {% assign slide_index = slide_index | plus: 1 %}
        {% endif %}
        {% if assembly_video_url != blank %}
          <button class="workshop-evidence__slider-dot {% if slide_index == 0 %}is-active{% endif %}" type="button" aria-label="Slide to Assembly" data-process-slide="{{ slide_index }}"></button>
          {% assign slide_index = slide_index | plus: 1 %}
        {% endif %}
        {% if packaging_image_count > 0 %}
          <button class="workshop-evidence__slider-dot {% if slide_index == 0 %}is-active{% endif %}" type="button" aria-label="Slide to Packaging" data-process-slide="{{ slide_index }}"></button>
        {% endif %}
      </div>

      {% if packaging_image_count > 0 %}`;
content = content.replace(htmlTarget, htmlReplacement);

// 2. Insert CSS styles
const cssTarget = `  @media screen and (max-width: 1199px) {`;
const cssReplacement = `  .workshop-evidence__slider-nav {
    display: none;
    justify-content: center;
    gap: var(--sp-2);
    margin-block-start: var(--sp-6);
  }

  .workshop-evidence__slider-dot {
    width: var(--sp-2);
    height: var(--sp-2);
    padding: 0;
    border: var(--border-width) solid color-mix(in srgb, var(--color-earth-brown) 30%, transparent);
    border-radius: var(--radius-full);
    background: transparent;
    cursor: pointer;
    transition: all var(--duration-default) var(--ease-out);
  }

  .workshop-evidence__slider-dot.is-active {
    width: var(--sp-5);
    background: var(--color-earth-brown);
    border-color: var(--color-earth-brown);
  }

  @media screen and (max-width: 1199px) {`;
content = content.replace(cssTarget, cssReplacement);

const mobileCssTarget = `  @media screen and (max-width: 767px) {
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
      margin-block-start: var(--sp-4);
      font-size: var(--font-size-body-lg);
      gap: var(--sp-3);
    }`;
const mobileCssReplacement = `  @media screen and (max-width: 767px) {
    .workshop-evidence {
      padding: var(--sp-7) var(--layout-padding-mobile) var(--sp-6);
    }
    
    .workshop-evidence__slider-nav {
      display: flex;
    }

    .workshop-evidence__media-grid {
      display: flex;
      flex-wrap: nowrap;
      overflow-x: auto;
      scroll-snap-type: x mandatory;
      scroll-behavior: smooth;
      scrollbar-width: none;
      gap: var(--sp-4);
      padding-bottom: var(--sp-2);
    }
    .workshop-evidence__media-grid::-webkit-scrollbar {
      display: none;
    }

    .workshop-evidence__video-card,
    .workshop-evidence__packaging {
      flex: 0 0 100%;
      min-width: 100%;
      scroll-snap-align: start;
      scroll-snap-stop: always;
    }

    .workshop-evidence__video-frame,
    .workshop-evidence__package-frame {
      aspect-ratio: 4 / 3;
      border-radius: 14px;
    }
    
    .workshop-evidence__package-frame {
      touch-action: pan-y;
    }

    .workshop-evidence__caption {
      justify-content: center;
      margin-inline: auto;
      max-width: 100%;
      margin-block-start: 16px;
      font-size: var(--font-size-body-lg);
      gap: 12px;
    }`;
content = content.replace(mobileCssTarget, mobileCssReplacement);

// 3. JS Changes
const jsTarget = `    document.addEventListener('keydown', function (event) {`;
const jsReplacement = `    document.addEventListener('click', function(event) {
      var processDot = event.target.closest('[data-process-slide]');
      if (processDot) {
        var index = parseInt(processDot.dataset.processSlide, 10);
        var section = processDot.closest('.workshop-evidence');
        var slider = section ? section.querySelector('.workshop-evidence__media-grid') : null;
        if (slider) {
          slider.scrollTo({
            left: index * slider.clientWidth,
            behavior: 'smooth'
          });
        }
      }
    });

    var touchStartX = 0;
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
      var section = slider.closest('.workshop-evidence');
      var dots = section ? section.querySelectorAll('.workshop-evidence__slider-dot') : [];
      if (!dots.length) return;

      var isScrolling;
      slider.addEventListener('scroll', function() {
        window.clearTimeout(isScrolling);
        isScrolling = setTimeout(function() {
          var index = Math.round(slider.scrollLeft / slider.clientWidth);
          dots.forEach(function(dot, i) {
            dot.classList.toggle('is-active', i === index);
          });
        }, 50);
      }, { passive: true });
    });

    document.addEventListener('keydown', function (event) {`;
content = content.replace(jsTarget, jsReplacement);

fs.writeFileSync(path, content);
console.log("Successfully updated workshop-evidence.liquid");
