const { chromium } = require('/home/khaled/crescent/engine/browserClient/node_modules/playwright');
const fs=require('fs'), path=require('path');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--disable-gpu-sandbox','--no-sandbox']});
  const p=await b.newPage({viewport:{width:460,height:644}});
  p.on('pageerror',e=>console.log('[err]',e.message.slice(0,160)));
  await p.goto('http://localhost:8901/tools/water_elemental_test.html',{waitUntil:'load'});
  await p.waitForTimeout(6000);
  await p.evaluate(()=>{ window.__element('air'); window.__pretty(); window.__freeze=true;
                         window.__setWater(1.0);
                         // the beauty key is far too hot for something this pale
                         window.__dimLights(0.22); });
  const out=path.join(__dirname,'output','air'); fs.mkdirSync(out,{recursive:true});
  // mist opacity, body centre opacity
  // additive shells SATURATE — the fix is much lower per-shell opacity and a
  // cooler, dimmer mist colour. Wind is near-colourless; you see it through
  // what it carries, not as a lightbulb.
  const V=[[0.05,0.05,'#93a8bd'],[0.09,0.07,'#9db2c6'],
           [0.14,0.09,'#a8bccf'],[0.20,0.11,'#b3c6d8'],[0.28,0.14,'#c0d2e2']];
  for(const [i,[mo,bo,col]] of V.entries()){
    await p.evaluate(([mo,bo,col])=>{
      window.__shellSet('uMistOpacity',mo);
      window.__shellSet('uMistColor',col);
      window.__matSet('uCenterOpacity',bo); window.__matSet('uEdgeOpacity',bo*0.35);
      window.__matSet('uCoreGlow',0.10); window.__matSet('uBodyRim',0.55);
      window.__setTime(1.7); window.__warm(1.0);
    },[mo,bo,col]);
    await p.waitForTimeout(400);
    const d=await p.evaluate(()=>window.__cap());
    fs.writeFileSync(path.join(out,'air_'+i+'.png'),Buffer.from(d.split(',')[1],'base64'));
    console.log('  mist='+mo+' body='+bo+' col='+col);
  }
  console.log('DONE'); await b.close();
})();
