import { chromium } from '@playwright/test';
const BASE='http://127.0.0.1:9292';
const PROD='/products/contemporary-wooden-tree-bookcase-with-branch-display';
const COLL_EMPTY='/collections/all?filter.v.price.gte=999999'; // force empty to reveal empty-state buttons
const pages=['/','/pages/about-us','/pages/customization','/pages/faq','/pages/care-guide','/pages/contact','/collections/all',COLL_EMPTY,PROD,'/search?q=wood'];
const b=await chromium.launch();
const page=await (await b.newContext({viewport:{width:1440,height:900}})).newPage();
const all=[];
for(const P of pages){
  try{
    await page.goto(BASE+P,{waitUntil:'networkidle',timeout:60000});
    await page.waitForTimeout(800);
    const a=await page.$$eval('a[class*="btn"],a[class*="button"],a[class*="cta"]',els=>els.map(e=>({t:(e.textContent||'').replace(/\s+/g,' ').trim().slice(0,32),h:e.href,c:e.getAttribute('class')||''})));
    for(const x of a) all.push({p:P,...x});
    console.log(`[${P}] ${a.length} anchors: `+a.map(x=>x.c.split(' ')[0]).join(', '));
  }catch(e){ console.log('FAIL',P,e.message); }
}
// unique internal testable
const norm=h=>h.split('#')[0];
const skip=h=>!h||/^javascript:|^mailto:|^tel:/.test(h);
const uniq=new Map();
for(const f of all){ if(skip(f.h))continue; const k=norm(f.h); if(!uniq.has(k))uniq.set(k,f); }
const results=[];
for(const [u,meta] of uniq){
  try{ const r=await page.goto(u,{waitUntil:'domcontentloaded',timeout:45000}); const st=r?r.status():'(no-nav)'; const t=await page.title();
    results.push({url:u.replace(BASE,''),status:st,is404:st===404||/not found|404/i.test(t),from:meta.p,text:meta.t,cls:meta.c.split(' ')[0]});
  }catch(e){ results.push({url:u.replace(BASE,''),status:'ERR',is404:true,from:meta.p,text:meta.t,cls:meta.c.split(' ')[0],err:e.message}); }
}
console.log('\n=== UNIQUE LINK TARGETS ('+uniq.size+') ===');
for(const r of results) console.log(`${r.is404?'❌404':'✅'+r.status}  ${r.url}   [${r.cls} | "${r.text}" @ ${r.from}]`);
await b.close();
