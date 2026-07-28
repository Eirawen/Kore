const { chromium } = require('/home/khaled/crescent/engine/browserClient/node_modules/playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const browser = await chromium.launch({ args:[
    '--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader',
    '--disable-gpu-sandbox','--no-sandbox'] });
  const page = await browser.newPage({ viewport:{width:520,height:700} });
  const logs=[];
  page.on('console', m=>logs.push('['+m.type()+'] '+m.text().slice(0,300)));
  page.on('pageerror', e=>logs.push('[pageerror] '+e.message.slice(0,300)));
  const url='http://localhost:8901/tools/water_elemental_test.html';
  await page.goto(url,{waitUntil:'load'});
  await page.waitForTimeout(5000);
  const st = await page.evaluate(()=>({
    matOK: window.__matOK, loaded: window.__loaded,
    bounds: window.__bounds, errors: (window.__errors?window.__errors():[]),
    progOK: window.__progOK ? window.__progOK() : 'n/a'
  }));
  console.log('matOK   :', st.matOK);
  console.log('loaded  :', st.loaded);
  console.log('bounds  :', JSON.stringify(st.bounds));
  console.log('progLink:', st.progOK);
  console.log('errors  :', st.errors.length ? st.errors.join('\n           ') : 'none');
  const shaderLogs = logs.filter(l=>/shader|glsl|compil|link|program|THREE/i.test(l));
  console.log('shaderLogs:', shaderLogs.length ? shaderLogs.slice(0,6).join('\n           ') : 'none');
  const out = path.join(__dirname,'output','water');
  fs.mkdirSync(out,{recursive:true});
  await page.evaluate(()=>{ window.__freeze=true; });
  // let the droplet field populate before capturing
  await page.evaluate(()=>{ window.__initShed && window.__initShed(); });
  const levels=[1.0,0.65,0.35,0.10];
  for (let i=0;i<levels.length;i++){
    await page.evaluate(([w,t])=>{ window.__setWater(w); window.__setTime(t); }, [levels[i], 1.7]);
    await page.evaluate(()=>{ window.__warm(2.0); });   // populate droplets
    await page.waitForTimeout(220);
    const d = await page.evaluate(()=>window.__cap());
    fs.writeFileSync(path.join(out,'water_'+i+'.png'), Buffer.from(d.split(',')[1],'base64'));
  }
  // a few time samples at full water, to check the wave animates
  for (let i=0;i<3;i++){
    await page.evaluate(([w,t])=>{ window.__setWater(w); window.__setTime(t); window.__step(0); },
                        [1.0, i*1.1]);
    await page.waitForTimeout(200);
    const d = await page.evaluate(()=>window.__cap());
    fs.writeFileSync(path.join(out,'time_'+i+'.png'), Buffer.from(d.split(',')[1],'base64'));
  }
  // scoop burst frame
  await page.evaluate(()=>{ window.__setWater(0.8); window.__warm(0.8);
                            window.__scoop(0.22,-0.12,0.10); window.__warm(0.20); });
  await page.waitForTimeout(200);
  { const d=await page.evaluate(()=>window.__cap());
    fs.writeFileSync(path.join(out,'scoop.png'), Buffer.from(d.split(',')[1],'base64')); }
  console.log('CAPTURED -> '+out);
  await browser.close();
})();
