const fs = require('fs');
const path = 'sections/footer.liquid';
let content = fs.readFileSync(path, 'utf8');

const target = `@media (max-width: 48rem) {
    .footer-custom__inner {
      padding-inline: var(--layout-padding-mobile);
    }

    .footer-custom__main {
      gap: var(--sp-7);
      padding-top: var(--sp-8);
      padding-bottom: var(--sp-8);
    }

    .footer-custom__brand-panel {
      text-align: left;
    }

    .footer-custom__nav {
      grid-template-columns: minmax(0, 1fr);
      gap: var(--sp-7);
    }

    .footer-custom__newsletter {
      padding-top: var(--sp-7);
    }

    .footer-custom__input-group {
      grid-template-columns: minmax(0, 1fr);
    }

    .footer-custom__submit {
      min-height: 50px;
    }

    .footer-custom__follow-on-shop {
      max-width: none;
    }

    .footer-custom__social-wrap {
      flex-direction: column;
      gap: var(--sp-4);
    }

    .footer-custom__payments {
      width: min(100%, 320px);
      gap: 6px;
    }

    .footer-custom__payment-icon svg {
      width: 38px;
    }

    .footer-custom__copyright {
      white-space: normal;
    }
  }`;

const replacement = `@media (max-width: 48rem) {
    .footer-custom__inner {
      padding-inline: var(--layout-padding-mobile);
    }

    .footer-custom__main {
      gap: 32px;
      padding-top: var(--sp-6);
      padding-bottom: var(--sp-6);
    }

    .footer-custom__brand-panel {
      text-align: left;
      width: 100%;
    }

    .footer-custom__brand-panel .rte,
    .footer-custom__brand-panel p {
      margin-bottom: 8px;
    }

    .footer-custom__nav {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 28px 24px;
    }
    
    .footer-custom__menu {
      gap: 12px;
    }

    .footer-custom__nav > div:nth-child(3),
    .footer-custom__nav > .footer-custom__menu-col:nth-child(3),
    .footer-custom__nav > .footer-custom__column:nth-child(3) {
      grid-column: 1 / -1;
    }

    .footer-custom__nav > div:nth-child(3) .footer-custom__menu {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px 20px;
    }

    .footer-custom__newsletter {
      padding-top: var(--sp-6);
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .footer-custom__newsletter-title {
      text-align: center;
      margin-bottom: var(--sp-3);
    }

    .footer-custom__newsletter-title::after {
      margin-inline: auto;
    }

    .footer-custom__newsletter-copy {
      max-width: 340px;
      margin-inline: auto;
      text-align: center;
      margin-bottom: var(--sp-4);
    }

    .footer-custom__form {
      width: 100%;
      max-width: 550px;
      margin-inline: auto;
    }

    .footer-custom__input-group {
      grid-template-columns: minmax(0, 1fr);
    }
    
    .footer-custom__input-group input,
    .footer-custom__input-group button {
      width: 100%;
    }

    .footer-custom__localization {
      display: flex;
      justify-content: center;
      width: 100%;
    }

    .footer-custom__submit {
      min-height: 50px;
    }

    .footer-custom__follow-on-shop {
      max-width: none;
      margin-inline: auto;
    }

    .footer-custom__social-wrap {
      flex-direction: column;
      align-items: center;
      gap: var(--sp-4);
    }
    
    .footer-custom__social {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 10px;
    }
    
    .footer-custom__bottom-inner {
      text-align: center;
    }

    .footer-custom__payments {
      width: min(100%, 320px);
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      margin-inline: auto;
      gap: 6px;
    }

    .footer-custom__payment-icon svg {
      width: 38px;
    }

    .footer-custom__copyright {
      white-space: normal;
    }
  }`;

// normalize CRLF before replacing
content = content.replace(/\r\n/g, '\n');

if (content.includes(target)) {
  content = content.replace(target, replacement);
  fs.writeFileSync(path, content);
  console.log("Successfully updated mobile footer css");
} else {
  console.log("target not found");
}
