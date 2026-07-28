const { chromium } = require('/home/khaled/crescent/engine/browserClient/node_modules/playwright');
const fs=require('fs'), path=require('path');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--disable-gpu-sandbox','--no-sandbox']});
  const p=await b.newPage({viewport:{width:520,height:700}});
  await p.goto('http://localhost:8901/tools/water_elemental_test.html',{waitUntil:'load'});
  await p.waitForTimeout(5000);
  console.log('shellOK:', await p.evaluate(()=>window.__shellOK));
  await p.evaluate(()=>{ window.__freeze=true; window.__setWater(1.0); window.__setTime(1.7); });
  const out=path.join(__dirname,'output','water'); fs.mkdirSync(out,{recursive:true});
  // (threshold, opacity, rimGain) — lower threshold = more coverage
  const V=[[0.52,0.42,1.0],[0.44,0.80,1.4],[0.36,1.00,1.8],[0.28,1.00,2.4]];
  for(let i=0;i<V.length;i++){
    const [th,op,rg]=V[i];
    await p.evaluate(([th,op,rg])=>{ window.__shellSet('uThreshold',th);
      window.__shellSet('uMistOpacity',op); window.__shellSet('uRimGain',rg);
      window.__step(0); },[th,op,rg]);
    await p.waitForTimeout(200);
    const d=await p.evaluate(()=>window.__cap());
    fs.writeFileSync(path.join(out,'sweep_'+i+'.png'),Buffer.from(d.split(',')[1],'base64'));
    console.log('  variant',i,'threshold',th,'opacity',op,'rimGain',rg);
  }
  console.log('SWEPT');
  await b.close();
})();
