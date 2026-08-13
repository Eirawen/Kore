const { chromium } = require('/home/khaled/crescent/engine/browserClient/node_modules/playwright');
const fs=require('fs'), path=require('path');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--disable-gpu-sandbox','--no-sandbox']});
  const p=await b.newPage({viewport:{width:900,height:1260},deviceScaleFactor:1});
  p.on('pageerror',e=>console.log('[err]',e.message.slice(0,200)));
  await p.goto('http://localhost:8901/tools/water_elemental_test.html',{waitUntil:'load'});
  await p.waitForTimeout(6000);
  const EL=process.env.PRETTY_EL||'water';
  await p.evaluate((el)=>{ window.__element(el); window.__pretty();
                         window.__freeze=true; window.__setWater(1.0); }, EL);
  const out=path.join(__dirname,'output','pretty'); fs.mkdirSync(out,{recursive:true});
  await p.evaluate((el)=>{ window.__PRETTY_EL=el; }, EL);
  const V=(process.env.PRETTY_SET==='all')
    ? [['A',0.000],['B',0.038],['C',0.075],['D',0.112],['E',0.150]]
    : (process.env.PRETTY_SET==='bd'
        ? [['B',0.038],['D',0.112]]
        : (process.env.PRETTY_SET==='graded'
            ? [['GRADED',-1]]              // -1 = use the material's own defaults
            : [['A',0.000],['C',0.075],['E',0.150]]));
  for(const [nm,mo] of V){
    await p.evaluate(([mo])=>{
      if(mo>=0) window.__shellSet('uMistOpacity',mo);
      if(window.__PRETTY_EL==='water'){
        window.__matSet('uCoreGlow',1.0); window.__matSet('uBodyRim',0.9);
        window.__matSet('uPink',0.9); window.__matSet('uPinkEmissive',0.55);
      }
      window.__setTime(1.7); window.__warm(1.0);
    },[mo]);
    await p.waitForTimeout(700);
    const d=await p.evaluate(()=>window.__cap());
    fs.writeFileSync(path.join(out,EL+'_'+nm+'.png'),Buffer.from(d.split(',')[1],'base64'));
    console.log('  rendered '+nm+'  mist='+mo);
  }
  console.log('PRETTY DONE'); await b.close();
})();
