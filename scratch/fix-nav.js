const fs = require('fs');
const path = 'sections/footer.liquid';
let content = fs.readFileSync(path, 'utf8');

const target = `    .footer-custom__nav > div:nth-child(3) .footer-custom__menu {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px 20px;
    }`;

const addition = `    .footer-custom__nav > div:nth-child(3) .footer-custom__menu {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px 20px;
    }

    .footer-custom__nav .footer-custom__column,
    .footer-custom__nav .footer-custom__menu-col {
      min-width: 0;
      text-align: center;
    }

    .footer-custom__heading {
      text-align: center;
      margin-inline: auto;
    }

    .footer-custom__heading::after {
      margin-inline: auto;
    }

    .footer-custom__menu {
      justify-items: center;
      text-align: center;
    }

    .footer-custom__menu li,
    .footer-custom__menu a {
      width: fit-content;
      max-width: 100%;
      text-align: center;
      overflow-wrap: anywhere;
    }

    .footer-custom__nav > div:nth-child(3) .footer-custom__menu a {
      justify-self: center;
    }`;

content = content.replace(/\r\n/g, '\n');
if (content.includes(target)) {
  content = content.replace(target, addition);
  fs.writeFileSync(path, content);
  console.log("Successfully fixed mobile nav centering.");
} else {
  console.log("target not found");
}
