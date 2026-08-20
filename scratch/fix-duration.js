const fs = require('fs');
const path = 'sections/workshop-evidence.liquid';
let content = fs.readFileSync(path, 'utf8');

// Replace --duration-default with --timing-base everywhere
content = content.replace(/--duration-default/g, '--timing-base');

fs.writeFileSync(path, content);
console.log("Successfully replaced --duration-default with --timing-base");
