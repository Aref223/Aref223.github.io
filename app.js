/* ============================================================
   AdCraft AI — app.js
   Canvas engine · AI integration · UI
   ============================================================ */

'use strict';

// ── State ────────────────────────────────────────────────────
const state = {
  template:   'luxury',
  format:     'square',
  variations: [],
  activeVar:  0,
  copy: {
    headline:    'Redefine Your Limits',
    subheadline: 'Premium quality that sets you apart',
    body:        'Experience the difference that true craftsmanship makes. Built for those who refuse to settle.',
    cta:         'Shop Now',
    hashtags:    '#brand #quality #lifestyle',
  },
  brand: {
    name:     '',
    tagline:  '',
    color1:   '#7c3aed',
    color2:   '#0f0f1a',
    accent:   '#f0c040',
  },
  highResCanvas: null,
};

// ── Ad Sizes ─────────────────────────────────────────────────
const AD_SIZES = {
  square:    { w: 1080, h: 1080 },
  portrait:  { w: 1080, h: 1350 },
  story:     { w: 1080, h: 1920 },
  landscape: { w: 1920, h: 1080 },
};

// ── DOM refs ─────────────────────────────────────────────────
const $ = id => document.getElementById(id);

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadState();
  setupListeners();
  resizeCanvas();
  renderAd();
  window.addEventListener('resize', debounce(resizeCanvas, 120));
});

// ── Persist & Load ───────────────────────────────────────────
function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem('adcraft_state') || '{}');
    if (saved.copy)  Object.assign(state.copy,  saved.copy);
    if (saved.brand) Object.assign(state.brand, saved.brand);
    if (saved.template) state.template = saved.template;
    if (saved.format)   state.format   = saved.format;
  } catch (_) {}

  $('brandName').value     = state.brand.name;
  $('brandTagline').value  = state.brand.tagline;
  $('color1').value        = state.brand.color1;
  $('color2').value        = state.brand.color2;
  $('colorAccent').value   = state.brand.accent;

  $('editHeadline').value  = state.copy.headline;
  $('editSub').value       = state.copy.subheadline;
  $('editBody').value      = state.copy.body;
  $('editCTA').value       = state.copy.cta;
  $('editHashtags').value  = state.copy.hashtags;

  // Activate saved template & format buttons
  document.querySelectorAll('.tmpl-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.template === state.template);
  });
  document.querySelectorAll('.pill').forEach(b => {
    b.classList.toggle('active', b.dataset.format === state.format);
  });
}

function persistState() {
  try {
    localStorage.setItem('adcraft_state', JSON.stringify({
      copy:     state.copy,
      brand:    state.brand,
      template: state.template,
      format:   state.format,
    }));
  } catch (_) {}
}

// ── Listeners ────────────────────────────────────────────────
function setupListeners() {
  // Form inputs → state
  const liveInputs = [
    ['brandName',    v => state.brand.name     = v],
    ['brandTagline', v => state.brand.tagline  = v],
    ['color1',       v => state.brand.color1   = v],
    ['color2',       v => state.brand.color2   = v],
    ['colorAccent',  v => state.brand.accent   = v],
    ['editHeadline', v => state.copy.headline    = v],
    ['editSub',      v => state.copy.subheadline = v],
    ['editBody',     v => state.copy.body        = v],
    ['editCTA',      v => state.copy.cta         = v],
    ['editHashtags', v => state.copy.hashtags    = v],
  ];
  liveInputs.forEach(([id, fn]) => {
    $(id).addEventListener('input', e => { fn(e.target.value); renderAd(); persistState(); });
  });

  // Template buttons
  document.querySelectorAll('.tmpl-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tmpl-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.template = btn.dataset.template;
      renderAd();
      persistState();
    });
  });

  // Format pills
  document.querySelectorAll('.pill').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.format = btn.dataset.format;
      resizeCanvas();
      renderAd();
      persistState();
    });
  });

  // Generate
  $('btnGenerate').addEventListener('click', handleGenerate);
  $('btnManual').addEventListener('click', () => {
    $('editHeadline').focus();
    showToast('Fill in the copy fields on the right ✏️');
  });

  // API key modal
  $('linkApiKey').addEventListener('click', e => { e.preventDefault(); openModal('modalApiKey'); });
  $('navSettings').addEventListener('click', () => openModal('modalApiKey'));
  $('modalClose').addEventListener('click', () => closeModal('modalApiKey'));
  $('btnSaveKey').addEventListener('click', () => {
    const key = $('apiKeyInput').value.trim();
    if (key) {
      localStorage.setItem('adcraft_apikey', key);
      closeModal('modalApiKey');
      showToast('API key saved ✓');
    } else {
      showToast('Please enter a valid key');
    }
  });
  // Pre-fill key input
  const stored = localStorage.getItem('adcraft_apikey') || '';
  if (stored) $('apiKeyInput').value = stored;

  // Saved ads
  $('navSaved').addEventListener('click', openSaved);
  $('modalSavedClose').addEventListener('click', () => closeModal('modalSaved'));

  // Overlay click to close
  ['modalApiKey', 'modalSaved'].forEach(id => {
    $(id).addEventListener('click', e => {
      if (e.target === $(id)) closeModal(id);
    });
  });

  // Actions
  $('btnDownload').addEventListener('click', downloadAd);
  $('btnCopyText').addEventListener('click', copyText);
  $('btnSave').addEventListener('click', saveAd);

  // Nav
  $('navCreate').addEventListener('click', () => {
    $('navCreate').classList.add('active');
    $('navSaved').classList.remove('active');
    $('navSettings').classList.remove('active');
  });
}

// ── Canvas Sizing ─────────────────────────────────────────── */
function resizeCanvas() {
  const wrap    = $('canvasWrap');
  const canvas  = $('adCanvas');
  const size    = AD_SIZES[state.format];
  const ratio   = size.w / size.h;

  const maxW = wrap.clientWidth  - 32;
  const maxH = wrap.clientHeight - 32;
  const fitW = Math.min(maxW, maxH * ratio);
  const fitH = fitW / ratio;

  canvas.style.width  = fitW + 'px';
  canvas.style.height = fitH + 'px';

  // High-res canvas
  const hr = document.createElement('canvas');
  hr.width  = size.w;
  hr.height = size.h;
  state.highResCanvas = hr;

  // Display canvas at lower resolution for speed
  canvas.width  = Math.round(fitW  * (window.devicePixelRatio || 1));
  canvas.height = Math.round(fitH  * (window.devicePixelRatio || 1));
}

// ── Render Ad ────────────────────────────────────────────────
function renderAd() {
  const canvas = $('adCanvas');
  const hr     = state.highResCanvas;
  if (!hr) return;

  const data = buildData();

  // Draw on high-res canvas
  drawTemplate(hr.getContext('2d'), hr.width, hr.height, data);

  // Scale to display canvas
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(hr, 0, 0, canvas.width, canvas.height);
}

function buildData() {
  return {
    headline:    state.copy.headline    || 'Your Headline Here',
    subheadline: state.copy.subheadline || 'Your subheadline',
    body:        state.copy.body        || '',
    cta:         state.copy.cta         || 'Learn More',
    hashtags:    state.copy.hashtags    || '',
    brand:       state.brand.name       || 'BRAND',
    tagline:     state.brand.tagline    || '',
    color1:      state.brand.color1,
    color2:      state.brand.color2,
    accent:      state.brand.accent,
  };
}

// ── Template Router ───────────────────────────────────────── */
function drawTemplate(ctx, W, H, d) {
  const map = {
    luxury:    drawLuxury,
    bold:      drawBold,
    minimal:   drawMinimal,
    tech:      drawTech,
    lifestyle: drawLifestyle,
    corporate: drawCorporate,
  };
  (map[state.template] || drawLuxury)(ctx, W, H, d);
}

// ─────────────────────────────────────────────────────────────
// TEMPLATE 1: LUXURY DARK
// ─────────────────────────────────────────────────────────────
function drawLuxury(ctx, W, H, d) {
  ctx.clearRect(0, 0, W, H);

  // Background gradient
  const bg = ctx.createLinearGradient(0, 0, W * .6, H);
  bg.addColorStop(0, shadeColor(d.color2, -20));
  bg.addColorStop(1, '#060610');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  // Subtle grain
  addGrain(ctx, W, H, 0.025);

  // Diagonal light ray
  const ray = ctx.createLinearGradient(W * .7, 0, W, H * .5);
  ray.addColorStop(0, hexToRGBA(d.color1, .12));
  ray.addColorStop(1, 'transparent');
  ctx.fillStyle = ray;
  ctx.fillRect(0, 0, W, H);

  // Top decorative line (gold)
  const lineY = H * .1;
  drawLine(ctx, W * .1, lineY, W * .9, lineY, d.accent, W * .001, .5);

  // Ornamental dots on the line
  [W * .1, W * .9].forEach(x => {
    ctx.beginPath();
    ctx.arc(x, lineY, W * .005, 0, Math.PI * 2);
    ctx.fillStyle = d.accent;
    ctx.fill();
  });

  // Brand name (top-center)
  setFont(ctx, 300, W * .022, 'Inter, sans-serif');
  ctx.fillStyle = hexToRGBA(d.accent, .8);
  ctx.textAlign = 'center';
  ctx.letterSpacing = '0.25em';
  ctx.fillText(d.brand.toUpperCase(), W / 2, lineY * 2.2);
  ctx.letterSpacing = '0';

  // Large headline
  const hlSize = W * .085;
  setFont(ctx, 400, hlSize, 'Playfair Display, Georgia, serif');
  ctx.fillStyle = '#f5f5f5';
  ctx.textAlign = 'center';
  wrapTextCenter(ctx, d.headline, W / 2, H * .44, W * .78, hlSize * 1.25);

  // Divider
  const divY = H * .57;
  const divW = W * .1;
  drawLine(ctx, W / 2 - divW, divY, W / 2 - W * .02, divY, d.accent, W * .001);
  drawLine(ctx, W / 2 + W * .02, divY, W / 2 + divW, divY, d.accent, W * .001);
  ctx.beginPath();
  ctx.arc(W / 2, divY, W * .008, 0, Math.PI * 2);
  ctx.strokeStyle = d.accent;
  ctx.lineWidth = W * .001;
  ctx.stroke();

  // Subheadline
  setFont(ctx, 300, W * .032, 'Inter, sans-serif');
  ctx.fillStyle = hexToRGBA('#ffffff', .6);
  ctx.textAlign = 'center';
  ctx.letterSpacing = '0.08em';
  ctx.fillText(d.subheadline, W / 2, divY + H * .07);
  ctx.letterSpacing = '0';

  // CTA Button
  drawCTAButton(ctx, W / 2, H * .74, d.cta, d.accent, '#000', W);

  // Bottom line
  const btmY = H * .88;
  drawLine(ctx, W * .1, btmY, W * .9, btmY, d.accent, W * .001, .3);

  // Tagline / hashtags
  if (d.tagline || d.hashtags) {
    setFont(ctx, 300, W * .018, 'Inter, sans-serif');
    ctx.fillStyle = hexToRGBA('#ffffff', .3);
    ctx.textAlign = 'center';
    ctx.letterSpacing = '0.15em';
    ctx.fillText((d.tagline || d.hashtags.split(' ')[0] || '').toUpperCase(), W / 2, btmY + H * .04);
    ctx.letterSpacing = '0';
  }
}

// ─────────────────────────────────────────────────────────────
// TEMPLATE 2: BOLD / MODERN
// ─────────────────────────────────────────────────────────────
function drawBold(ctx, W, H, d) {
  ctx.clearRect(0, 0, W, H);

  // Vibrant gradient background
  const bg = ctx.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, d.color1);
  bg.addColorStop(1, shadeColor(d.color1, -40));
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  // Geometric circle (background decoration)
  ctx.beginPath();
  ctx.arc(W * .85, H * .15, W * .45, 0, Math.PI * 2);
  ctx.fillStyle = hexToRGBA('#ffffff', .05);
  ctx.fill();

  ctx.beginPath();
  ctx.arc(W * .15, H * .85, W * .35, 0, Math.PI * 2);
  ctx.fillStyle = hexToRGBA('#000000', .12);
  ctx.fill();

  addGrain(ctx, W, H, 0.02);

  // Accent bar (left edge)
  ctx.fillStyle = d.accent;
  ctx.fillRect(0, H * .2, W * .012, H * .6);

  // Brand name
  setFont(ctx, 700, W * .028, 'Space Grotesk, Inter, sans-serif');
  ctx.fillStyle = hexToRGBA('#ffffff', .5);
  ctx.textAlign = 'left';
  ctx.letterSpacing = '0.2em';
  ctx.fillText(d.brand.toUpperCase(), W * .08, H * .15);
  ctx.letterSpacing = '0';

  // Large headline
  const hlSize = W * .095;
  setFont(ctx, 700, hlSize, 'Space Grotesk, Inter, sans-serif');
  ctx.fillStyle = '#ffffff';
  ctx.textAlign = 'left';
  wrapTextLeft(ctx, d.headline.toUpperCase(), W * .08, H * .38, W * .84, hlSize * 1.15);

  // Subheadline
  setFont(ctx, 400, W * .034, 'Inter, sans-serif');
  ctx.fillStyle = hexToRGBA('#ffffff', .75);
  ctx.textAlign = 'left';
  wrapTextLeft(ctx, d.subheadline, W * .08, H * .58, W * .7, W * .045);

  // Body (small)
  if (d.body) {
    setFont(ctx, 300, W * .024, 'Inter, sans-serif');
    ctx.fillStyle = hexToRGBA('#ffffff', .5);
    wrapTextLeft(ctx, d.body, W * .08, H * .67, W * .65, W * .033);
  }

  // CTA – filled accent pill
  drawCTAPill(ctx, W * .08, H * .8, d.cta, d.accent, '#000', W, 'left');

  // Bottom hashtags
  if (d.hashtags) {
    setFont(ctx, 400, W * .02, 'Inter, sans-serif');
    ctx.fillStyle = hexToRGBA('#ffffff', .3);
    ctx.textAlign = 'left';
    ctx.fillText(d.hashtags, W * .08, H * .93);
  }
}

// ─────────────────────────────────────────────────────────────
// TEMPLATE 3: CLEAN MINIMAL
// ─────────────────────────────────────────────────────────────
function drawMinimal(ctx, W, H, d) {
  ctx.clearRect(0, 0, W, H);

  // White background
  ctx.fillStyle = '#fafafa';
  ctx.fillRect(0, 0, W, H);

  // Color block (top strip)
  ctx.fillStyle = d.color1;
  ctx.fillRect(0, 0, W, H * .08);

  // Brand name in strip
  setFont(ctx, 600, W * .025, 'DM Sans, Inter, sans-serif');
  ctx.fillStyle = '#ffffff';
  ctx.textAlign = 'center';
  ctx.letterSpacing = '0.18em';
  ctx.fillText(d.brand.toUpperCase(), W / 2, H * .055);
  ctx.letterSpacing = '0';

  // Large headline
  const hlSize = W * .088;
  setFont(ctx, 700, hlSize, 'DM Sans, Inter, sans-serif');
  ctx.fillStyle = '#111111';
  ctx.textAlign = 'center';
  wrapTextCenter(ctx, d.headline, W / 2, H * .37, W * .82, hlSize * 1.2);

  // Accent underline
  ctx.fillStyle = d.accent;
  ctx.fillRect(W * .4, H * .52, W * .2, H * .006);

  // Subheadline
  setFont(ctx, 400, W * .034, 'DM Sans, Inter, sans-serif');
  ctx.fillStyle = '#555555';
  ctx.textAlign = 'center';
  wrapTextCenter(ctx, d.subheadline, W / 2, H * .61, W * .72, W * .045);

  // Body
  if (d.body) {
    setFont(ctx, 300, W * .024, 'DM Sans, Inter, sans-serif');
    ctx.fillStyle = '#777777';
    ctx.textAlign = 'center';
    wrapTextCenter(ctx, d.body, W / 2, H * .72, W * .7, W * .032);
  }

  // CTA
  drawCTAButton(ctx, W / 2, H * .84, d.cta, d.color1, '#ffffff', W);

  // Bottom hashtags
  if (d.hashtags) {
    setFont(ctx, 400, W * .02, 'DM Sans, Inter, sans-serif');
    ctx.fillStyle = '#aaaaaa';
    ctx.textAlign = 'center';
    ctx.fillText(d.hashtags, W / 2, H * .95);
  }
}

// ─────────────────────────────────────────────────────────────
// TEMPLATE 4: TECH / DARK
// ─────────────────────────────────────────────────────────────
function drawTech(ctx, W, H, d) {
  ctx.clearRect(0, 0, W, H);

  // Near-black bg
  ctx.fillStyle = '#08080f';
  ctx.fillRect(0, 0, W, H);

  // Grid lines
  ctx.strokeStyle = hexToRGBA('#ffffff', .03);
  ctx.lineWidth = 1;
  const gridStep = W / 12;
  for (let x = 0; x <= W; x += gridStep) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
  }
  for (let y = 0; y <= H; y += gridStep) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }

  // Glow circle
  const glow = ctx.createRadialGradient(W * .5, H * .35, 0, W * .5, H * .35, W * .55);
  glow.addColorStop(0, hexToRGBA(d.color1, .2));
  glow.addColorStop(1, 'transparent');
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, W, H);

  // Hexagon decoration
  drawHex(ctx, W * .85, H * .12, W * .07, d.color1, .15);
  drawHex(ctx, W * .1,  H * .88, W * .05, d.color1, .1);

  // Horizontal rule (accent)
  ctx.strokeStyle = d.color1;
  ctx.lineWidth = W * .002;
  ctx.setLineDash([W * .02, W * .01]);
  ctx.beginPath();
  ctx.moveTo(W * .08, H * .18);
  ctx.lineTo(W * .92, H * .18);
  ctx.stroke();
  ctx.setLineDash([]);

  // Brand
  setFont(ctx, 600, W * .022, 'Syne, Inter, sans-serif');
  ctx.fillStyle = d.color1;
  ctx.textAlign = 'left';
  ctx.letterSpacing = '0.25em';
  ctx.fillText(d.brand.toUpperCase(), W * .08, H * .14);
  ctx.letterSpacing = '0';

  // Version / platform label
  setFont(ctx, 400, W * .018, 'Inter, sans-serif');
  ctx.fillStyle = hexToRGBA('#ffffff', .25);
  ctx.textAlign = 'right';
  ctx.fillText('v2.0', W * .92, H * .14);

  // Headline
  const hlSize = W * .09;
  setFont(ctx, 700, hlSize, 'Syne, Inter, sans-serif');
  ctx.fillStyle = '#ffffff';
  ctx.textAlign = 'left';
  wrapTextLeft(ctx, d.headline, W * .08, H * .4, W * .84, hlSize * 1.15);

  // Subheadline
  setFont(ctx, 400, W * .03, 'Inter, sans-serif');
  ctx.fillStyle = hexToRGBA('#ffffff', .55);
  ctx.textAlign = 'left';
  wrapTextLeft(ctx, d.subheadline, W * .08, H * .58, W * .75, W * .04);

  // Feature pills
  const features = d.body ? d.body.split('.').filter(s => s.trim()).slice(0, 2) : [];
  features.forEach((feat, i) => {
    const px = W * .08 + i * W * .4;
    const py = H * .69;
    ctx.fillStyle = hexToRGBA(d.color1, .15);
    roundRect(ctx, px, py - W * .025, W * .35, W * .035, W * .005);
    ctx.fill();
    ctx.strokeStyle = hexToRGBA(d.color1, .3);
    ctx.lineWidth = 1;
    roundRect(ctx, px, py - W * .025, W * .35, W * .035, W * .005);
    ctx.stroke();
    setFont(ctx, 400, W * .018, 'Inter, sans-serif');
    ctx.fillStyle = hexToRGBA('#ffffff', .7);
    ctx.textAlign = 'left';
    ctx.fillText('▶  ' + feat.trim(), px + W * .015, py);
  });

  // CTA
  drawCTAButton(ctx, W * .08 + W * .18, H * .82, d.cta, d.color1, '#ffffff', W, 'left');

  // Bottom line
  ctx.strokeStyle = hexToRGBA('#ffffff', .06);
  ctx.lineWidth = 1;
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.moveTo(W * .08, H * .92);
  ctx.lineTo(W * .92, H * .92);
  ctx.stroke();

  if (d.hashtags) {
    setFont(ctx, 400, W * .018, 'Inter, sans-serif');
    ctx.fillStyle = hexToRGBA('#ffffff', .2);
    ctx.textAlign = 'left';
    ctx.fillText(d.hashtags, W * .08, H * .96);
  }
}

// ─────────────────────────────────────────────────────────────
// TEMPLATE 5: LIFESTYLE / WARM
// ─────────────────────────────────────────────────────────────
function drawLifestyle(ctx, W, H, d) {
  ctx.clearRect(0, 0, W, H);

  // Warm gradient bg (simulate golden hour)
  const bg = ctx.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0,   '#f7c59f');
  bg.addColorStop(0.5, blendColors(d.color1, '#f7a05a', 0.4));
  bg.addColorStop(1,   shadeColor(d.color1, -30));
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, W, H);

  addGrain(ctx, W, H, 0.03);

  // Soft bokeh circles
  [[W*.8,H*.1,W*.3,.08],[W*.1,H*.7,W*.25,.05],[W*.9,H*.75,W*.15,.04]].forEach(([cx,cy,r,a]) => {
    const g = ctx.createRadialGradient(cx,cy,0,cx,cy,r);
    g.addColorStop(0, hexToRGBA('#ffffff', a));
    g.addColorStop(1, 'transparent');
    ctx.fillStyle = g;
    ctx.fillRect(0,0,W,H);
  });

  // Semi-transparent overlay card
  ctx.fillStyle = hexToRGBA('#ffffff', .88);
  roundRect(ctx, W*.08, H*.28, W*.84, H*.55, W*.02);
  ctx.fill();

  // Brand (above card)
  setFont(ctx, 700, W * .026, 'DM Sans, Inter, sans-serif');
  ctx.fillStyle = hexToRGBA('#ffffff', .9);
  ctx.textAlign = 'center';
  ctx.letterSpacing = '0.15em';
  ctx.fillText(d.brand.toUpperCase(), W / 2, H * .22);
  ctx.letterSpacing = '0';

  // Accent dot brand decoration
  ctx.beginPath();
  ctx.arc(W/2 - ctx.measureText(d.brand.toUpperCase() + '  ').width/2 - W*.01, H*.215, W*.006, 0, Math.PI*2);
  ctx.fillStyle = d.accent;
  ctx.fill();

  // Headline
  const hlSize = W * .072;
  setFont(ctx, 700, hlSize, 'Playfair Display, Georgia, serif');
  ctx.fillStyle = '#1a1a1a';
  ctx.textAlign = 'center';
  ctx.fillStyle = shadeColor(d.color1, -50);
  wrapTextCenter(ctx, d.headline, W / 2, H * .44, W * .76, hlSize * 1.2);

  // Subheadline
  setFont(ctx, 400, W * .028, 'DM Sans, Inter, sans-serif');
  ctx.fillStyle = '#444444';
  ctx.textAlign = 'center';
  wrapTextCenter(ctx, d.subheadline, W / 2, H * .58, W * .72, W * .038);

  // Thin accent line
  ctx.fillStyle = d.accent;
  const lw = W*.06;
  ctx.fillRect(W/2-lw/2, H*.64, lw, H*.004);

  // CTA
  drawCTAButton(ctx, W / 2, H * .73, d.cta, d.color1, '#ffffff', W);

  // Hashtags below card
  if (d.hashtags) {
    setFont(ctx, 400, W * .02, 'DM Sans, Inter, sans-serif');
    ctx.fillStyle = hexToRGBA('#ffffff', .5);
    ctx.textAlign = 'center';
    ctx.fillText(d.hashtags, W / 2, H * .9);
  }
}

// ─────────────────────────────────────────────────────────────
// TEMPLATE 6: CORPORATE / B2B
// ─────────────────────────────────────────────────────────────
function drawCorporate(ctx, W, H, d) {
  ctx.clearRect(0, 0, W, H);

  // Clean white bg
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, W, H);

  // Left color column
  const colW = W * .38;
  const bg = ctx.createLinearGradient(0, 0, colW, H);
  bg.addColorStop(0, d.color1);
  bg.addColorStop(1, shadeColor(d.color1, 20));
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, colW, H);

  // Diagonal cut
  ctx.fillStyle = '#ffffff';
  ctx.beginPath();
  ctx.moveTo(colW - W*.06, 0);
  ctx.lineTo(colW + W*.06, 0);
  ctx.lineTo(colW + W*.06, H);
  ctx.lineTo(colW - W*.06, H);
  ctx.closePath();
  ctx.fill();

  // Reapply the diagonal slice on left (white triangle cutout)
  ctx.fillStyle = '#ffffff';
  ctx.beginPath();
  ctx.moveTo(colW * .7, 0);
  ctx.lineTo(colW, 0);
  ctx.lineTo(colW *.7, H);
  ctx.closePath();
  ctx.fill();

  addGrain(ctx, W, H, 0.015);

  // Brand name (left column)
  setFont(ctx, 700, W * .028, 'Inter, sans-serif');
  ctx.fillStyle = hexToRGBA('#ffffff', .85);
  ctx.textAlign = 'center';
  ctx.letterSpacing = '0.12em';
  ctx.fillText(d.brand.toUpperCase(), colW * .42, H * .12);
  ctx.letterSpacing = '0';

  // Left stat / accent number
  setFont(ctx, 800, W * .16, 'Inter, sans-serif');
  ctx.fillStyle = hexToRGBA('#ffffff', .12);
  ctx.textAlign = 'center';
  ctx.fillText('✦', colW * .42, H * .65);

  // Left tagline
  setFont(ctx, 300, W * .022, 'Inter, sans-serif');
  ctx.fillStyle = hexToRGBA('#ffffff', .65);
  ctx.textAlign = 'center';
  ctx.letterSpacing = '0.08em';
  const tl = d.tagline || d.subheadline;
  wrapTextCenter(ctx, tl, colW * .42, H * .75, colW * .7, W * .03);
  ctx.letterSpacing = '0';

  // Right side content
  const rx = colW + W * .1;
  const rw = W - rx - W * .06;

  // Small label
  setFont(ctx, 600, W * .018, 'Inter, sans-serif');
  ctx.fillStyle = d.color1;
  ctx.textAlign = 'left';
  ctx.letterSpacing = '0.15em';
  ctx.fillText('NEW RELEASE', rx, H * .14);
  ctx.letterSpacing = '0';

  // Headline
  const hlSize = W * .072;
  setFont(ctx, 700, hlSize, 'Inter, sans-serif');
  ctx.fillStyle = '#111111';
  ctx.textAlign = 'left';
  wrapTextLeft(ctx, d.headline, rx, H * .32, rw, hlSize * 1.2);

  // Accent rule
  ctx.fillStyle = d.accent;
  ctx.fillRect(rx, H * .47, rw * .3, H * .004);

  // Body
  setFont(ctx, 400, W * .026, 'Inter, sans-serif');
  ctx.fillStyle = '#555555';
  ctx.textAlign = 'left';
  wrapTextLeft(ctx, d.body || d.subheadline, rx, H * .58, rw, W * .036);

  // CTA
  const ctaX = rx + W * .13;
  drawCTAButton(ctx, ctaX, H * .75, d.cta, d.color1, '#ffffff', W, 'center');

  // Bottom line + hashtags
  ctx.strokeStyle = '#eeeeee';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(rx, H * .88);
  ctx.lineTo(W - W * .06, H * .88);
  ctx.stroke();

  if (d.hashtags) {
    setFont(ctx, 400, W * .018, 'Inter, sans-serif');
    ctx.fillStyle = '#aaaaaa';
    ctx.textAlign = 'left';
    ctx.fillText(d.hashtags, rx, H * .93);
  }
}

// ── Drawing Helpers ───────────────────────────────────────────

function setFont(ctx, weight, size, family) {
  ctx.font = `${weight} ${size}px ${family}`;
}

function wrapTextCenter(ctx, text, cx, cy, maxW, lineH) {
  if (!text) return 0;
  const lines = breakLines(ctx, text, maxW);
  const total = lines.length * lineH;
  const startY = cy - total / 2 + lineH * 0.5;
  lines.forEach((l, i) => ctx.fillText(l, cx, startY + i * lineH));
  return total;
}

function wrapTextLeft(ctx, text, x, y, maxW, lineH) {
  if (!text) return 0;
  const lines = breakLines(ctx, text, maxW);
  lines.forEach((l, i) => ctx.fillText(l, x, y + i * lineH));
  return lines.length * lineH;
}

function breakLines(ctx, text, maxW) {
  const words  = text.split(' ');
  const lines  = [];
  let   line   = '';
  for (const word of words) {
    const test = line ? line + ' ' + word : word;
    if (ctx.measureText(test).width > maxW && line) {
      lines.push(line);
      line = word;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}

function drawLine(ctx, x1, y1, x2, y2, color, width, alpha = 1) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = color;
  ctx.lineWidth   = width;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
  ctx.restore();
}

function drawCTAButton(ctx, cx, cy, text, bg, fg, W, align = 'center') {
  const pad  = W * .04;
  const h    = W * .055;
  const r    = h / 2;
  setFont(ctx, 600, W * .028, 'Inter, sans-serif');
  const tw   = ctx.measureText(text).width;
  const bw   = tw + pad * 2;
  const bx   = align === 'left' ? cx - bw / 2 : cx - bw / 2;
  const by   = cy - h / 2;

  ctx.fillStyle = bg;
  roundRect(ctx, bx, by, bw, h, r);
  ctx.fill();

  ctx.fillStyle = fg;
  ctx.textAlign = 'center';
  ctx.fillText(text, bx + bw / 2, cy + W * .008);
}

function drawCTAPill(ctx, lx, cy, text, bg, fg, W) {
  const pad  = W * .04;
  const h    = W * .055;
  const r    = h / 2;
  setFont(ctx, 600, W * .028, 'Inter, sans-serif');
  const tw = ctx.measureText(text).width;
  const bw = tw + pad * 2;

  ctx.fillStyle = bg;
  roundRect(ctx, lx, cy - h/2, bw, h, r);
  ctx.fill();

  ctx.fillStyle = fg;
  ctx.textAlign = 'center';
  ctx.fillText(text, lx + bw/2, cy + W * .008);
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function drawHex(ctx, cx, cy, r, color, alpha) {
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 6;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.stroke();
  ctx.restore();
}

function addGrain(ctx, W, H, intensity) {
  const imageData = ctx.getImageData(0, 0, W, H);
  const data = imageData.data;
  for (let i = 0; i < data.length; i += 4) {
    const n = (Math.random() * 2 - 1) * 255 * intensity;
    data[i]     = clamp(data[i]     + n);
    data[i + 1] = clamp(data[i + 1] + n);
    data[i + 2] = clamp(data[i + 2] + n);
  }
  ctx.putImageData(imageData, 0, 0);
}

function clamp(v) { return Math.max(0, Math.min(255, v)); }

// ── Color Utilities ───────────────────────────────────────────

function hexToRGBA(hex, alpha) {
  const r = parseInt(hex.slice(1,3), 16);
  const g = parseInt(hex.slice(3,5), 16);
  const b = parseInt(hex.slice(5,7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function shadeColor(hex, percent) {
  try {
    let r = parseInt(hex.slice(1,3),16);
    let g = parseInt(hex.slice(3,5),16);
    let b = parseInt(hex.slice(5,7),16);
    r = clamp(r + Math.round(percent * 2.55));
    g = clamp(g + Math.round(percent * 2.55));
    b = clamp(b + Math.round(percent * 2.55));
    return '#' + [r,g,b].map(x => x.toString(16).padStart(2,'0')).join('');
  } catch(_) { return hex; }
}

function blendColors(hex1, hex2, t) {
  try {
    const r1=parseInt(hex1.slice(1,3),16), g1=parseInt(hex1.slice(3,5),16), b1=parseInt(hex1.slice(5,7),16);
    const r2=parseInt(hex2.slice(1,3),16), g2=parseInt(hex2.slice(3,5),16), b2=parseInt(hex2.slice(5,7),16);
    const r=Math.round(r1+(r2-r1)*t), g=Math.round(g1+(g2-g1)*t), b=Math.round(b1+(b2-b1)*t);
    return '#'+[r,g,b].map(x=>x.toString(16).padStart(2,'0')).join('');
  } catch(_) { return hex1; }
}

// ── AI Generation ─────────────────────────────────────────────

async function handleGenerate() {
  const apiKey = localStorage.getItem('adcraft_apikey');
  if (!apiKey) {
    openModal('modalApiKey');
    showToast('Add your OpenAI API key first');
    return;
  }

  const brand    = $('brandName').value.trim()    || 'Brand';
  const product  = $('productName').value.trim()  || 'Product';
  const benefit  = $('keyBenefit').value.trim()   || 'Superior quality';
  const audience = $('targetAudience').value.trim() || 'General audience';
  const desc     = $('productDesc').value.trim();
  const tone     = $('tone').value;
  const platform = $('platform').value;

  showLoading(true);
  $('btnGenerate').disabled = true;

  try {
    const variations = await callOpenAI(apiKey, { brand, product, benefit, audience, desc, tone, platform });
    state.variations = variations;
    state.activeVar  = 0;
    applyCopy(variations[0]);
    renderVariationDots();
    renderAd();
    showToast('✦ 3 variations generated!');
  } catch (err) {
    console.error(err);
    showToast('Error: ' + (err.message || 'API call failed'));
  } finally {
    showLoading(false);
    $('btnGenerate').disabled = false;
  }
}

async function callOpenAI(apiKey, { brand, product, benefit, audience, desc, tone, platform }) {
  const systemPrompt =
    `You are Alex Chen, the world's highest-paid advertising copywriter. ` +
    `You have created iconic campaigns for Apple, Nike, Tesla, Louis Vuitton, and Chanel. ` +
    `Your copy is emotionally resonant, human, and never sounds AI-generated. ` +
    `Every word earns its place. You think in feelings, not features.`;

  const userPrompt =
    `Create 3 DISTINCT professional ad variations for:\n` +
    `- Brand: ${brand}\n` +
    `- Product/Service: ${product}\n` +
    `- Key Benefit: ${benefit}\n` +
    `- Target Audience: ${audience}\n` +
    `- Tone: ${tone}\n` +
    `- Platform: ${platform}\n` +
    (desc ? `- Additional context: ${desc}\n` : '') +
    `\nRequirements:\n` +
    `- Each variation uses a COMPLETELY different creative angle\n` +
    `- Headlines are punchy, memorable, under 10 words\n` +
    `- Copy sounds authentically human — NO corporate jargon, NO buzzwords\n` +
    `- Use emotional hooks and sensory language\n` +
    `- Subheadline supports the headline (max 15 words)\n` +
    `- Body is 1-2 sentences, compelling and concise\n` +
    `- CTA is action-oriented, 2-5 words\n` +
    `- 3-5 hashtags relevant to the platform and audience\n` +
    `\nReturn ONLY valid JSON, no markdown fences, no explanation:\n` +
    `{"variations":[{"headline":"...","subheadline":"...","body":"...","cta":"...","hashtags":"#tag1 #tag2 #tag3"},{"headline":"...","subheadline":"...","body":"...","cta":"...","hashtags":"..."},{"headline":"...","subheadline":"...","body":"...","cta":"...","hashtags":"..."}]}`;

  const res = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + apiKey,
    },
    body: JSON.stringify({
      model: 'gpt-4o',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user',   content: userPrompt   },
      ],
      temperature: 0.9,
      max_tokens:  900,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || `HTTP ${res.status}`);
  }

  const data = await res.json();
  const raw  = data.choices?.[0]?.message?.content?.trim() || '{}';

  // Strip potential markdown fences
  const clean = raw.replace(/^```(?:json)?\n?/, '').replace(/\n?```$/, '');
  const parsed = JSON.parse(clean);
  return parsed.variations || [];
}

function applyCopy(v) {
  if (!v) return;
  state.copy.headline    = v.headline    || state.copy.headline;
  state.copy.subheadline = v.subheadline || state.copy.subheadline;
  state.copy.body        = v.body        || state.copy.body;
  state.copy.cta         = v.cta         || state.copy.cta;
  state.copy.hashtags    = v.hashtags    || state.copy.hashtags;

  $('editHeadline').value = state.copy.headline;
  $('editSub').value      = state.copy.subheadline;
  $('editBody').value     = state.copy.body;
  $('editCTA').value      = state.copy.cta;
  $('editHashtags').value = state.copy.hashtags;
}

function renderVariationDots() {
  const bar  = $('variationBar');
  const dots = $('variationDots');
  if (!state.variations.length) { bar.classList.add('hidden'); return; }

  bar.classList.remove('hidden');
  dots.innerHTML = '';
  state.variations.forEach((_, i) => {
    const btn = document.createElement('button');
    btn.className = 'var-dot' + (i === state.activeVar ? ' active' : '');
    btn.textContent = i + 1;
    btn.addEventListener('click', () => {
      state.activeVar = i;
      applyCopy(state.variations[i]);
      renderVariationDots();
      renderAd();
    });
    dots.appendChild(btn);
  });
}

// ── Export ────────────────────────────────────────────────────

function downloadAd() {
  const hr = state.highResCanvas;
  if (!hr) return;

  const data  = buildData();
  drawTemplate(hr.getContext('2d'), hr.width, hr.height, data);

  const link       = document.createElement('a');
  link.download    = `${(state.brand.name || 'ad').replace(/\s+/g,'_')}_${state.template}_${state.format}.png`;
  link.href        = hr.toDataURL('image/png');
  link.click();
  showToast('⬇ Downloading high-res PNG…');
}

function copyText() {
  const text =
    `Headline: ${state.copy.headline}\n` +
    `Subheadline: ${state.copy.subheadline}\n` +
    `Body: ${state.copy.body}\n` +
    `CTA: ${state.copy.cta}\n` +
    `${state.copy.hashtags}`;

  navigator.clipboard?.writeText(text)
    .then(() => showToast('📋 Copy text copied!'))
    .catch(() => showToast('Could not copy to clipboard'));
}

function saveAd() {
  try {
    const hr   = state.highResCanvas;
    if (!hr) return;
    const data = buildData();
    drawTemplate(hr.getContext('2d'), hr.width, hr.height, data);

    const saves = JSON.parse(localStorage.getItem('adcraft_saves') || '[]');
    saves.unshift({
      id:        Date.now(),
      thumbnail: hr.toDataURL('image/jpeg', 0.5),
      label:     (state.brand.name || 'Ad') + ' · ' + state.template,
      copy:      { ...state.copy },
      brand:     { ...state.brand },
      template:  state.template,
      format:    state.format,
    });
    if (saves.length > 20) saves.pop();
    localStorage.setItem('adcraft_saves', JSON.stringify(saves));
    showToast('🔖 Ad saved!');
  } catch (e) {
    showToast('Could not save: storage full?');
  }
}

function openSaved() {
  const saves = JSON.parse(localStorage.getItem('adcraft_saves') || '[]');
  const grid  = $('savedGrid');

  grid.innerHTML = saves.length
    ? saves.map(s => `
        <div class="saved-card" data-id="${s.id}">
          <img src="${s.thumbnail}" alt="${s.label}" loading="lazy" />
          <div class="saved-card-label">${s.label}</div>
        </div>`).join('')
    : '<p class="empty-msg">No saved ads yet. Create one and click Save Ad.</p>';

  grid.querySelectorAll('.saved-card').forEach(card => {
    card.addEventListener('click', () => {
      const s = saves.find(x => x.id === +card.dataset.id);
      if (!s) return;
      Object.assign(state.copy,  s.copy);
      Object.assign(state.brand, s.brand);
      state.template = s.template;
      state.format   = s.format;
      loadState();
      resizeCanvas();
      renderAd();
      closeModal('modalSaved');
      showToast('Ad loaded ✓');
    });
  });

  openModal('modalSaved');
  $('navSaved').classList.add('active');
  $('navCreate').classList.remove('active');
}

// ── UI Helpers ────────────────────────────────────────────────

function showLoading(on) {
  $('canvasLoading').classList.toggle('hidden', !on);
}

function openModal(id) {
  $(id).classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeModal(id) {
  $(id).classList.add('hidden');
  document.body.style.overflow = '';
}

let toastTimer;
function showToast(msg) {
  const t = $('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  requestAnimationFrame(() => t.classList.add('show'));
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    t.classList.remove('show');
    setTimeout(() => t.classList.add('hidden'), 300);
  }, 2800);
}

function debounce(fn, ms) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}
