const {
  Presentation,
  PresentationFile,
  row,
  column,
  grid,
  panel,
  text,
  rule,
  fill,
  hug,
  fixed,
  wrap,
  grow,
  fr,
  auto,
  drawSlideToCtx,
} = await import('@oai/artifact-tool');
const { Canvas } = await import('../node_modules/@oai/artifact-tool/node_modules/skia-canvas/lib/index.js');

const OUT = new URL('../output/output.pptx', import.meta.url).pathname;
const SCRATCH = new URL('../scratch/', import.meta.url).pathname;

const W = 1920;
const H = 1080;
const C = {
  ink: '#1E2328',
  slate: '#53616E',
  mist: '#F3F6F8',
  line: '#CBD5DE',
  blue: '#236A8E',
  moss: '#2F6F5E',
  rust: '#B5532A',
  gold: '#D79A2B',
  white: '#FFFFFF',
  charcoal: '#111827',
};

const pres = Presentation.create({ slideSize: { width: W, height: H } });

function addSlide(bg = C.mist) {
  const s = pres.slides.add();
  s.background.fill = bg;
  return s;
}

function titleBlock(title, kicker, subtitle, opts = {}) {
  return column({ name: opts.name || 'title-block', width: fill, height: hug, gap: 14, columnSpan: opts.columnSpan }, [
    kicker ? text(kicker.toUpperCase(), { name: 'kicker', width: fill, height: hug, style: { fontSize: 18, bold: true, color: opts.kickerColor || C.blue, letterSpacing: 1.4 } }) : null,
    text(title, { name: 'title', width: wrap(opts.titleWidth || 1280), height: hug, style: { fontSize: opts.titleSize || 62, bold: true, color: opts.titleColor || C.ink } }),
    subtitle ? text(subtitle, { name: 'subtitle', width: wrap(opts.subtitleWidth || 1120), height: hug, style: { fontSize: opts.subtitleSize || 25, color: opts.subtitleColor || C.slate, lineSpacing: 1.12 } }) : null,
  ].filter(Boolean));
}

function footer(label = 'MemoryOS runbook') {
  return row({ name: 'footer', width: fill, height: hug, align: 'center' }, [
    rule({ name: 'footer-rule', width: fixed(120), stroke: C.line, weight: 2 }),
    text(label, { name: 'footer-label', width: hug, height: hug, style: { fontSize: 14, color: '#7A8793' } }),
  ]);
}

function chip(label, color = C.blue) {
  return panel({ name: `chip-${label}`, width: hug, height: fixed(40), padding: { x: 16, y: 8 }, fill: '#FFFFFF', stroke: color, borderRadius: 10 },
    text(label, { name: `chip-text-${label}`, width: hug, height: hug, style: { fontSize: 18, bold: true, color } })
  );
}

function stepNode(number, label, detail, color = C.blue) {
  return row({ name: `step-${number}`, width: fill, height: fixed(84), gap: 18, align: 'center' }, [
    panel({ name: `step-dot-${number}`, width: fixed(44), height: fixed(44), padding: 0, fill: color, borderRadius: 22 },
      text(String(number), { name: `step-num-${number}`, width: fill, height: fill, style: { fontSize: 19, bold: true, color: C.white, textAlign: 'center', verticalAlign: 'middle' } })
    ),
    column({ name: `step-copy-${number}`, width: fill, height: fill, gap: 2, justify: 'center' }, [
      text(label, { name: `step-label-${number}`, width: fill, height: hug, style: { fontSize: 22, bold: true, color: C.ink } }),
      text(detail, { name: `step-detail-${number}`, width: wrap(650), height: hug, style: { fontSize: 14, color: C.slate } }),
    ]),
  ]);
}

function command(textValue) {
  return panel({ name: `cmd-${textValue.slice(0, 12)}`, width: fill, height: hug, padding: { x: 14, y: 6 }, fill: C.charcoal, borderRadius: 8 },
    text(textValue, { name: `cmd-text-${textValue.slice(0, 12)}`, width: fill, height: hug, style: { fontSize: 15, fontFace: 'Menlo', color: '#D8F3E5' } })
  );
}

function metric(label, value, color = C.blue) {
  return column({ name: `metric-${label}`, width: fill, height: hug, gap: 4 }, [
    text(value, { name: `metric-value-${label}`, width: fill, height: hug, style: { fontSize: 48, bold: true, color } }),
    text(label, { name: `metric-label-${label}`, width: fill, height: hug, style: { fontSize: 18, color: C.slate } }),
  ]);
}

function smallCard(title, body, color = C.blue) {
  return panel({ name: `card-${title}`, width: fill, height: hug, padding: { x: 24, y: 22 }, fill: C.white, stroke: C.line, borderRadius: 10 },
    column({ width: fill, height: hug, gap: 8 }, [
      text(title, { width: fill, height: hug, style: { fontSize: 26, bold: true, color } }),
      text(body, { width: fill, height: hug, style: { fontSize: 19, color: C.slate, lineSpacing: 1.1 } }),
    ])
  );
}

// 1 cover
{
  const s = addSlide(C.ink);
  s.compose(grid({ name: 'cover-root', width: fill, height: fill, columns: [fr(1.05), fr(0.95)], rows: [fr(1)], padding: { x: 88, y: 76 }, columnGap: 64 }, [
    column({ name: 'cover-left', width: fill, height: fill, gap: 30, justify: 'center' }, [
      text('MEMORYOS', { name: 'cover-kicker', width: fill, height: hug, style: { fontSize: 22, bold: true, color: '#93D1C1', letterSpacing: 2.2 } }),
      text('How to run the local memory engine', { name: 'cover-title', width: wrap(900), height: hug, style: { fontSize: 82, bold: true, color: C.white, lineSpacing: 0.96 } }),
      text('A runbook for capture, indexing, search, privacy, and the menu bar workflow.', { name: 'cover-subtitle', width: wrap(780), height: hug, style: { fontSize: 27, color: '#C6D2DC', lineSpacing: 1.12 } }),
      row({ name: 'cover-chips', width: fill, height: hug, gap: 12 }, [chip('macOS', '#93D1C1'), chip('FastAPI', '#89B8F2'), chip('React', '#F2C67C')]),
    ]),
    column({ name: 'cover-right', width: fill, height: fill, gap: 18, justify: 'center' }, [
      command('curl -fsSL https://memoryos-mac.netlify.app/install.sh | bash'),
      command('scripts/install_memoryos.sh'),
      command('open http://127.0.0.1:5173'),
      command('Open the MemoryOS menu bar icon'),
    ]),
  ]), { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 });
}

// 2 where we are
{
  const s = addSlide();
  s.compose(column({ name: 'root', width: fill, height: fill, padding: { x: 86, y: 70 }, gap: 42 }, [
    titleBlock('The software is runnable; the memory starts local', 'Current state', 'All seven local-development phases are implemented. The next unlock is collecting real captures and labeling enough examples to train stronger models.'),
    grid({ name: 'metrics', width: fill, height: hug, columns: [fr(1), fr(1), fr(1), fr(1)], columnGap: 34 }, [
      metric('Roadmap phases implemented', '7 / 7', C.moss),
      metric('Current captures', '0', C.rust),
      metric('Local services', '3', C.blue),
      metric('GitHub commits', '2', C.gold),
    ]),
    grid({ name: 'state-table', width: fill, height: hug, columns: [fr(1), fr(1), fr(1)], columnGap: 22 }, [
      smallCard('Built', 'Daemon, backend, web UI, ML scripts, menu bar app, privacy controls, docs.', C.moss),
      smallCard('Running', 'Backend on :8765, web UI on :5173, menu bar app in macOS.', C.blue),
      smallCard('Next data step', 'Run the daemon, grant Accessibility, collect captures, label keep/noise.', C.rust),
    ]),
    footer('Status after Phase 6'),
  ]), { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 });
}

// 3 architecture
{
  const s = addSlide(C.white);
  const nodes = [
    ['1', 'Capture', 'daemon / extension', C.moss],
    ['2', 'Store', 'SQLite', C.blue],
    ['3', 'Learn', 'noise + embeddings', C.gold],
    ['4', 'Index', 'TF-IDF or FAISS', C.blue],
    ['5', 'Serve', 'FastAPI localhost', C.rust],
    ['6', 'Use', 'web + menu bar', C.moss],
  ];
  s.compose(column({ name: 'root', width: fill, height: fill, padding: { x: 80, y: 68 }, gap: 42 }, [
    titleBlock('How MemoryOS works', 'Architecture', 'Everything important runs locally: capture writes to SQLite, the ML layer indexes non-noise content, and the UI searches through the local backend.'),
    row({ name: 'pipeline', width: fill, height: fixed(310), gap: 18, align: 'center' }, nodes.map(([num, title, body, color]) =>
      column({ name: `node-${num}`, width: grow(1), height: fill, gap: 12, justify: 'center', align: 'center' }, [
        panel({ width: fixed(72), height: fixed(72), fill: color, borderRadius: 36 }, text(num, { width: fill, height: fill, style: { fontSize: 28, bold: true, color: C.white, textAlign: 'center', verticalAlign: 'middle' } })),
        text(title, { width: fill, height: hug, style: { fontSize: 27, bold: true, color: C.ink, textAlign: 'center' } }),
        text(body, { width: fill, height: hug, style: { fontSize: 17, color: C.slate, textAlign: 'center' } }),
      ])
    )),
    rule({ width: fill, stroke: C.line, weight: 2 }),
    grid({ name: 'below', width: fill, height: hug, columns: [fr(1), fr(1)], columnGap: 44 }, [
      smallCard('Local-first boundary', 'Backend binds to 127.0.0.1. Personal captures stay in SQLite unless you export them.', C.moss),
      smallCard('Two search modes', 'TF-IDF works today. sentence-transformers + FAISS becomes useful after real data collection.', C.blue),
    ]),
  ]), { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 });
}

// 4 run locally
{
  const s = addSlide();
  s.compose(grid({ name: 'root', width: fill, height: fill, columns: [fr(0.8), fr(1.2)], rows: [auto, fr(1), auto], padding: { x: 82, y: 68 }, columnGap: 58, rowGap: 34 }, [
    titleBlock('Run it in four terminals', 'Local startup', 'Start the backend, web UI, daemon, and menu bar app. The backend and web UI are already running in this workspace.', { name: 'title', titleWidth: 1500, columnSpan: 2 }),
    column({ name: 'left', width: fill, height: fill, gap: 4 }, [
      stepNode(1, 'Backend', 'FastAPI API on http://127.0.0.1:8765', C.blue),
      stepNode(2, 'Web UI', 'React operator console on http://127.0.0.1:5173', C.moss),
      stepNode(3, 'Daemon', 'Native macOS capture process', C.gold),
      stepNode(4, 'Menu bar', 'Controls search, status, pause, and reindex', C.rust),
    ]),
    column({ name: 'commands', width: fill, height: fill, gap: 16 }, [
      command('scripts/run_backend.sh'),
      command('cd web && npm run dev'),
      command('daemon/.build/memoryos-daemon'),
      command('open menubar/dist/MemoryOS.app'),
    ]),
    footer('Runbook commands'),
  ]), { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 });
}

// 5 first-time setup
{
  const s = addSlide(C.white);
  s.compose(column({ name: 'root', width: fill, height: fill, padding: { x: 84, y: 68 }, gap: 34 }, [
    titleBlock('First-time setup is mostly permissions', 'Before useful capture', 'The code runs now, but macOS must allow the daemon to read accessible window text. Then you need normal usage time to generate a corpus.'),
    grid({ name: 'setup-grid', width: fill, height: fill, columns: [fr(1), fr(1)], rows: [fr(1), fr(1)], columnGap: 26, rowGap: 26 }, [
      smallCard('1. Build binaries', 'Run scripts/build_daemon.sh and scripts/build_menubar.sh after pulling new code.', C.blue),
      smallCard('2. Grant Accessibility', 'System Settings → Privacy & Security → Accessibility → enable the terminal app running the daemon.', C.rust),
      smallCard('3. Load extension', 'Chrome → Extensions → Developer mode → Load unpacked → select extension/.', C.gold),
      smallCard('4. Collect data', 'Use the Mac normally. Check Recent and Stats in the web UI after a work session.', C.moss),
    ]),
    footer('Initial setup'),
  ]), { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 });
}

// 6 daily loop
{
  const s = addSlide();
  s.compose(column({ name: 'root', width: fill, height: fill, padding: { x: 86, y: 68 }, gap: 38 }, [
    titleBlock('The daily loop turns raw history into searchable memory', 'Operating workflow', 'The UI is built as an operator console because the model quality depends on inspection, labels, and reindexing.'),
    grid({ name: 'loop', width: fill, height: hug, columns: [fr(1), fr(1), fr(1), fr(1), fr(1)], columnGap: 18 }, [
      smallCard('Capture', 'Daemon and browser extension save raw text.', C.moss),
      smallCard('Inspect', 'Recent shows what was actually collected.', C.blue),
      smallCard('Label', 'Mark keep vs noise to build training data.', C.gold),
      smallCard('Reindex', 'Stats → Reindex rebuilds search.', C.rust),
      smallCard('Search', 'Queries return ranked local memories.', C.moss),
    ]),
    panel({ name: 'operator-note', width: fill, height: hug, padding: { x: 34, y: 26 }, fill: '#EAF3F0', stroke: '#C8E0D7', borderRadius: 12 },
      text('Practical rule: do not start model training until Recent contains enough real captures and the Label tab has both keep and noise examples.', { width: fill, height: hug, style: { fontSize: 28, bold: true, color: C.ink } })
    ),
    footer('Daily use pattern'),
  ]), { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 });
}

// 7 ML pipeline
{
  const s = addSlide(C.white);
  s.compose(grid({ name: 'root', width: fill, height: fill, columns: [fr(0.95), fr(1.05)], rows: [auto, fr(1), auto], padding: { x: 84, y: 68 }, columnGap: 54, rowGap: 34 }, [
    titleBlock('Training starts after data exists', 'ML process', 'Phase 2 scripts are complete, but production artifacts depend on a real corpus: captures, labels, training pairs, and click logs.', { columnSpan: 2, titleWidth: 1500 }),
    column({ name: 'steps', width: fill, height: fill, gap: 4 }, [
      stepNode(1, 'Label 500–1000 captures', 'Use the web Label tab or ml/train/label_captures.py.', C.rust),
      stepNode(2, 'Train noise classifier', 'ml/train/train_noise.py outputs noise_classifier.joblib.', C.gold),
      stepNode(3, 'Build index', 'TF-IDF now; FAISS after sentence-transformers are installed.', C.blue),
      stepNode(4, 'Fine-tune later', 'Generate pairs and fine-tune when the corpus is large enough.', C.moss),
    ]),
    column({ name: 'commands', width: fill, height: fill, gap: 16, justify: 'center' }, [
      command('python3 ml/train/train_noise.py'),
      command('python3 ml/train/build_index.py --backend tfidf'),
      command('python3 -m pip install -r ml/requirements.txt'),
      command('python3 ml/train/finetune_embedder.py'),
    ]),
    footer('Phase 2 model workflow'),
  ]), { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 });
}

// 8 privacy
{
  const s = addSlide();
  s.compose(column({ name: 'root', width: fill, height: fill, padding: { x: 86, y: 68 }, gap: 36 }, [
    titleBlock('Privacy is a first-class control surface', 'Safety controls', 'MemoryOS is powerful because it watches local activity. The safe way to use it is to keep capture local, visible, pausable, and deletable.'),
    grid({ name: 'privacy-grid', width: fill, height: hug, columns: [fr(1), fr(1), fr(1)], columnGap: 24 }, [
      smallCard('Blocklists', 'Apps, domains, and path fragments can be excluded through Settings.', C.rust),
      smallCard('Pause capture', 'Menu bar toggles capture.paused without killing the daemon.', C.gold),
      smallCard('Forget + export', 'Settings can export JSON or delete filtered capture ranges.', C.moss),
    ]),
    column({ name: 'privacy-paths', width: fill, height: hug, gap: 12 }, [
      command('~/Library/Application Support/MemoryOS/privacy.json'),
      command('~/Library/Application Support/MemoryOS/capture.paused'),
      command('scripts/export_memoryos.sh'),
    ]),
    footer('Privacy controls'),
  ]), { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 });
}

// 9 install and validate
{
  const s = addSlide(C.white);
  s.compose(grid({ name: 'root', width: fill, height: fill, columns: [fr(1), fr(1)], rows: [auto, fr(1), auto], padding: { x: 84, y: 58 }, columnGap: 48, rowGap: 24 }, [
    titleBlock('Install login startup', 'Operational checks', 'Keep first runs explicit. Once backend, daemon, web, and menu bar behave correctly, install LaunchAgents for login startup.', { columnSpan: 2, titleWidth: 1500, titleSize: 56 }),
    column({ name: 'install', width: fill, height: fill, gap: 6 }, [
      text('Login startup', { width: fill, height: hug, style: { fontSize: 28, bold: true, color: C.ink } }),
      command('scripts/install_daemon_launch_agent.sh'),
      command('scripts/install_menubar_launch_agent.sh'),
      command('scripts/uninstall_daemon_launch_agent.sh'),
      command('scripts/uninstall_menubar_launch_agent.sh'),
    ]),
    column({ name: 'validate', width: fill, height: fill, gap: 6 }, [
      text('Validation', { width: fill, height: hug, style: { fontSize: 28, bold: true, color: C.ink } }),
      command('curl http://127.0.0.1:8765/health'),
      command('npm run build'),
      command('scripts/benchmark_backend.py --captures 500 --runs 20'),
      command('scripts/benchmark_runtime.sh'),
    ]),
    footer('Install and validation'),
  ]), { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 });
}

// 10 next steps
{
  const s = addSlide(C.ink);
  s.compose(column({ name: 'root', width: fill, height: fill, padding: { x: 88, y: 76 }, gap: 42 }, [
    titleBlock('The remaining work is data, training, and distribution', 'Where to go next', 'The app is built. Make it valuable by running it for real, labeling captures, training the models, and packaging a signed app when the workflow proves itself.', { titleColor: C.white, subtitleColor: '#C6D2DC', kickerColor: '#93D1C1', titleWidth: 1400 }),
    grid({ name: 'next-grid', width: fill, height: hug, columns: [fr(1), fr(1), fr(1)], columnGap: 24 }, [
      panel({ width: fill, height: hug, padding: { x: 28, y: 24 }, fill: '#1F3B45', stroke: '#3A6270', borderRadius: 10 }, column({ width: fill, height: hug, gap: 8 }, [
        text('1. Collect', { width: fill, height: hug, style: { fontSize: 32, bold: true, color: '#93D1C1' } }),
        text('Run the daemon for normal work sessions until Recent shows a useful corpus.', { width: fill, height: hug, style: { fontSize: 20, color: '#D5E3E8' } }),
      ])),
      panel({ width: fill, height: hug, padding: { x: 28, y: 24 }, fill: '#3E3020', stroke: '#6A5130', borderRadius: 10 }, column({ width: fill, height: hug, gap: 8 }, [
        text('2. Train', { width: fill, height: hug, style: { fontSize: 32, bold: true, color: '#F2C67C' } }),
        text('Label keep/noise, train the classifier, and rebuild the search index.', { width: fill, height: hug, style: { fontSize: 20, color: '#F1E4CF' } }),
      ])),
      panel({ width: fill, height: hug, padding: { x: 28, y: 24 }, fill: '#3F241D', stroke: '#724033', borderRadius: 10 }, column({ width: fill, height: hug, gap: 8 }, [
        text('3. Package', { width: fill, height: hug, style: { fontSize: 32, bold: true, color: '#F0A37D' } }),
        text('Replace deprecated watcher API, sign/notarize, and tighten onboarding.', { width: fill, height: hug, style: { fontSize: 20, color: '#F1D8CD' } }),
      ])),
    ]),
    rule({ width: fixed(260), stroke: '#93D1C1', weight: 4 }),
    text('GitHub: github.com/adad44/MemoryOS', { width: fill, height: hug, style: { fontSize: 24, color: '#AFC3CE' } }),
  ]), { frame: { left: 0, top: 0, width: W, height: H }, baseUnit: 8 });
}

const blob = await PresentationFile.exportPptx(pres);
await blob.save(OUT);

for (let i = 0; i < pres.slides.items.length; i += 1) {
  const canvas = new Canvas(W, H);
  const ctx = canvas.getContext('2d');
  await drawSlideToCtx(pres.slides.items[i], pres, ctx);
  const path = `${SCRATCH}slide-${String(i + 1).padStart(2, '0')}.png`;
  await canvas.toFile(path);
}

console.log(JSON.stringify({ pptx: OUT, slides: pres.slides.items.length, previews: SCRATCH }, null, 2));
