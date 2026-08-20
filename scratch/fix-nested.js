const fs = require('fs');
const path = 'sections/footer.liquid';
let content = fs.readFileSync(path, 'utf8');

const target = `    @media (max-width: 390px) {
      .footer-custom__contact li {
        align-items: flex-start;
      }
    }`;

content = content.replace(/\r\n/g, '\n');
if (content.includes(target)) {
  content = content.replace(target, '');
  
  // insert before {% endstylesheet %}
  const endStyle = '{% endstylesheet %}';
  const newRule = `  @media (max-width: 390px) {\n    .footer-custom__contact li {\n      align-items: flex-start;\n    }\n  }\n`;
  content = content.replace(endStyle, newRule + endStyle);
  
  fs.writeFileSync(path, content);
  console.log("Successfully extracted nested media query");
} else {
  console.log("target not found");
}
