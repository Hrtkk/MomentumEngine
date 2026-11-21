import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {marked} from '/Users/khritik/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/marked/lib/marked.esm.js';
import sharp from '/Users/khritik/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/lib/index.js';
const dir=path.dirname(fileURLToPath(import.meta.url));
const files=['01-executive-brief.md','02-comprehensive-report.md','03-metric-glossary.md','04-peers-and-history.md','05-scenarios.md','06-risk-register.md','07-evidence-and-calculations.md'];
const labels=['Briefing','Full analysis','Metric glossary','Peers & history','Scenarios','Risk register','Evidence'];
let body='';
for (let i=0;i<files.length;i++) {
 let html=marked.parse(fs.readFileSync(path.join(dir,files[i]),'utf8'));
 for (const f of files) html=html.replaceAll(`href="${f}"`,`href="#s${files.indexOf(f)}"`);
 html=html.replace(/<table>/g,'<div class="table-scroll"><table>').replace(/<\/table>/g,'</table></div>');
 for(const img of ['history.svg','scenario-prices.svg'])html=html.replaceAll(`src="${img}"`,`src="data:image/svg+xml;base64,${fs.readFileSync(path.join(dir,img)).toString('base64')}"`);
 body+=`<section id="s${i}">${html}</section>`;
}
const nav=files.map((f,i)=>`<a href="#s${i}">${labels[i]}</a>`).join('');
const css=`*{box-sizing:border-box}body{margin:0;background:#eef2f6;color:#203047;font:16px/1.65 -apple-system,BlinkMacSystemFont,Arial,sans-serif}header{background:#142d48;color:white;padding:40px max(5%,calc((100% - 1120px)/2))}header p{color:#cfdeed}nav{background:#fff;display:flex;flex-wrap:wrap;gap:12px;padding:15px 5%;border-bottom:1px solid #ccd6e2}nav a{padding:5px 10px;text-decoration:none;font-size:14px}main{max-width:1200px;margin:30px auto;padding:0 24px}section{background:#fff;border:1px solid #d9e1e9;border-radius:8px;padding:36px;margin-bottom:28px;scroll-margin-top:20px}h1{font-size:29px;line-height:1.25;color:#153d63}h2{font-size:23px;margin-top:34px;color:#174d77}h3{font-size:19px;color:#174d77}a{color:#136bad}p,li{max-width:100ch}.table-scroll{overflow-x:auto;margin:20px 0}table{width:100%;border-collapse:collapse;font-size:13px;line-height:1.5}th{background:#e9f0f7;text-align:left;color:#173b60}td,th{padding:11px;border-bottom:1px solid #d9e1e9;vertical-align:top;min-width:80px}tr:nth-child(even) td{background:#f8fafc}img{display:block;max-width:100%;height:auto;margin:24px auto}code{background:#edf2f6;padding:2px 4px}footer{padding:30px;text-align:center;font-size:13px;color:#52677e}@media(max-width:650px){section{padding:18px}main{padding:0 10px}h1{font-size:25px}}@media print{body{background:white;font-size:10pt}nav{display:none}header{padding:20px}main{margin:0;max-width:none;padding:0}section{border:0;page-break-before:always;padding:12px}section:first-child{page-break-before:auto}.table-scroll{overflow:visible}table{font-size:8pt}td,th{padding:5px;min-width:0}h2,h3{break-after:avoid}tr,img{break-inside:avoid}}`;
fs.writeFileSync(path.join(dir,'BSE-research-report.html'),`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BSE — Interpretation & Intelligence</title><style>${css}</style></head><body><header><div>COMPANY RESEARCH / 14 OCTOBER 2026</div><h1 style="color:white">BSE Ltd: earnings durability and valuation</h1><p>Seven-part research report · Explicit evidence gaps · Conditional scenarios</p></header><nav aria-label="Report sections">${nav}</nav><main>${body}</main><footer>Prepared from the dated BSE evidence pack. Research remains incomplete; no buy or sell recommendation.</footer></body></html>`);
for(const f of ['history','scenario-prices']) await sharp(path.join(dir,f+'.svg')).png().toFile(path.join(dir,f+'.png'));
console.log('Built self-contained report HTML and two chart previews.');
