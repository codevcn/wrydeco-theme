const fs = require('fs');
const path = 'sections/workshop-evidence.liquid';
let content = fs.readFileSync(path, 'utf8');

const target = `    function closeLightbox(lightbox) {
      if (!lightbox) return;

      var image = lightbox.querySelector('[data-workshop-lightbox-image]');
      if (image) image.removeAttribute('src');
      lightbox.classList.remove('is-open');
      lightbox.setAttribute('aria-hidden', 'true');
      document.documentElement.classList.remove('workshop-evidence-lightbox-open');

      if (activeLightbox === lightbox) activeLightbox = null;
    }`;

const replacement = `    function closeLightbox(lightbox) {
      if (!lightbox) return;

      var image = lightbox.querySelector('[data-workshop-lightbox-image]');
      lightbox.classList.remove('is-open');
      lightbox.setAttribute('aria-hidden', 'true');
      document.documentElement.classList.remove('workshop-evidence-lightbox-open');

      if (image) {
        setTimeout(function() {
          if (!lightbox.classList.contains('is-open')) {
            image.removeAttribute('src');
          }
        }, 300);
      }

      if (activeLightbox === lightbox) activeLightbox = null;
    }`;

// normalize CRLF before replacing
content = content.replace(/\r\n/g, '\n');

if (content.includes(target)) {
  content = content.replace(target, replacement);
  fs.writeFileSync(path, content);
  console.log("Successfully fixed closeLightbox JS timing");
} else {
  console.log("target not found");
}
