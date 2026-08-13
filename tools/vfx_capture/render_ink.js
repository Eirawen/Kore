const { chromium } = require('/home/khaled/crescent/engine/browserClient/node_modules/playwright');
const fs=require('fs'), path=require('path');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--disable-gpu-sandbox','--no-sandbox']});
  const p=await b.newPage({viewport:{width:820,height:1148}});
  p.on('pageerror',e=>console.log('[err]',e.message.slice(0,200)));
  await p.goto('http://localhost:8901/tools/water_elemental_test.html',{waitUntil:'load'});
  await p.waitForTimeout(6000);
  const ok=await p.evaluate(()=>{ const a=window.__element('ink'); const b=window.__paper('#efe7d6');
    window.__freeze=true; window.__setWater(1.0); window.__setTime(1.7); window.__warm(1.2); return a&&b; });
  console.log('ink applied:', ok);
  const out=path.join(__dirname,'output','ink'); fs.mkdirSync(out,{recursive:true});
  const BG=[['bluewash','#efe7d6','ink_bluewash'],
            ['crimrim_paper','#efe7d6','ink_crimson_rim'],
            ['crimrim_dark','#0a0a0c','ink_crimson_rim']];
  for(const [nm,bg,el] of BG){
    await p.evaluate(([bg,el])=>{ window.__element(el); window.__paper(bg); window.__warm(0.9); }, [bg,el]);
    await p.waitForTimeout(400);
    const d=await p.evaluate(()=>window.__cap());
    fs.writeFileSync(path.join(out,'ink_'+nm+'.png'),Buffer.from(d.split(',')[1],'base64'));
    console.log('  '+nm+'  bg='+bg+'  preset='+el);
  }
  console.log('DONE'); await b.close();
})();
