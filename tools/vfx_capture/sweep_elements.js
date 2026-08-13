const { chromium } = require('/home/khaled/crescent/engine/browserClient/node_modules/playwright');
const fs=require('fs'), path=require('path');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--disable-gpu-sandbox','--no-sandbox']});
  const p=await b.newPage({viewport:{width:440,height:620}});
  const logs=[]; p.on('pageerror',e=>logs.push(e.message.slice(0,200)));
  await p.goto('http://localhost:8901/tools/water_elemental_test.html',{waitUntil:'load'});
  await p.waitForTimeout(5000);
  await p.evaluate(()=>{ window.__freeze=true; window.__setWater(1.0); window.__setTime(1.7); });
  const out=path.join(__dirname,'output','water'); fs.mkdirSync(out,{recursive:true});
  for (const [i,el] of ['water','air','earth','fire'].entries()){
    const ok=await p.evaluate((e)=>{ const r=window.__element(e); window.__warm(0.9); return r; }, el);
    await p.waitForTimeout(260);
    const d=await p.evaluate(()=>window.__cap());
    fs.writeFileSync(path.join(out,'el_'+i+'.png'),Buffer.from(d.split(',')[1],'base64'));
    console.log('  '+el+'  applied='+ok);
  }
  if(logs.length) console.log('ERRORS:', logs.slice(0,3).join(' | '));
  console.log('DONE'); await b.close();
})();
