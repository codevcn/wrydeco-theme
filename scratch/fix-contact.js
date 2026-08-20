const fs = require('fs');
const path = 'sections/footer.liquid';
let content = fs.readFileSync(path, 'utf8');

const target = `.footer-custom__brand-panel .rte,
    .footer-custom__brand-panel p {
      margin-bottom: 8px;
    }`;

const addition = `.footer-custom__brand-panel .rte,
    .footer-custom__brand-panel p {
      margin-bottom: 8px;
    }

    .footer-custom__contact-title {
      text-align: center;
      margin-inline: auto;
    }

    .footer-custom__contact-title::after {
      margin-inline: auto;
    }

    .footer-custom__contact {
      width: 100%;
      max-width: 560px;
      margin-inline: auto;
      display: grid;
      gap: 0;
    }

    .footer-custom__contact li {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 12px;
      text-align: center;
    }

    .footer-custom__contact li > span:not(.footer-custom__contact-icon) {
      min-width: 0;
      text-align: center;
    }

    @media (max-width: 390px) {
      .footer-custom__contact li {
        align-items: flex-start;
      }
    }`;

content = content.replace(/\r\n/g, '\n');
if (content.includes(target)) {
  content = content.replace(target, addition);
  fs.writeFileSync(path, content);
  console.log("Successfully added contact us mobile centering.");
} else {
  console.log("target not found");
}
