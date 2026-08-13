const { chromium } = require('/home/khaled/crescent/engine/browserClient/node_modules/playwright');
(async()=>{
  const b=await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader',
    '--enable-unsafe-swiftshader','--disable-gpu-sandbox','--no-sandbox']});
  const p=await b.newPage({viewport:{width:400,height:560}});
  const logs=[];
  p.on('console',m=>{ const t=m.text(); if(/error|shader|glsl|compil|link|WebGL/i.test(t)) logs.push('['+m.type()+'] '+t.slice(0,600)); });
  p.on('pageerror',e=>logs.push('[pageerror] '+e.message.slice(0,400)));
  await p.goto('http://localhost:8901/tools/water_elemental_test.html',{waitUntil:'load'});
  await p.waitForTimeout(5000);
  const st=await p.evaluate(()=>{
    const m=window.__shells&&window.__shells.length;
    let bodyVisible=null, bodyMat=null;
    // find the body mesh (the one NOT in __shells)
    return { matOK:window.__matOK, shellOK:window.__shellOK, shells:m,
             errors:(window.__errors?window.__errors():[]).slice(0,4) };
  });
  console.log('matOK',st.matOK,'shellOK',st.shellOK,'shells',st.shells);
  console.log('page errors:', st.errors.length?st.errors.join(' | '):'none');
  console.log('shader logs:', logs.length?logs.slice(0,4).join('\n   '):'none');
  await b.close();
})();
