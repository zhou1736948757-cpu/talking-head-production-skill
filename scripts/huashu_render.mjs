// Independent, local-only executor for a reviewed external Huashu clip.html runtime.
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {createHash} from 'node:crypto';

const args={};for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].replace(/^--/,'')]=process.argv[i+1];
for(const key of ['engine','spec','out','chrome','package-root'])if(!args[key])throw new Error(`Missing --${key}`);
const engine=await fs.realpath(args.engine),spec=JSON.parse(await fs.readFile(args.spec,'utf8'));
const allowed=new Set(['t2_keynote_ui','y3_whiteboard','y5_kinetic_type']);
if(!allowed.has(spec.grammar))throw new Error('Only reviewed clip grammars are supported');
if(spec.grammar==='y3_whiteboard'&&!['hidden','original'].includes(spec.koubo_pen))throw new Error('Choose whiteboard pen explicitly');
if(!Number.isInteger(spec.fps)||spec.fps<1||spec.fps>60||!(spec.duration>0&&spec.duration<=8))throw new Error('Invalid clip clock');
if(![spec.width,spec.height].every(n=>Number.isInteger(n)&&n>=64&&n<=1920&&n%2===0))throw new Error('Invalid Canvas');
const inputs=new Map();
for(const cue of spec.cues||[]) {
  if(cue.frames)throw new Error('Character/frame generation is outside this adapter');
  if(cue.image) {
    if(/^(?:https?:|data:|file:)/i.test(cue.image))throw new Error('Only explicitly supplied local images are accepted');
    const source=await fs.realpath(path.resolve(path.dirname(args.spec),cue.image));
    if(!['.png','.jpg','.jpeg','.webp'].includes(path.extname(source).toLowerCase()))throw new Error('Unsupported image');
    const key=`/inputs/${inputs.size}${path.extname(source)}`;inputs.set(key,source);cue.image=key;
  }
}
const types={'.html':'text/html','.js':'text/javascript','.woff':'font/woff','.woff2':'font/woff2','.ttf':'font/ttf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp'};
let server,browser,encoder;
const errors=[],warnings=[],blocked=[];
try {
  server=http.createServer(async(req,res)=>{
    try {
      const pathname=new URL(req.url,'http://localhost').pathname;
      if(pathname==='/favicon.ico'){res.writeHead(204);return res.end();}
      let file=inputs.get(pathname);
      if(!file) {
        const relative=decodeURIComponent(pathname).replace(/^\//,'');
        if(!(relative==='clip.html'||relative==='clip.js'||relative===`clips/${spec.grammar}.js`||relative.startsWith('lib/')))throw new Error('Not admitted');
        file=await fs.realpath(path.resolve(engine,relative));
        if(!file.startsWith(engine+path.sep)||!['.html','.js','.woff','.woff2','.ttf'].includes(path.extname(file)))throw new Error('Not admitted');
      }
      const bytes=await fs.readFile(file);res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(bytes);
    }catch{res.writeHead(404);res.end();}
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const origin=`http://127.0.0.1:${server.address().port}`;
  const require=createRequire(path.join(path.resolve(args['package-root']),'package.json'));
  const puppeteer=require('puppeteer-core');
  browser=await puppeteer.launch({executablePath:path.resolve(args.chrome),headless:true});
  const page=await browser.newPage();await page.setViewport({width:spec.width,height:spec.height,deviceScaleFactor:1});
  await page.setRequestInterception(true);
  page.on('request',request=>{
    const url=request.url();if(url.startsWith(origin+'/'))request.continue();else{blocked.push(url.split('?')[0]);request.abort();}
  });
  page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')errors.push(message.text());if(message.type()==='warn'||message.type()==='warning')warnings.push(message.text());});
  await page.evaluateOnNewDocument(value=>{window.CLIP_SPEC=value;},spec);
  await page.goto(origin+'/clip.html?render=1',{waitUntil:'networkidle0',timeout:30000});
  await page.waitForFunction(()=>window.__ready===true||!!window.__bootFailed,{timeout:30000});
  const failure=await page.evaluate(()=>window.__bootFailed||null);if(failure)throw new Error(failure);
  // Explicit adapter option: keep animated line reveals, hide only the decorative pen.
  // The external installation is never modified. Original pen movement needs visual review.
  if(spec.grammar==='y3_whiteboard'&&spec.koubo_pen==='hidden')await page.evaluate(()=>{
    if(typeof DG==='undefined'||typeof DG.pen!=='function')throw new Error('Reviewed pen interface changed');
    DG.pen=()=>{};
  });
  const capture=async(frame)=>page.evaluate(async t=>{await window.prepare(t);window.renderFrame(t);return window.__canvas.toDataURL('image/png').split(',')[1];},frame/spec.fps);
  const n=Math.round(spec.duration*spec.fps),sample=Math.min(n-1,Math.floor(n*.6));
  const first=await capture(sample);await capture(0);const second=await capture(sample);
  if(first!==second)throw new Error('Repeated semantic time produced different pixels');
  const out=path.resolve(args.out);await fs.mkdir(path.dirname(out),{recursive:true});
  encoder=spawn('ffmpeg',['-v','error','-y','-f','image2pipe','-framerate',String(spec.fps),'-c:v','png','-i','pipe:0','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-an','-movflags','+faststart',out],{stdio:['pipe','ignore','pipe']});
  let encoderErrors='';encoder.stderr.on('data',d=>encoderErrors+=d.toString());
  const completed=once(encoder,'close');const frameSamples=[],renderMs=[];
  const sampleFrames=new Set([0,Math.min(n-1,Math.round(.3*spec.fps)),Math.floor(n/2),n-1]);
  for(let frame=0;frame<n;frame++) {
    const begin=performance.now();const encoded=await capture(frame);renderMs.push(performance.now()-begin);
    const bytes=Buffer.from(encoded,'base64');
    if(sampleFrames.has(frame))frameSamples.push({frame,sha256:createHash('sha256').update(bytes).digest('hex')});
    if(!encoder.stdin.write(bytes))await once(encoder.stdin,'drain');
  }
  encoder.stdin.end();const [code]=await completed;if(code!==0)throw new Error(encoderErrors||'FFmpeg failed');
  if(errors.length||blocked.length||warnings.some(w=>/缺字|safe.*忽略/.test(w)))throw new Error(JSON.stringify({errors,warnings,blocked}));
  const facts={format:'koubo-huashu-render@1',frames:n,duration:n/spec.fps,dimensions:[spec.width,spec.height],
    grammar:spec.grammar,whiteboard_pen:spec.koubo_pen||null,deterministic_sample:true,frame_samples:frameSamples,sampled_frames_differ:new Set(frameSamples.map(s=>s.sha256)).size>1,
    mean_capture_ms:renderMs.reduce((a,b)=>a+b,0)/renderMs.length,errors,warnings,external_requests:blocked.length,
    upstream_qa_executed:false,audio_generated:false,fonts:'external local Huashu installation; not redistributed'};
  await fs.writeFile(out+'.qa.json',JSON.stringify(facts,null,2)+'\n');console.log(JSON.stringify(facts));
} finally {
  if(encoder&&encoder.exitCode===null)encoder.kill();
  if(browser)await browser.close();
  if(server)await new Promise(resolve=>server.close(resolve));
}
