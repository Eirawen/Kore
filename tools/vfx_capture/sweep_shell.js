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
  // grain SIZE sweep: uNoiseScale (higher = finer). 62 aliased into static
  // across three nested shells; find the size that reads as spray.
  const V=[[28,0.62],[38,0.62],[48,0.55],[62,0.48]];
  for(let i=0;i<V.length;i++){
    const [ns,op]=V[i];
    await p.evaluate(([ns,op])=>{ window.__shellSet('uNoiseScale',ns);
      window.__shellSet('uMistOpacity',op); window.__step(0); },[ns,op]);
    await p.waitForTimeout(200);
    const d=await p.evaluate(()=>window.__cap());
    fs.writeFileSync(path.join(out,'sweep_'+i+'.png'),Buffer.from(d.split(',')[1],'base64'));
    console.log('  variant',i,'noiseScale',ns,'opacity',op);
  }
  console.log('SWEPT');
  await b.close();
})();
