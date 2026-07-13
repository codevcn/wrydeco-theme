import { chromium } from '@playwright/test';
import { writeFileSync } from 'fs';
const OUT=process.argv[2];
const BASE='http://127.0.0.1:9292';
const PAGES=[['home','/'],['pdp','/products/contemporary-wooden-tree-bookcase-with-branch-display']];
const b=await chromium.launch();
const out={};
for(const [name,path] of PAGES){
  const page=await (await b.newContext({viewport:{width:1440,height:900}})).newPage();
  // capture response sizes via CDP-ish: use response event + body length header
  const t0=Date.now();
  await page.goto(BASE+path,{waitUntil:'load',timeout:60000});
  await page.waitForTimeout(3000); // let deferred/3rd-party load
  const data=await page.evaluate(()=>{
    const nav=performance.getEntriesByType('navigation')[0]||{};
    const res=performance.getEntriesByType('resource').map(r=>({
      name:r.name, type:r.initiatorType, dur:Math.round(r.duration),
      transfer:r.transferSize||0, enc:r.encodedBodySize||0, dec:r.decodedBodySize||0
    }));
    // render-blocking-ish: scripts in head without async/defer
    const headScripts=[...document.head.querySelectorAll('script[src]')].map(s=>({src:s.src, async:s.async, defer:s.defer}));
    const allScripts=[...document.querySelectorAll('script[src]')].map(s=>({src:s.src, async:s.async, defer:s.defer, inHead: !!s.closest('head')}));
    const inlineScripts=[...document.querySelectorAll('script:not([src])')];
    let inlineBytes=0; inlineScripts.forEach(s=>inlineBytes+=(s.textContent||'').length);
    const stylesheets=[...document.querySelectorAll('link[rel="stylesheet"]')].map(l=>l.href);
    return {
      nav:{ttfb:Math.round(nav.responseStart-nav.requestStart), domContentLoaded:Math.round(nav.domContentLoadedEventEnd-nav.startTime), load:Math.round(nav.loadEventEnd-nav.startTime), transferSize:nav.transferSize, docSize:nav.decodedBodySize},
      res, allScripts, inlineCount:inlineScripts.length, inlineBytes, stylesheets, htmlBytes:document.documentElement.outerHTML.length
    };
  });
  out[name]={wallClockMs:Date.now()-t0, ...data};
  await page.close();
}
await b.close();
writeFileSync(OUT, JSON.stringify(out,null,1));
// quick console summary
for(const [name,d] of Object.entries(out)){
  const byType={};
  let totalTransfer=0, totalEnc=0;
  for(const r of d.res){ const t=r.type||'other'; byType[t]=byType[t]||{n:0,enc:0,transfer:0}; byType[t].n++; byType[t].enc+=r.enc; byType[t].transfer+=r.transfer; totalTransfer+=r.transfer; totalEnc+=r.enc; }
  console.log(`\n== ${name} ==`);
  console.log('requests:', d.res.length, '| TTFB(ms):', d.nav.ttfb, '| DCL:', d.nav.domContentLoaded, '| Load:', d.nav.load);
  console.log('HTML bytes:', d.htmlBytes, '| inline scripts:', d.inlineCount, '(~'+d.inlineBytes+' chars)', '| ext scripts:', d.allScripts.length, '| stylesheets:', d.stylesheets.length);
  console.log('total transfer:', Math.round(totalTransfer/1024)+'KB', '| total encoded:', Math.round(totalEnc/1024)+'KB');
  for(const [t,v] of Object.entries(byType).sort((a,b)=>b[1].enc-a[1].enc)) console.log(`   ${t}: ${v.n} req, ${Math.round(v.enc/1024)}KB`);
}
