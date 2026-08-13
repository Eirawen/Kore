const { chromium } = require('/home/khaled/crescent/engine/browserClient/node_modules/playwright');
const fs=require('fs'), path=require('path');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--disable-gpu-sandbox','--no-sandbox']});
  const p=await b.newPage({viewport:{width:460,height:640}});
  await p.goto('http://localhost:8901/tools/water_elemental_test.html',{waitUntil:'load'});
  await p.waitForTimeout(5000);
  await p.evaluate(()=>{ window.__freeze=true; window.__setWater(1.0); window.__setTime(1.7); });
  const out=path.join(__dirname,'output','water'); fs.mkdirSync(out,{recursive:true});
  // glow, rim, pink
  // ISOLATE: is it the material or the AURA that killed her silhouette?
  // mistOpacity, glow, rim, pink
  const V=[['A  mist 0.000',0.000, 1.0,0.9,0.9],
           ['B  mist 0.038',0.038, 1.0,0.9,0.9],
           ['C  mist 0.075',0.075, 1.0,0.9,0.9],
           ['D  mist 0.112',0.112, 1.0,0.9,0.9],
           ['E  mist 0.150',0.150, 1.0,0.9,0.9]];
  for(let i=0;i<V.length;i++){
    const [nm,mo,g,r,k]=V[i];
    await p.evaluate(([mo,g,r,k])=>{ window.__shellSet('uMistOpacity',mo);
      window.__matSet('uCoreGlow',g);
      window.__matSet('uBodyRim',r); window.__matSet('uPink',k);
      window.__warm(0.6); },[mo,g,r,k]);
    await p.waitForTimeout(250);
    const d=await p.evaluate(()=>window.__cap());
    fs.writeFileSync(path.join(out,'read_'+i+'.png'),Buffer.from(d.split(',')[1],'base64'));
    console.log('  '+nm);
  }
  console.log('SWEPT'); await b.close();
})();
