/* =========================================================================
   CIDF — shared data + chart engine (vanilla JS, no dependencies)
   Data: results/audit_results.json (2026-06-24 audit).
   Verified source URLs: docs/source_url_verification.csv.
   ========================================================================= */
(function () {
  'use strict';

  /* ------------------------------------------------------------------ DATA */
  const CASE_META = {
    notpetya: { name: 'NotPetya',        codename: 'NOTPETYA',      date: 'JUN 2017', hex: '#E8521A', cssvar: 'var(--c-notpetya)' },
    kasat:    { name: 'KA-SAT / Viasat', codename: 'VIASAT KA-SAT', date: 'FEB 2022', hex: '#1A6BE8', cssvar: 'var(--c-kasat)' },
    pap:      { name: 'PAP Hack',        codename: 'PAP HACK',      date: 'MAY 2024', hex: '#E81A1A', cssvar: 'var(--c-pap)' }
  };
  const ORDER = ['notpetya', 'kasat', 'pap'];

  // home overview cards
  const CASES = [
    {
      id: 'notpetya', codename: 'NOTPETYA', date: 'JUNE 2017', color: '#E8521A',
      scores: { tci: 0.662, ivc: 0.468, cidi: 0.546 }, sub: { attrDrift: 0.291, narrFrag: 0.646, rtp: 0.422 },
      coverage: 0.80, actors: 'Sandworm (GRU), Ukraine SBU, US CISA, EU Council, Maersk, Merck',
      attribution: 'CONTESTED → ATTRIBUTED', attributionMeta: 'Feb 2018 · US / UK / AU',
      corpus: '18 documents · 15 public + 3 technical',
      sources: [
        { id: 'pub_006', name: 'US-CERT / CISA', type: 'INSTITUTIONAL', url: 'https://www.cisa.gov/news-events/alerts/2017/07/01/petya-ransomware', status: 'verified' },
        { id: 'pub_009', name: 'White House', type: 'INSTITUTIONAL', url: 'https://trumpwhitehouse.archives.gov/briefings-statements/statement-press-secretary-25/', status: 'verified' },
        { id: 'pub_008', name: 'UK Foreign Office', type: 'INSTITUTIONAL', url: 'https://www.gov.uk/government/news/foreign-office-minister-condemns-russia-for-notpetya-attacks', status: 'verified' },
        { id: 'pub_015', name: 'European Council', type: 'INSTITUTIONAL', url: 'https://www.consilium.europa.eu/en/press/press-releases/2020/07/30/eu-imposes-the-first-ever-sanctions-against-cyber-attacks/', status: 'verified' },
        { id: 'tech_001', name: 'Cisco Talos', type: 'TECHNICAL', url: 'https://blog.talosintelligence.com/2017/07/the-medoc-connection.html', status: 'verified' },
        { id: 'tech_003', name: 'SentinelOne', type: 'TECHNICAL', url: 'https://www.sentinelone.com/blog/dissecting-notpetya-so-you-thought-it-was-ransomware/', status: 'verified' },
        { id: 'pub_007', name: 'Ukraine SBU (via SecurityAffairs)', type: 'INSTITUTIONAL', url: 'https://securityaffairs.com/60562/intelligence/sbu-investigation-notpetya.html', status: 'cross' },
        { id: 'pub_012', name: 'Wired', type: 'MAINSTREAM', url: 'https://www.wired.com/story/notpetya-cyberattack-ukraine-russia-code-crashed-the-world', status: 'verified' }
      ]
    },
    {
      id: 'kasat', codename: 'VIASAT KA-SAT', date: 'FEBRUARY 2022', color: '#1A6BE8',
      scores: { tci: 0.550, ivc: 0.342, cidi: 0.425 }, sub: { attrDrift: 0.174, narrFrag: 0.509, rtp: null },
      coverage: 0.60, actors: 'GRU (AcidRain malware), Viasat Inc., SentinelLabs, EU / EEAS, NCSC UK, Enercon (collateral)',
      attribution: 'ATTRIBUTED', attributionMeta: 'May 2022 · EU / UK / US joint statement',
      corpus: '18 documents · 15 public + 3 technical',
      sources: [
        { id: 'tech_001', name: 'Viasat', type: 'TECHNICAL', url: 'https://www.viasat.com/perspectives/corporate/2022/ka-sat-network-cyber-attack-overview/', status: 'verified' },
        { id: 'tech_002', name: 'SentinelLabs', type: 'TECHNICAL', url: 'https://www.sentinelone.com/labs/acidrain-a-modem-wiper-rains-down-on-europe/', status: 'verified' },
        { id: 'pub_014', name: 'Council of the EU / EEAS', type: 'INSTITUTIONAL', url: 'https://euneighbourseast.eu/news-and-stories/latest-news/european-union-strongly-condemns-cyberattack-against-ukraine/', status: 'verified' },
        { id: 'pub_015', name: 'European Commission', type: 'INSTITUTIONAL', url: 'https://ec.europa.eu/newsroom/cipr/redirection/item/740427/en/2357', status: 'verified' },
        { id: 'pub_004', name: 'Reuters (UK NCSC attribution)', type: 'MAINSTREAM', url: 'https://www.reuters.com/world/uk/uk-says-russia-was-behind-feb-24-viasat-cyber-attack-2022-05-10/', status: 'verified' },
        { id: 'pub_007', name: 'The Washington Post', type: 'MAINSTREAM', url: 'https://www.washingtonpost.com/national-security/2022/03/24/russian-military-behind-hack-satellite-communication-devices-ukraine-wars-outset-us-officials-say/', status: 'verified' },
        { id: 'pub_006', name: 'Wired', type: 'MAINSTREAM', url: 'https://www.wired.com/story/viasat-internet-hack-ukraine-russia/', status: 'verified' },
        { id: 'tech_003', name: 'MITRE ATT&CK · AcidRain (S1125)', type: 'TECHNICAL', url: 'https://attack.mitre.org/software/S1125/', status: 'contextual' }
      ]
    },
    {
      id: 'pap', codename: 'PAP HACK', date: 'MAY 2024', color: '#E81A1A',
      scores: { tci: 0.250, ivc: 0.353, cidi: 0.312 }, sub: { attrDrift: 0.110, narrFrag: 0.595, rtp: 0.167 },
      coverage: 0.40, actors: 'PAP (Polish Press Agency), ABW, Min. Gawkowski, PM Tusk, NASK / CERT.pl, Notes from Poland',
      attribution: 'APT28 (Russian GRU)', attributionMeta: 'Unofficial attribution',
      corpus: '17 documents · 15 public + 2 technical',
      sources: [
        { id: 'pub_001', name: 'PAP (Polska Agencja Prasowa)', type: 'INSTITUTIONAL', url: 'https://www.pap.pl/en/news/fake-pap-report-looks-cyberattack-says-govt-official', status: 'verified' },
        { id: 'tech_001', name: 'Cybernews', type: 'TECHNICAL', url: 'https://cybernews.com/security/russian-hackers-poland-pap-fake-news-ukraine-military/', status: 'verified' },
        { id: 'pub_012', name: 'Alliance for Securing Democracy (GMF)', type: 'INSTITUTIONAL', url: 'https://securingdemocracy.gmfus.org/incident/russian-hack-leads-to-false-news-agency-story-about-polish-mobilization/', status: 'verified' },
        { id: 'pub_008', name: 'Euractiv', type: 'MAINSTREAM', url: 'https://www.euractiv.com/news/poland-sees-russian-cyberattack-behind-fake-military-draft-report/', status: 'verified' },
        { id: 'pub_004', name: 'Tusk / Gawkowski (via Notes from Poland)', type: 'MAINSTREAM', url: 'https://notesfrompoland.com/2024/05/31/fake-polish-press-agency-reports-on-sending-troops-to-ukraine-blamed-on-russian-hackers/', status: 'cross' },
        { id: 'pub_007', name: 'ABW (via RDC.pl)', type: 'INSTITUTIONAL', url: 'https://www.rdc.pl/aktualnosci/polska/atak-hakerski-pap-mobilizacja-dementi-dobrzynski-cyberatak-wojna-hybrydowa_Gct0NJQDIbORD30CxBMl', status: 'cross' },
        { id: 'pub_002', name: 'AP (via US News)', type: 'MAINSTREAM', url: 'https://www.usnews.com/news/world/articles/2024-05-31/poland-says-a-fake-news-report-on-mobilizing-200-000-men-was-likely-the-work-of-russia', status: 'cross' },
        { id: 'pub_014', name: 'NASK → CERT.pl · APT28 (pre-incident)', type: 'INSTITUTIONAL', url: 'https://cert.pl/en/posts/2024/05/apt28-campaign/', status: 'contextual' }
      ]
    }
  ];

  // TCI component-level (5 ATT&CK components, evidence status + raw value)
  const COMP_ORDER = ['tactics', 'techniques', 'stealth', 'persistence', 'lateral_movement'];
  const COMP_LABEL = { tactics: 'Tactics', techniques: 'Techniques', stealth: 'Stealth', persistence: 'Persistence', lateral_movement: 'Lateral Mvmt' };
  const ST_LABEL = { present: 'Documented', absence: 'Doc. absence', inferred: 'Inferred', unknown: 'Unknown' };
  const ST_FULL = { present: 'documented_present', absence: 'documented_absence', inferred: 'inferred', unknown: 'unknown' };
  const TCI = {
    notpetya: { floor: 0.580, ea: 0.6625, assessed: 0.580, cov: 0.80, comps: { tactics: { v: 0.90, st: 'present' }, techniques: { v: 0.75, st: 'present' }, stealth: { v: 0.25, st: 'inferred' }, persistence: { v: 0.00, st: 'absence' }, lateral_movement: { v: 1.00, st: 'present' } } },
    kasat:    { floor: 0.370, ea: 0.550, assessed: 0.4625, cov: 0.60, comps: { tactics: { v: 0.40, st: 'present' }, techniques: { v: 0.25, st: 'present' }, stealth: { v: 0.20, st: 'inferred' }, persistence: { v: 0.00, st: 'unknown' }, lateral_movement: { v: 1.00, st: 'present' } } },
    pap:      { floor: 0.100, ea: 0.250, assessed: 0.250, cov: 0.40, comps: { tactics: { v: 0.40, st: 'present' }, techniques: { v: 0.10, st: 'present' }, stealth: { v: 0.50, st: 'unknown' }, persistence: { v: 0.00, st: 'unknown' }, lateral_movement: { v: 0.00, st: 'unknown' } } }
  };

  // IVA per case
  const IVA = {
    notpetya: {
      attrDrift: 0.2909, attrComps: { actor_plurality: 0.000, temporal_instability: 0.3333, convergence_delay: 0.6384, confidence_dispersion: 0.2400 },
      converged: '2018-02-15', convDays: 233, crisis: '2017-06-27',
      narrFrag: 0.6458, nfK: 4, nfSens: [[3, 0.5796], [4, 0.6458], [5, 0.6826]], nfClusters: [7, 4, 1, 3],
      rtp: 0.4222, rtpVoid: 4, rtpAvail: true, tgCos: 0.286, tgJac: 0.843, ivc: 0.468,
      seq: [
        { d: '2017-10-01', a: 'russia', st: 'attributed', c: 'high', id: 'pub_007' },
        { d: '2018-02-14', a: 'russia', st: 'attributed', c: 'high', id: 'pub_008' },
        { d: '2018-02-15', a: 'russia', st: 'attributed', c: 'high', id: 'pub_009' },
        { d: '2018-02-15', a: 'russia', st: 'attributed', c: 'high', id: 'pub_010' },
        { d: '2018-02-15', a: 'russia', st: 'attributed', c: 'high', id: 'pub_011' },
        { d: '2018-12-01', a: 'unknown', st: 'attributed', c: 'low', id: 'pub_013' },
        { d: '2020-07-30', a: 'russia', st: 'attributed', c: 'high', id: 'pub_015' }
      ]
    },
    kasat: {
      attrDrift: 0.1742, attrComps: { actor_plurality: 0.000, temporal_instability: 0.0909, convergence_delay: 0.1616, confidence_dispersion: 0.5556 },
      converged: '2022-05-09', convDays: 59, crisis: '2022-02-24',
      narrFrag: 0.5093, nfK: 4, nfSens: [[3, 0.5236], [4, 0.5093], [5, 0.5503]], nfClusters: [8, 4, 2, 1],
      rtp: null, rtpVoid: null, rtpAvail: false, tgCos: 0.354, tgJac: 0.909, ivc: 0.342,
      seq: [
        { d: '2022-03-11', a: 'unknown', st: 'uncertain', c: 'none', id: 'pub_003' },
        { d: '2022-03-23', a: 'unknown', st: 'uncertain', c: 'none', id: 'pub_006' },
        { d: '2022-03-24', a: 'russia', st: 'attributed', c: 'medium', id: 'pub_007' },
        { d: '2022-03-31', a: 'russia', st: 'attributed', c: 'medium', id: 'pub_008' },
        { d: '2022-05-09', a: 'russia', st: 'attributed', c: 'high', id: 'pub_001' },
        { d: '2022-05-09', a: 'russia', st: 'attributed', c: 'high', id: 'pub_002' },
        { d: '2022-05-09', a: 'russia', st: 'attributed', c: 'high', id: 'pub_009' },
        { d: '2022-05-10', a: 'russia', st: 'attributed', c: 'high', id: 'pub_004' },
        { d: '2022-05-10', a: 'russia', st: 'attributed', c: 'high', id: 'pub_005' },
        { d: '2022-05-10', a: 'russia', st: 'attributed', c: 'high', id: 'pub_014' },
        { d: '2022-05-11', a: 'russia', st: 'attributed', c: 'high', id: 'pub_012' },
        { d: '2022-05-11', a: 'russia', st: 'attributed', c: 'high', id: 'pub_013' }
      ]
    },
    pap: {
      attrDrift: 0.1103, attrComps: { actor_plurality: 0.000, temporal_instability: 0.2222, convergence_delay: 0.0027, confidence_dispersion: 0.2704 },
      converged: '2024-06-01', convDays: 1, crisis: '2024-05-31',
      narrFrag: 0.5948, nfK: 4, nfSens: [[3, 0.5150], [4, 0.5948], [5, 0.6270]], nfClusters: [2, 7, 4, 1],
      rtp: 0.1667, rtpVoid: 0, rtpAvail: true, tgCos: 0.272, tgJac: 0.898, ivc: 0.353,
      seq: [
        { d: '2024-05-31', a: 'russia', st: 'attributed', c: 'medium', id: 'pub_002' },
        { d: '2024-05-31', a: 'unknown', st: 'uncertain', c: 'none', id: 'pub_003' },
        { d: '2024-05-31', a: 'russia', st: 'attributed', c: 'high', id: 'pub_005' },
        { d: '2024-05-31', a: 'russia', st: 'attributed', c: 'high', id: 'pub_006' },
        { d: '2024-06-01', a: 'russia', st: 'attributed', c: 'medium', id: 'pub_007' },
        { d: '2024-06-01', a: 'russia', st: 'attributed', c: 'medium', id: 'pub_008' },
        { d: '2024-06-01', a: 'russia', st: 'attributed', c: 'medium', id: 'pub_009' },
        { d: '2024-06-01', a: 'russia', st: 'attributed', c: 'medium', id: 'pub_011' },
        { d: '2024-06-05', a: 'russia', st: 'attributed', c: 'medium', id: 'pub_012' },
        { d: '2024-09-01', a: 'russia', st: 'attributed', c: 'medium', id: 'pub_013' }
      ]
    }
  };
  const ATTR_W = { actor_plurality: 0.30, temporal_instability: 0.25, convergence_delay: 0.25, confidence_dispersion: 0.20 };
  const ATTR_LABEL = { actor_plurality: 'Actor plurality', temporal_instability: 'Temporal instability', convergence_delay: 'Convergence delay', confidence_dispersion: 'Confidence dispersion' };

  // CIDI scenario matrix
  const CIDI = {
    notpetya: { core: { neutral: 0.5654, interp: 0.5460, tech: 0.5848 }, ext: { neutral: 0.5608, interp: 0.5405, tech: 0.5812 }, tci: 0.6625, ivc: 0.4684, cov: 0.80 },
    kasat:    { core: { neutral: 0.4459, interp: 0.4251, tech: 0.4667 }, ext: null, tci: 0.5500, ivc: 0.3418, cov: 0.60 },
    pap:      { core: { neutral: 0.3013, interp: 0.3115, tech: 0.2910 }, ext: { neutral: 0.2827, interp: 0.2892, tech: 0.2762 }, tci: 0.2500, ivc: 0.3526, cov: 0.40 }
  };
  const RANKING = {
    coreOrder: ['notpetya', 'kasat', 'pap'], coreStable: true,
    extOrder: ['notpetya', 'pap'], extStable: true
  };

  const NET = {
    'Threat Actors': [['Sandworm · GRU Unit 74455', '#E8521A'], ['GRU · AcidRain wiper', '#1A6BE8'], ['APT28 · Fancy Bear', '#E81A1A']],
    'Victim Organizations': [['Maersk', '#E8521A'], ['Merck', '#E8521A'], ['Ukraine infrastructure', '#E8521A'], ['Viasat Inc.', '#1A6BE8'], ['KA-SAT network', '#1A6BE8'], ['Enercon (collateral)', '#1A6BE8'], ['PAP · Polish Press Agency', '#E81A1A']],
    'Institutional Responders': [['US CISA / US-CERT', '#E8521A'], ['UK Foreign Office', '#E8521A'], ['European Council', '#E8521A'], ['Ukraine SBU', '#E8521A'], ['EU / EEAS', '#1A6BE8'], ['NCSC UK', '#1A6BE8'], ['European Commission', '#1A6BE8'], ['ABW', '#E81A1A'], ['NASK / CERT.pl', '#E81A1A'], ['Min. Gawkowski', '#E81A1A'], ['PM Tusk', '#E81A1A']],
    'Media & Research': [['Wired', '#E8521A'], ['Cisco Talos', '#E8521A'], ['SecurityAffairs', '#E8521A'], ['Washington Post', '#1A6BE8'], ['SentinelLabs', '#1A6BE8'], ['Reuters', '#1A6BE8'], ['Notes from Poland', '#E81A1A'], ['Cybernews', '#E81A1A'], ['Euractiv', '#E81A1A']]
  };

  const STATUS_LABEL = { verified: '✓ VERIFIED', cross: '⚠ CROSS-SOURCE', contextual: '○ CONTEXTUAL' };
  const TYPE_ABBR = { INSTITUTIONAL: 'INST', MAINSTREAM: 'MAIN', TECHNICAL: 'TECH' };
  const ST_COLOR = { present: 'var(--st-present)', absence: 'var(--st-absence)', inferred: 'var(--st-inferred)', unknown: 'var(--st-unknown)' };

  /* --------------------------------------------------------------- HELPERS */
  const f3 = v => v.toFixed(3);
  const f2 = v => v.toFixed(2);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const hostOf = u => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return u; } };
  const days = d => Date.parse(d + 'T00:00:00Z');
  function frag(html) { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstElementChild; }

  /* --------------------------------------------------------------- TOOLTIP */
  let tipEl = null;
  function tip() { if (!tipEl) { tipEl = frag('<div class="tip" role="status" aria-live="polite"></div>'); document.body.appendChild(tipEl); } return tipEl; }
  function showTip(title, body, x, y) {
    const t = tip();
    t.innerHTML = (title ? '<b>' + esc(title) + '</b>' : '') + (body ? '<div>' + esc(body).replace(/\n/g, '<br>') + '</div>' : '');
    t.style.left = Math.min(x + 14, window.innerWidth - 250) + 'px';
    t.style.top = Math.max(10, y - 10) + 'px';
    t.classList.add('show');
  }
  function hideTip() { if (tipEl) tipEl.classList.remove('show'); }
  function wireTips(root) {
    root.querySelectorAll('[data-tt]').forEach(n => {
      const title = n.getAttribute('data-tt'); const body = n.getAttribute('data-tb') || '';
      n.setAttribute('tabindex', '0');
      n.addEventListener('mouseenter', e => showTip(title, body, e.clientX, e.clientY));
      n.addEventListener('mousemove', e => showTip(title, body, e.clientX, e.clientY));
      n.addEventListener('mouseleave', hideTip);
      n.addEventListener('focus', () => { const r = n.getBoundingClientRect(); showTip(title, body, r.left + r.width / 2, r.top); });
      n.addEventListener('blur', hideTip);
    });
  }

  /* ------------------------------------------------------ A11Y DATA TABLE */
  function addTable(mount, caption, headers, rows) {
    const id = 'dt-' + Math.abs(caption.split('').reduce((a, c) => a + c.charCodeAt(0) * 31, 0)) + '-' + mount.children.length;
    const thead = '<tr>' + headers.map((h, i) => '<th scope="col">' + esc(h) + '</th>').join('') + '</tr>';
    const body = rows.map(r => '<tr>' + r.map((c, i) => i === 0 ? '<th scope="row">' + esc(c) + '</th>' : '<td>' + esc(c) + '</td>').join('') + '</tr>').join('');
    const wrap = frag('<div style="margin-top:14px"><button class="dtbl-btn" aria-expanded="false" aria-controls="' + id + '">Show data table</button>' +
      '<div class="dtbl" id="' + id + '" hidden><table><caption>' + esc(caption) + '</caption><thead>' + thead + '</thead><tbody>' + body + '</tbody></table></div></div>');
    const btn = wrap.querySelector('button'); const tbl = wrap.querySelector('.dtbl');
    btn.addEventListener('click', () => { const open = tbl.hidden; tbl.hidden = !open; btn.setAttribute('aria-expanded', String(open)); btn.textContent = open ? 'Hide data table' : 'Show data table'; });
    mount.appendChild(wrap);
  }

  /* ------------------------------------------------------ CHART: H-BARS */
  // opts: {title, ariaLabel, rows:[{label, value, color, status, tt}], max, fmt, unit, tableCaption}
  function hBars(mount, opts) {
    const rows = opts.rows, max = opts.max || 1, fmt = opts.fmt || f3;
    const W = 520, rowH = 38, padT = 14, padB = 26, labelW = 132, valueW = 56;
    const plotW = W - labelW - valueW;
    const H = padT + rows.length * rowH + padB;
    const x0 = labelW, x1 = labelW + plotW;
    let svg = '<svg class="chart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(opts.ariaLabel || opts.title || 'bar chart') + '" preserveAspectRatio="xMinYMin meet">';
    // gridlines + ticks (0, .25, .5, .75, 1 scaled to max)
    const ticks = [0, 0.25, 0.5, 0.75, 1];
    ticks.forEach(t => {
      const x = x0 + plotW * t;
      svg += '<line class="grid-line" x1="' + x + '" y1="' + padT + '" x2="' + x + '" y2="' + (H - padB) + '"/>';
      svg += '<text class="ax-label" x="' + x + '" y="' + (H - padB + 16) + '" text-anchor="middle">' + (t * max).toFixed(2) + '</text>';
    });
    rows.forEach((r, i) => {
      const y = padT + i * rowH; const cy = y + rowH / 2 - 2;
      const w = Math.max(2, plotW * (r.value / max));
      const col = r.color || 'var(--accent)';
      svg += '<text class="cat-label" x="' + (labelW - 12) + '" y="' + (cy + 4) + '" text-anchor="end">' + esc(r.label) + '</text>';
      const tt = r.tt ? ' data-tt="' + esc(r.label) + '" data-tb="' + esc(r.tt) + '"' : '';
      svg += '<g class="ch-bar"' + tt + '><rect class="bar-rect" x="' + x0 + '" y="' + (cy - 9) + '" width="' + w + '" height="14" fill="' + col + '"/></g>';
      svg += '<text class="val-label" x="' + (x1 + 8) + '" y="' + (cy + 4) + '">' + fmt(r.value) + (opts.unit || '') + '</text>';
    });
    svg += '</svg>';
    const wrap = frag('<div>' + svg + '</div>');
    mount.appendChild(wrap.firstChild);
    wireTips(mount);
    if (opts.tableCaption) addTable(mount, opts.tableCaption, ['Item', 'Value'], rows.map(r => [r.label, fmt(r.value) + (opts.unit || '')]));
    observeChart(mount.querySelector('.chart'));
  }

  /* ------------------------------------------ CHART: GROUPED V-BARS (small) */
  // opts: {groups:[{label}], series:[{name,color}], data:[[v per series] per group], max, fmt, ariaLabel, tableCaption, primaryIdx}
  function groupedVBars(mount, opts) {
    const groups = opts.groups, series = opts.series, data = opts.data, max = opts.max || 1, fmt = opts.fmt || f3;
    const gW = 150, H = 190, padT = 14, padB = 40, plotH = H - padT - padB;
    const W = groups.length * gW + 30;
    let svg = '<svg class="chart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(opts.ariaLabel || 'grouped bars') + '" preserveAspectRatio="xMinYMin meet">';
    [0, 0.5, 1].forEach(t => { const y = padT + plotH * (1 - t); svg += '<line class="grid-line" x1="22" y1="' + y + '" x2="' + (W - 4) + '" y2="' + y + '"/><text class="ax-label" x="16" y="' + (y + 3) + '" text-anchor="end">' + (t * max).toFixed(1) + '</text>'; });
    groups.forEach((g, gi) => {
      const gx = 30 + gi * gW; const bw = Math.min(34, (gW - 30) / series.length);
      const inner = bw * series.length + (series.length - 1) * 8;
      const startX = gx + ((gW - 24) - inner) / 2;
      series.forEach((s, si) => {
        const v = data[gi][si]; const h = Math.max(1, plotH * (v / max));
        const x = startX + si * (bw + 8); const y = padT + plotH - h;
        const hi = (opts.primaryIdx != null && si === opts.primaryIdx);
        svg += '<g class="ch-grow" data-tt="' + esc(g.label + ' · ' + s.name) + '" data-tb="value ' + fmt(v) + '">' +
          '<rect class="bar-rect" x="' + x + '" y="' + y + '" width="' + bw + '" height="' + h + '" fill="' + s.color + '"' + (hi ? ' stroke="var(--text)" stroke-width="1"' : '') + '/></g>' +
          '<text class="ax-label" x="' + (x + bw / 2) + '" y="' + (padT + plotH + 13) + '" text-anchor="middle">' + esc(s.name) + '</text>';
      });
      svg += '<text class="cat-label" x="' + (gx + (gW - 24) / 2) + '" y="' + (H - 8) + '" text-anchor="middle" font-weight="700">' + esc(g.label) + '</text>';
    });
    svg += '</svg>';
    mount.appendChild(frag('<div>' + svg + '</div>').firstChild);
    wireTips(mount);
    if (opts.tableCaption) addTable(mount, opts.tableCaption, ['Group'].concat(series.map(s => s.name)), groups.map((g, gi) => [g.label].concat(data[gi].map(fmt))));
    observeChart(mount.querySelector('.chart'));
  }

  /* ------------------------------------------ CHART: STACKED COMPOSITION */
  // opts: {rows:[{label, segs:[{value,color,name}], total}], max, fmt, ariaLabel, tableCaption}
  function stacked(mount, opts) {
    const rows = opts.rows, max = opts.max || 1, fmt = opts.fmt || f3;
    const W = 520, rowH = 46, padT = 12, padB = 26, labelW = 132, valueW = 56, plotW = W - labelW - valueW;
    const H = padT + rows.length * rowH + padB; const x0 = labelW;
    let svg = '<svg class="chart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(opts.ariaLabel || 'stacked bars') + '" preserveAspectRatio="xMinYMin meet">';
    [0, 0.25, 0.5, 0.75, 1].forEach(t => { const x = x0 + plotW * t; svg += '<line class="grid-line" x1="' + x + '" y1="' + padT + '" x2="' + x + '" y2="' + (H - padB) + '"/><text class="ax-label" x="' + x + '" y="' + (H - padB + 16) + '" text-anchor="middle">' + (t * max).toFixed(2) + '</text>'; });
    rows.forEach((r, i) => {
      const y = padT + i * rowH; const cy = y + rowH / 2 - 2; let acc = 0;
      svg += '<text class="cat-label" x="' + (labelW - 12) + '" y="' + (cy + 4) + '" text-anchor="end">' + esc(r.label) + '</text>';
      r.segs.forEach(sg => {
        const w = plotW * (sg.value / max); const x = x0 + plotW * (acc / max);
        svg += '<g class="ch-bar" data-tt="' + esc(r.label + ' · ' + sg.name) + '" data-tb="' + esc('contributes ' + fmt(sg.value)) + '"><rect class="bar-rect" x="' + x + '" y="' + (cy - 10) + '" width="' + Math.max(1, w) + '" height="16" fill="' + sg.color + '"/></g>';
        acc += sg.value;
      });
      svg += '<text class="val-label" x="' + (x0 + plotW + 8) + '" y="' + (cy + 4) + '">' + fmt(r.total) + '</text>';
    });
    svg += '</svg>';
    mount.appendChild(frag('<div>' + svg + '</div>').firstChild);
    wireTips(mount);
    if (opts.tableCaption) addTable(mount, opts.tableCaption, ['Case'].concat(rows[0].segs.map(s => s.name)).concat(['Total']), rows.map(r => [r.label].concat(r.segs.map(s => fmt(s.value))).concat([fmt(r.total)])));
    observeChart(mount.querySelector('.chart'));
  }

  /* ------------------------------------------------- INTERSECTION OBSERVER */
  const chartObs = ('IntersectionObserver' in window) ? new IntersectionObserver((es, o) => {
    es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); o.unobserve(e.target); } });
  }, { threshold: 0.2 }) : null;
  function observeChart(el) { if (!el) return; if (chartObs) chartObs.observe(el); else el.classList.add('in'); }

  /* ============================ NAMED CHART DISPATCH ====================== */
  const CHARTS = {
    /* ---------- TCI ---------- */
    'tci-evidence': function (m) {
      const legend = '<div class="clegend">' +
        '<span><i style="background:var(--st-present)"></i>Documented present</span>' +
        '<span><i style="background:var(--st-absence)"></i>Documented absence</span>' +
        '<span><i style="background:var(--st-inferred)"></i>Inferred (excl. from evidence-adj.)</span>' +
        '<span><i style="background:var(--st-unknown)"></i>Unknown (excluded)</span></div>';
      let h = '<table class="hm"><thead><tr><th class="rowhead">Case \\ Component</th>' +
        COMP_ORDER.map(c => '<th>' + COMP_LABEL[c] + '</th>').join('') + '</tr></thead><tbody>';
      ORDER.forEach(k => {
        h += '<tr><td class="rowhead">' + CASE_META[k].name + '</td>';
        COMP_ORDER.forEach(c => {
          const cell = TCI[k].comps[c]; const col = ST_COLOR[cell.st];
          const opacity = cell.st === 'unknown' ? 0.5 : 1;
          h += '<td><div class="cell" style="border-color:' + col + ';background:rgba(255,255,255,0.02)" data-tt="' + esc(CASE_META[k].name + ' · ' + COMP_LABEL[c]) + '" data-tb="' + esc('status: ' + ST_FULL[cell.st] + '\nraw value: ' + f2(cell.v)) + '">' +
            '<span class="cv" style="opacity:' + opacity + '">' + f2(cell.v) + '</span>' +
            '<span class="cs" style="color:' + col + '">' + ST_LABEL[cell.st] + '</span></div></td>';
        });
        h += '</tr>';
      });
      h += '</tbody></table>';
      m.innerHTML = legend + '<div class="xscroll">' + h + '</div>';
      wireTips(m);
      addTable(m, 'TCI component raw values by case (status in parentheses)', ['Case'].concat(COMP_ORDER.map(c => COMP_LABEL[c])),
        ORDER.map(k => [CASE_META[k].name].concat(COMP_ORDER.map(c => f2(TCI[k].comps[c].v) + ' (' + ST_FULL[TCI[k].comps[c].st] + ')'))));
    },
    'tci-variants': function (m) {
      groupedVBars(m, {
        groups: ORDER.map(k => ({ label: CASE_META[k].name })),
        series: [{ name: 'floor', color: 'var(--st-unknown)' }, { name: 'evid-adj', color: 'var(--accent)' }, { name: 'assessed', color: 'var(--st-absence)' }],
        data: ORDER.map(k => [TCI[k].floor, TCI[k].ea, TCI[k].assessed]),
        max: 1, primaryIdx: 1, ariaLabel: 'TCI score variants — conservative floor, evidence-adjusted, assessed-with-inference — per case',
        tableCaption: 'TCI score variants by case'
      });
    },
    'tci-coverage': function (m) {
      hBars(m, {
        ariaLabel: 'TCI evidence coverage per case',
        rows: ORDER.map(k => ({ label: CASE_META[k].name, value: TCI[k].cov, color: CASE_META[k].cssvar, tt: 'evidence coverage ' + f2(TCI[k].cov) })),
        max: 1, fmt: f2, tableCaption: 'TCI evidence coverage by case'
      });
    },

    /* ---------- IVA ---------- */
    'iva-dimensions': function (m) {
      // small multiples: one h-bar panel per case (4 dimensions)
      const dims = [
        { key: 'attrDrift', label: 'Attribution Drift', core: true },
        { key: 'narrFrag', label: 'Narrative Frag.', core: true },
        { key: 'rtp', label: 'Response Timing', core: false, ctx: true },
        { key: 'tg', label: 'Tech–Public Gap', core: false, diag: true }
      ];
      const grid = frag('<div class="grid-3"></div>');
      ORDER.forEach(k => {
        const d = IVA[k];
        const panel = frag('<div><div class="panel-head" style="margin-bottom:14px"><span class="cdot" style="display:inline-block;width:9px;height:9px;background:' + CASE_META[k].cssvar + '"></span><h3 style="font-size:13px">' + CASE_META[k].name + '</h3></div></div>');
        const sub = document.createElement('div');
        const rows = dims.map(dim => {
          let v, tt, col;
          if (dim.key === 'attrDrift') { v = d.attrDrift; col = 'var(--st-present)'; tt = 'CORE · weight 0.5 in IVC'; }
          else if (dim.key === 'narrFrag') { v = d.narrFrag; col = 'var(--st-present)'; tt = 'CORE · weight 0.5 in IVC'; }
          else if (dim.key === 'rtp') { v = d.rtpAvail ? d.rtp : 0; col = 'var(--st-inferred)'; tt = d.rtpAvail ? 'CONTEXTUAL · Extended CIDI only' : 'UNAVAILABLE — insufficient early-window evidence; never imputed'; }
          else { v = d.tgCos; col = 'var(--st-absence)'; tt = 'DIAGNOSTIC · excluded from every aggregate (cosine distance)'; }
          return { label: dim.label, value: v, color: col, tt: tt };
        });
        panel.appendChild(sub);
        hBars(sub, { ariaLabel: CASE_META[k].name + ' IVA dimensions', rows: rows, max: 1, fmt: f3 });
        // annotate KA-SAT RTP as N/A
        if (!d.rtpAvail) {
          const na = frag('<div class="mono" style="font-size:9.5px;color:var(--text-dim);letter-spacing:0.05em;margin-top:-4px">⚠ Response Timing UNAVAILABLE (not imputed) · shown as 0</div>');
          sub.appendChild(na);
        }
        grid.appendChild(panel);
      });
      m.appendChild(grid);
    },
    'iva-attrdrift': function (m) {
      groupedVBars(m, {
        groups: ORDER.map(k => ({ label: CASE_META[k].name })),
        series: Object.keys(ATTR_W).map((c, i) => ({ name: ATTR_LABEL[c].split(' ')[0], color: ['var(--st-present)', 'var(--st-inferred)', 'var(--accent)', 'var(--st-absence)'][i] })),
        data: ORDER.map(k => Object.keys(ATTR_W).map(c => IVA[k].attrComps[c])),
        max: 1, ariaLabel: 'Attribution Drift sub-component scores by case (actor plurality, temporal instability, convergence delay, confidence dispersion)',
        tableCaption: 'Attribution Drift sub-components by case (weights: plurality 0.30, temporal 0.25, convergence 0.25, dispersion 0.20)'
      });
    },
    'iva-timelines': function (m) {
      ORDER.forEach(k => {
        const d = IVA[k]; const meta = CASE_META[k];
        const min = days(d.crisis); const maxD = days(d.seq[d.seq.length - 1].d); const span = Math.max(1, maxD - min);
        const block = frag('<div style="margin-bottom:30px"><div class="mono" style="font-size:11px;color:var(--text);letter-spacing:0.06em;margin-bottom:2px"><span style="display:inline-block;width:9px;height:9px;background:' + meta.cssvar + ';margin-right:8px"></span>' + meta.name +
          ' <span style="color:var(--text-dim)">· drift ' + f3(d.attrDrift) + ' · converged @ ' + d.converged + ' (' + d.convDays + 'd)</span></div>' +
          '<div class="mono" style="font-size:8.5px;color:var(--text-dim);letter-spacing:0.05em">crisis ' + d.crisis + ' → ' + d.seq[d.seq.length - 1].d + '</div>' +
          '<div class="tl"><div class="tl-track"></div></div></div>');
        const track = block.querySelector('.tl-track');
        // convergence marker
        const convX = ((days(d.converged) - min) / span) * 100;
        const conv = frag('<div class="tl-conv" style="left:' + Math.min(96, Math.max(2, convX)) + '%"></div>');
        track.appendChild(conv);
        d.seq.forEach(ev => {
          let x = ((days(ev.d) - min) / span) * 100; x = Math.min(98, Math.max(2, x));
          const cls = ev.a === 'unknown' ? 'uncertain' : (ev.st === 'no_claim' ? 'no_claim' : 'attributed');
          const dot = frag('<div class="tl-dot ' + cls + '" style="left:' + x + '%" role="img" data-tt="' + esc(ev.id + ' · ' + ev.d) + '" data-tb="' + esc('state: ' + ev.st + '\nactor: ' + ev.a + '\nconfidence: ' + ev.c) + '" aria-label="' + esc(ev.id + ' ' + ev.d + ' actor ' + ev.a + ' confidence ' + ev.c) + '"></div>');
          track.appendChild(dot);
        });
        m.appendChild(block);
      });
      const legend = frag('<div class="clegend"><span><i style="background:var(--st-present)"></i>Actor identified (Russia)</span><span><i style="background:var(--st-inferred)"></i>Unresolved / uncertain</span><span><i style="background:var(--accent);width:2px"></i>Convergence point</span></div>');
      m.insertBefore(legend, m.firstChild);
      wireTips(m);
    },
    'iva-narrative': function (m) {
      groupedVBars(m, {
        groups: ORDER.map(k => ({ label: CASE_META[k].name })),
        series: [{ name: 'k=3', color: 'var(--st-unknown)' }, { name: 'k=4', color: 'var(--accent)' }, { name: 'k=5', color: 'var(--st-absence)' }],
        data: ORDER.map(k => IVA[k].nfSens.map(s => s[1])),
        max: 1, primaryIdx: 1, ariaLabel: 'Narrative Fragmentation K-Means sensitivity across k=3,4,5 per case; primary k=4 highlighted',
        tableCaption: 'Narrative Fragmentation by cluster count k (primary k=4)'
      });
    },
    'iva-ivc': function (m) {
      stacked(m, {
        rows: ORDER.map(k => ({ label: CASE_META[k].name, total: IVA[k].ivc, segs: [
          { name: '0.5 × Attribution Drift', value: 0.5 * IVA[k].attrDrift, color: 'var(--accent)' },
          { name: '0.5 × Narrative Frag.', value: 0.5 * IVA[k].narrFrag, color: 'var(--st-absence)' }
        ] })),
        max: 0.6, fmt: f3, ariaLabel: 'IVC core composition: equal-weighted Attribution Drift and Narrative Fragmentation per case',
        tableCaption: 'IVC core = 0.5×AttrDrift + 0.5×NarrFrag'
      });
      m.insertBefore(frag('<div class="clegend"><span><i style="background:var(--accent)"></i>0.5 × Attribution Drift</span><span><i style="background:var(--st-absence)"></i>0.5 × Narrative Fragmentation</span></div>'), m.firstChild);
    },

    /* ---------- CIDI ---------- */
    'cidi-matrix': function (m) {
      const scen = [['neutral', '0.50 / 0.50'], ['interp', '0.40 / 0.60'], ['tech', '0.60 / 0.40']];
      function block(kind, title) {
        // best per scenario column highlight
        let h = '<div class="mono" style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:var(--accent);margin:0 0 10px">' + title + '</div>';
        h += '<div class="xscroll"><table class="smatrix"><thead><tr><th class="rh">Case</th>' + scen.map(s => '<th>' + s[0] + '<br><span style="color:var(--text-mid);font-size:8px">TCI/IVC ' + s[1] + '</span></th>').join('') + '</tr></thead><tbody>';
        ORDER.forEach(k => {
          const sc = CIDI[k][kind];
          h += '<tr><td class="rh"><span style="display:inline-block;width:8px;height:8px;background:' + CASE_META[k].cssvar + ';margin-right:7px"></span>' + CASE_META[k].name + '</td>';
          scen.forEach(s => {
            if (!sc) { h += '<td><div class="sc na" data-tt="' + esc(CASE_META[k].name) + '" data-tb="Extended CIDI UNAVAILABLE — Response Timing Proxy not measurable; never imputed">N/A</div></td>'; return; }
            const v = sc[s[0]]; const inten = Math.max(0, Math.min(1, (v - 0.25) / 0.45));
            h += '<td><div class="sc" style="background:rgba(232,82,26,' + (0.08 + inten * 0.34).toFixed(3) + ')" data-tt="' + esc(CASE_META[k].name + ' · ' + kind + ' ' + s[0]) + '" data-tb="' + esc('CIDI ' + f3(v) + '\nTCI/IVC weights ' + s[1]) + '">' + f3(v) + '</div></td>';
          });
          h += '</tr>';
        });
        h += '</tbody></table></div>';
        return h;
      }
      const g = frag('<div class="grid-2"></div>');
      g.appendChild(frag('<div>' + block('core', 'CIDI Core · all cases') + '</div>'));
      g.appendChild(frag('<div>' + block('ext', 'CIDI Extended · + Response Timing') + '</div>'));
      m.appendChild(g);
      wireTips(m);
      addTable(m, 'CIDI Core & Extended scenario values', ['Case', 'Core neutral', 'Core interp', 'Core tech', 'Ext neutral', 'Ext interp', 'Ext tech'],
        ORDER.map(k => { const c = CIDI[k].core, e = CIDI[k].ext; return [CASE_META[k].name, f3(c.neutral), f3(c.interp), f3(c.tech), e ? f3(e.neutral) : 'N/A', e ? f3(e.interp) : 'N/A', e ? f3(e.tech) : 'N/A']; }));
    },
    'cidi-composition': function (m) {
      stacked(m, {
        rows: ORDER.map(k => ({ label: CASE_META[k].name, total: CIDI[k].core.interp, segs: [
          { name: '0.40 × TCI', value: 0.40 * CIDI[k].tci, color: 'var(--accent)' },
          { name: '0.60 × IVC', value: 0.60 * CIDI[k].ivc, color: 'var(--st-absence)' }
        ] })),
        max: 0.7, fmt: f3, ariaLabel: 'CIDI Core interpretive composition: 0.40 TCI plus 0.60 IVC per case',
        tableCaption: 'CIDI Core (interpretive 0.4/0.6) = 0.40×TCI + 0.60×IVC'
      });
      m.insertBefore(frag('<div class="clegend"><span><i style="background:var(--accent)"></i>0.40 × TCI<sub>EA</sub> (technical)</span><span><i style="background:var(--st-absence)"></i>0.60 × IVC (interpretive)</span></div>'), m.firstChild);
    },
    'cidi-sensitivity': function (m) {
      groupedVBars(m, {
        groups: ORDER.map(k => ({ label: CASE_META[k].name })),
        series: [{ name: 'neutral', color: 'var(--st-unknown)' }, { name: 'interp', color: 'var(--accent)' }, { name: 'technical', color: 'var(--st-absence)' }],
        data: ORDER.map(k => [CIDI[k].core.neutral, CIDI[k].core.interp, CIDI[k].core.tech]),
        max: 0.7, ariaLabel: 'CIDI Core under three weight scenarios per case',
        tableCaption: 'CIDI Core sensitivity across weight scenarios'
      });
    },
    'cidi-ranking': function (m) {
      function rankBlock(title, order, stable, getv) {
        let h = '<div class="mono" style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:var(--accent);margin-bottom:12px">' + title +
          ' <span style="color:var(--green-text)">· STABLE: ' + (stable ? 'YES' : 'NO') + '</span></div><div class="rank-cols">';
        order.forEach((k, i) => {
          h += '<div class="rankrow"><span class="rk">' + (i + 1) + '</span><span class="rcdot" style="background:' + CASE_META[k].cssvar + '"></span>' +
            '<span class="rname">' + CASE_META[k].name + '</span><span class="rval">' + getv(k) + '</span></div>';
        });
        h += '</div>';
        return h;
      }
      const g = frag('<div class="grid-2"></div>');
      g.appendChild(frag('<div>' + rankBlock('Core scenarios · 3 cases', RANKING.coreOrder, RANKING.coreStable, k => 'CIDI ' + f3(CIDI[k].core.interp)) + '</div>'));
      g.appendChild(frag('<div>' + rankBlock('Extended · available cases', RANKING.extOrder, RANKING.extStable, k => 'CIDI ' + f3(CIDI[k].ext.interp)) +
        '<div class="mono" style="font-size:9px;color:var(--text-dim);margin-top:12px;line-height:1.5">KA-SAT excluded — Extended CIDI unavailable (Response Timing not measurable). Descriptive ordering only; non-causal.</div></div>'));
      m.appendChild(g);
    }
  };

  /* ============================ HOME RENDERERS =========================== */
  function metricRow(name, value, extra) {
    return '<div class="metric"><div class="mtop"><span class="mname">' + name + '</span><span class="mval">' + f3(value) + '</span></div>' +
      '<div class="bar-track"><div class="bar-fill ' + (extra || '') + '" data-value="' + value + '"></div></div></div>';
  }
  function srcRows(sources) {
    return sources.map(s => '<tr><td class="sid">' + s.id + '</td><td>' + esc(s.name) + '</td><td class="stype" title="' + s.type + '">' + (TYPE_ABBR[s.type] || s.type) +
      '</td><td><a class="surl" href="' + s.url + '" target="_blank" rel="noopener" title="' + s.url + '">' + esc(hostOf(s.url)) + '</a></td>' +
      '<td><span class="sbadge ' + s.status + '">' + STATUS_LABEL[s.status] + '</span></td></tr>').join('');
  }
  function caseCard(c) {
    const rtp = c.sub.rtp === null ? '<div class="sv na">N/A</div><div class="sl">Resp. Timing<br>(unavailable)</div>' : '<div class="sv">' + f3(c.sub.rtp) + '</div><div class="sl">Resp.<br>Timing</div>';
    return '<div class="case" style="--ccol:' + c.color + '"><div class="chead"><div class="cn"><div class="codename"><span class="cdot"></span>' + c.codename + '</div><div class="cdate">' + c.date + '</div></div></div>' +
      '<div class="cbody">' + metricRow('TCI<sub>EA</sub>', c.scores.tci) + metricRow('IVC', c.scores.ivc) + metricRow('CIDI', c.scores.cidi, 'cidi') +
      '<div class="subgrid"><div><div class="sv">' + f3(c.sub.attrDrift) + '</div><div class="sl">Attribution<br>Drift</div></div>' +
      '<div><div class="sv">' + f3(c.sub.narrFrag) + '</div><div class="sl">Narrative<br>Fragmentation</div></div><div>' + rtp + '</div></div>' +
      '<div class="meta-rows"><div class="mrow"><span class="ml">Coverage</span><span class="mc">' + f2(c.coverage) + ' <span class="dim">evidence</span></span></div>' +
      '<div class="mrow"><span class="ml">Attribution</span><span class="mc"><span class="badge-attr">' + c.attribution + '</span><br><span class="dim" style="font-size:9.5px">' + c.attributionMeta + '</span></span></div>' +
      '<div class="mrow"><span class="ml">Key actors</span><span class="mc">' + esc(c.actors) + '</span></div>' +
      '<div class="mrow"><span class="ml">Corpus</span><span class="mc">' + c.corpus + '</span></div></div></div>' +
      '<div class="cfoot"><button class="src-btn" data-target="src-' + c.id + '" aria-expanded="false">View Sources <span class="arr">→</span></button>' +
      '<div class="sources-panel" id="src-' + c.id + '"><div class="sources-inner"><table class="src-table"><thead><tr><th>ID</th><th>Source</th><th>Type</th><th>URL</th><th>Status</th></tr></thead>' +
      '<tbody>' + srcRows(c.sources) + '</tbody></table><div class="src-foot">Full corpus: <a href="https://github.com/GiovanniArosio/cidf-framework" target="_blank" rel="noopener">github.com/GiovanniArosio/cidf-framework</a></div></div></div></div></div>';
  }
  function renderCases(mount) {
    mount.innerHTML = CASES.map(caseCard).join('');
    mount.querySelectorAll('.src-btn').forEach(btn => btn.addEventListener('click', () => {
      const p = document.getElementById(btn.dataset.target); const open = p.classList.toggle('open');
      btn.classList.toggle('open', open); btn.setAttribute('aria-expanded', String(open));
      btn.firstChild.textContent = open ? 'Hide Sources ' : 'View Sources ';
    }));
  }
  function renderActors(mount) {
    function hexA(hex, a) { const n = parseInt(hex.slice(1), 16); return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')'; }
    mount.innerHTML = Object.entries(NET).map(([col, tags]) => '<div class="net-col"><h3>' + col + '</h3><div class="tags">' +
      tags.map(([t, c]) => '<span class="tag" style="--tcol:' + c + ';--tglow:' + hexA(c, 0.4) + '">' + esc(t) + '</span>').join('') + '</div></div>').join('');
  }

  /* --------------------------------------------------- counters + barfill */
  function animateCounter(el) {
    const target = +el.dataset.target, dur = 1100, start = performance.now();
    function step(now) { const p = Math.min((now - start) / dur, 1), e = 1 - Math.pow(1 - p, 3); el.textContent = Math.round(e * target); if (p < 1) requestAnimationFrame(step); else el.textContent = target; }
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) { el.textContent = target; return; }
    requestAnimationFrame(step);
  }
  function wireBarFills() {
    const obs = ('IntersectionObserver' in window) ? new IntersectionObserver((es, o) => { es.forEach(e => { if (e.isIntersecting) { e.target.style.width = (parseFloat(e.target.dataset.value) * 100) + '%'; o.unobserve(e.target); } }); }, { threshold: 0.35 }) : null;
    document.querySelectorAll('.bar-fill').forEach(b => { if (obs) obs.observe(b); else b.style.width = (parseFloat(b.dataset.value) * 100) + '%'; });
  }

  /* --------------------------------------------------------- NAV active */
  function setActiveNav() {
    const page = document.body.getAttribute('data-page');
    document.querySelectorAll('.mainnav a[data-nav]').forEach(a => { if (a.getAttribute('data-nav') === page) a.setAttribute('aria-current', 'page'); });
  }

  /* --------------------------------------------------------------- INIT */
  function init() {
    setActiveNav();
    document.querySelectorAll('.stat .num[data-target]').forEach(animateCounter);
    const casesMount = document.getElementById('cases'); if (casesMount) renderCases(casesMount);
    const netMount = document.getElementById('net'); if (netMount) renderActors(netMount);
    document.querySelectorAll('[data-chart]').forEach(m => { const fn = CHARTS[m.getAttribute('data-chart')]; if (fn) { try { fn(m); } catch (e) { console.error('chart error', m.getAttribute('data-chart'), e); } } });
    wireBarFills();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();

  window.CIDF = { DATA: { CASES, TCI, IVA, CIDI, RANKING, CASE_META }, CHARTS, hBars, groupedVBars, stacked };
})();
