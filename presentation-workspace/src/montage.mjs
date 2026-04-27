const sharp = (await import('/Users/alandiaz/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/lib/index.js')).default;
const files = Array.from({length:10}, (_,i)=>`presentation-workspace/scratch/slide-${String(i+1).padStart(2,'0')}.png`);
const thumbs = await Promise.all(files.map(f => sharp(f).resize(384,216).png().toBuffer()));
const cols = 2, rows = 5, w = 384, h = 216, gap = 18;
const canvas = sharp({create:{width: cols*w+(cols-1)*gap, height: rows*h+(rows-1)*gap, channels:4, background:'#f2f4f6'}});
await canvas.composite(thumbs.map((input,idx)=>({input,left:(idx%cols)*(w+gap),top:Math.floor(idx/cols)*(h+gap)}))).png().toFile('presentation-workspace/scratch/montage.png');
