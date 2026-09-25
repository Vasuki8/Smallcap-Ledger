/* Research desk: UI composition and browser-local preferences only.
 * Loaded after the core client. The source/analytics/storage contracts are unchanged.
 */
(function () {
  'use strict';
  const SAVED_KEY = 'smallcap-ledger.saved.v1', MAX_COMPARE = 3;
  const paths = {
    explore: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    compare: '<path d="M8 3v18M16 3v18M3 7h10M11 17h10"/><path d="m5 4-3 3 3 3m14 4 3 3-3 3"/>',
    save: '<path d="M6 3h12v18l-6-4-6 4z"/>',
    data: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
    arrow: '<path d="M4 12h15m-6-6 6 6-6 6"/>',
    close: '<path d="m6 6 12 12M6 18 18 6"/>',
    external: '<path d="M14 3h7v7m0-7L10 14M10 3H4v17h17v-6"/>',
    shield: '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6z"/><path d="m8 12 3 3 5-6"/>',
    back: '<path d="M20 12H5m6-6-6 6 6 6"/>'
  };
  const icon = name => `<svg viewBox="0 0 24 24" class="icon" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${paths[name] || paths.explore}</svg>`;
  function codes(value) {
    if (!Array.isArray(value)) return [];
    return [...new Set(value.filter(x => (typeof x === 'number' || typeof x === 'string') && /^\d+$/.test(String(x))).map(Number).filter(x => Number.isSafeInteger(x) && x > 0))];
  }
  function number(value) {
    if (value === null || value === undefined || (typeof value === 'string' && !value.trim()) || !['number','string'].includes(typeof value)) return null;
    const n = Number(value); return Number.isFinite(n) ? n : null;
  }
  function safeURL(url) {
    try { const u = new URL(String(url)); return ['https:', 'http:'].includes(u.protocol) ? u.href : ''; }
    catch { return ''; }
  }
  function sortFunds(rows, key, direction = 'desc') {
    const value = f => key === 'family' ? f.family : key === 'aum' ? f.metrics?.aum?.value : key === 'ter' ? (f.metrics?.ter || f.metrics?.ter_observed || f.metrics?.base_expense_ratio || f.metrics?.expense_ratio)?.value : key === 'nav' ? f.nav?.value : f.returns?.[key];
    return [...rows].sort((a, b) => {
      let delta;
      if (key === 'family') delta = String(value(a) || '').localeCompare(String(value(b) || ''));
      else {
        const x = number(value(a)), y = number(value(b));
        if (x === null && y !== null) return 1;
        if (y === null && x !== null) return -1;
        delta = x === null && y === null ? 0 : x - y;
      }
      return (direction === 'asc' ? delta : -delta) || String(a.family).localeCompare(String(b.family)) || a.code - b.code;
    });
  }
  function sourceState(source) {
    if (source.enabled === 0 || source.enabled === false || source.status === 'Excluded') return 'inactive';
    if (['Checked', 'OK', 'ok', 'Success'].includes(source.status)) return 'checked';
    if (['Gap', 'Partial', 'Limited', 'Error', 'Failed'].includes(source.status)) return 'attention';
    return 'pending';
  }
  let installed = false;
  function install() {
    if (installed) return;
    installed = true;
    const base = {route, renderOverview, renderPerformance, renderFees, loadHoldings};
    const ui = {view: 'funds', saved: [], comparison: [], amc: '', quality: '', direction: 'desc', details: new Map(), performanceRequest: 0, monthly: 10000};
    try { ui.saved = codes(JSON.parse(localStorage.getItem(SAVED_KEY) || '[]')); } catch { /* Private mode or invalid preference data: start safely. */ }
    const stamp = v => v && !Number.isNaN(Date.parse(v)) ? new Date(v).toLocaleString('en-GB', {day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: 'UTC'}) + ' UTC' : 'Not recorded';
    const expenseName = fee => ({ter: 'TER', ter_observed: 'Observed TER', base_expense_ratio: 'BER', expense_ratio: 'Expense ratio'}[fee?.metric] || 'Expense');
    const source = (url, label = 'Source', extra = '') => safeURL(url) ? `<a class="source-link ${extra}" href="${E(safeURL(url))}" target="_blank" rel="noopener noreferrer">${E(label)} ${icon('external')}</a>` : '';
    const dated = (m, label = '') => m ? source(m.source, (label ? label + ' · ' : '') + D(m.as_of || m.date)) || E(D(m.as_of || m.date)) : 'Not available';
    const portfolio = f => f.portfolio || f.portfolios?.[0];
    const shortName = f => f.family.replace(/ Small[ -]?Cap Fund/i, '').replace(/ Mutual Fund/i, '');
    const fundMark = f => `<span class="fund-mark tone-${f.code % 4}" aria-hidden="true">${E(mark(f.family))}</span>`;
    const saveButton = f => `<button type="button" class="icon-button save-button ${ui.saved.includes(f.code) ? 'is-saved' : ''}" data-save="${f.code}" aria-label="${ui.saved.includes(f.code) ? 'Unsave' : 'Save'} ${E(f.family)} ${E(f.plan)} ${E(f.option)}" aria-pressed="${ui.saved.includes(f.code)}" title="${ui.saved.includes(f.code) ? 'Remove from saved funds' : 'Save for later'}">${icon('save')}</button>`;
    const compareButton = f => `<button type="button" class="secondary-button" data-compare="${f.code}" aria-pressed="${ui.comparison.includes(f.code)}">${icon('compare')} ${ui.comparison.includes(f.code) ? 'In comparison' : 'Compare'}</button>`;
    function statusStrip() {
      const last = state.status?.counts?.latest_nav_date;
      return `<div class="data-stamp">${icon('clock')}<span>Latest NAV <strong>${last ? D(last) : 'not available'}</strong></span><span class="stamp-divider"></span><a href="#/settings">Update status ${icon('arrow')}</a></div>`;
    }
    function heading(kicker, title, description, action = '') {
      return `<div class="page-heading"><div><div class="eyebrow">${E(kicker)}</div><h1>${E(title)}</h1><p>${E(description)}</p></div>${action ? `<div class="page-actions">${action}</div>` : ''}</div>`;
    }
    function syncButtons() {
      document.querySelectorAll('[data-save]').forEach(b => {
        const code = Number(b.dataset.save), f = state.funds.find(f => f.code === code) || state.fund;
        const active = ui.saved.includes(code); b.classList.toggle('is-saved', active); b.setAttribute('aria-pressed', String(active));
        if (f) b.setAttribute('aria-label', `${active ? 'Unsave' : 'Save'} ${f.family} ${f.plan} ${f.option}`);
        b.title = active ? 'Remove from saved funds' : 'Save for later';
      });
      document.querySelectorAll('[data-compare]').forEach(b => {
        const active = ui.comparison.includes(Number(b.dataset.compare));
        if (b.type === 'checkbox') b.checked = active;
        else { b.setAttribute('aria-pressed', String(active)); b.innerHTML = `${icon('compare')} ${active ? 'In comparison' : 'Compare'}`; }
      });
      document.querySelectorAll('[data-saved-count]').forEach(el => { el.textContent = ui.saved.length || ''; });
      updateDock();
    }
    function toggleSave(code) {
      if (!state.funds.some(f => f.code === code) && state.fund?.code !== code) return;
      const removing = ui.saved.includes(code);
      ui.saved = removing ? ui.saved.filter(x => x !== code) : [...ui.saved, code];
      let persisted = true;
      try { localStorage.setItem(SAVED_KEY, JSON.stringify(ui.saved)); } catch { persisted = false; }
      toast(removing ? 'Removed from saved funds.' : persisted ? 'Saved in this browser. No account needed.' : 'Saved for this visit. Browser storage is unavailable.');
      if (ui.view === 'saved') fundTable();
      syncButtons();
    }
    function toggleCompare(code) {
      if (!state.funds.some(f => f.code === code) && state.fund?.code !== code) return;
      if (ui.comparison.includes(code)) ui.comparison = ui.comparison.filter(x => x !== code);
      else if (ui.comparison.length < MAX_COMPARE) ui.comparison.push(code);
      else toast('Compare up to three plans. Remove one to add another.');
      syncButtons();
    }
    function comparisonURL() { return '#/compare/' + ui.comparison.join(','); }
    function updateDock() {
      const dock = $('#compare-dock'); if (!dock) return;
      dock.hidden = !ui.comparison.length || ui.view === 'compare';
      document.body.classList.toggle('has-compare-dock', !dock.hidden);
      if (dock.hidden) return;
      dock.innerHTML = `<div class="dock-label"><strong>${ui.comparison.length} / ${MAX_COMPARE}</strong><span>plans selected</span></div><div class="dock-funds">${ui.comparison.map(code => { const f = state.funds.find(x => x.code === code) || (state.fund?.code === code ? state.fund : null); return f ? `<button data-remove-compare="${code}" title="Remove ${E(f.family)}" aria-label="Remove ${E(f.family)} from comparison">${E(shortName(f))}${icon('close')}</button>` : ''; }).join('')}</div><button class="text-button" data-clear-comparison>Clear</button><button class="primary" data-open-comparison ${ui.comparison.length < 2 ? 'disabled' : ''}>Compare plans ${icon('arrow')}</button>`;
    }
    function resetDirectory() {
      state.search = ''; state.plan = 'Direct'; state.option = 'Growth'; state.sort = 'aum'; state.page = 1;
      ui.amc = ''; ui.quality = ''; ui.direction = 'desc'; renderDashboard();
    }
    shell = function () {
      $('#app').innerHTML = `<div class="research-layout"><header class="site-header"><div class="header-inner"><a class="brand" href="#/" aria-label="Smallcap Ledger home"><span class="brand-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M6 5v14h13M10 14V9m4 5V6m4 8V3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span>Smallcap<span class="brand-light"> Ledger</span><small>THE FUND RESEARCH DESK</small></span></a><nav class="primary-nav" aria-label="Main navigation"><a href="#/" data-nav="funds">Explore</a><a href="#/compare" data-nav="compare">Compare</a><a href="#/saved" data-nav="saved">Saved <span data-saved-count></span></a></nav><div class="header-tools"><a href="#/archive" data-nav="archive" aria-label="Data and sources">${icon('data')}<span>Data & sources</span></a><a class="icon-button" href="#/settings" data-nav="settings" aria-label="Update status" title="Update status">${icon('clock')}</a>${HOSTED ? '' : '<button id="refresh-all" aria-label="Refresh local data">↻</button>'}</div></div></header><div class="workspace"><div class="breadcrumb" id="breadcrumb">Explore / Small-cap funds</div><main class="main" id="main" tabindex="-1"></main><footer class="site-footer"><span>Smallcap Ledger <span class="footer-dot">·</span> Research, not recommendations.</span><div><a href="#/archive">Sources & methodology</a><a href="#/settings">Update status</a><span class="release-label">Research desk / 02</span></div></footer></div><nav class="mobile-nav" aria-label="Mobile navigation">${[['funds', '#/', 'explore', 'Explore'], ['compare', '#/compare', 'compare', 'Compare'], ['saved', '#/saved', 'save', 'Saved'], ['archive', '#/archive', 'data', 'Data']].map(([key, href, i, label]) => `<a href="${href}" data-nav="${key}">${icon(i)}<span>${label}</span></a>`).join('')}</nav><div id="compare-dock" class="compare-dock" aria-label="Selected comparison plans" hidden></div></div>`;
      $('#refresh-all')?.addEventListener('click', async () => { try { await post('/api/refresh', {kind: 'all'}); toast('Updates started.'); await pollStatus(); } catch (e) { toast(e.message); } });
      syncButtons();
    };
    renderDashboard = function () {
      ui.view = (location.hash || '').startsWith('#/saved') ? 'saved' : 'funds';
      const saved = ui.view === 'saved'; selectedNav(saved ? 'saved' : 'funds');
      $('#breadcrumb').textContent = saved ? 'Research desk / Saved funds' : 'Mutual funds / Equity / Small cap';
      document.title = `${saved ? 'Saved funds' : 'Explore small-cap funds'} · Smallcap Ledger`;
      const all = new Set(state.funds.map(f => f.family)).size;
      $('#main').innerHTML = `${heading(saved ? 'YOUR RESEARCH DESK' : 'EXPLORE THE CATEGORY', saved ? 'Your saved funds.' : 'Small caps. A clearer view.', saved ? 'A private shortlist, saved in this browser. Plans and options stay separate.' : 'Compare the essentials. Follow the evidence. Research at your own pace.', saved ? '' : `<div class="universe-count"><strong>${all}</strong><span>funds in focus<br>${state.funds.length} plans & options</span></div>`)}${statusStrip()}<div id="busy-area">${busy()}</div><section class="panel directory-panel no-pad"><div class="directory-toolbar"><label class="search-control"><span class="sr-only">Search funds</span>${icon('search')}<input id="search-funds" type="search" placeholder="Search funds, fund houses or AMFI codes" value="${E(state.search)}"><kbd aria-hidden="true">/</kbd></label>${saved ? '<span class="saved-explainer">All saved plans & options</span>' : `<label><span class="sr-only">Plan and option view</span><select id="view-filter" aria-label="Plan and option view">${[['direct-growth', 'Direct · Growth'], ['regular-growth', 'Regular · Growth'], ['all-growth', 'All plans · Growth'], ['idcw', 'All plans · IDCW'], ['all', 'All plans & options']].map(([v, t]) => `<option value="${v}" ${currentFundView() === v ? 'selected' : ''}>${t}</option>`).join('')}</select></label>`}<label><span class="sr-only">Fund house</span><select id="amc-filter" aria-label="Fund house"><option value="">All fund houses</option>${[...new Set(state.funds.map(f => f.amc))].sort().map(amc => `<option ${ui.amc === amc ? 'selected' : ''}>${E(amc)}</option>`).join('')}</select></label></div><div class="directory-subtoolbar"><span id="result-count" role="status"></span><div><label><span class="sr-only">Portfolio coverage</span><select id="quality-filter" aria-label="Portfolio coverage"><option value="">Any portfolio coverage</option><option value="complete" ${ui.quality === 'complete' ? 'selected' : ''}>Complete portfolio</option><option value="partial" ${ui.quality === 'partial' ? 'selected' : ''}>Partial portfolio</option><option value="missing" ${ui.quality === 'missing' ? 'selected' : ''}>Portfolio not available</option></select></label><label class="mobile-sort"><span class="sr-only">Sort funds</span><select id="sort-funds" aria-label="Sort funds">${[['aum', 'AUM'], ['5', '5Y CAGR'], ['3', '3Y CAGR'], ['1', '1Y return'], ['ter', 'Expense'], ['family', 'Fund name'], ['nav','NAV']].map(([v,t]) => `<option value="${v}" ${state.sort === v ? 'selected' : ''}>Sort: ${t}</option>`).join('')}</select></label><button class="text-button" id="reset-directory">Reset</button></div></div><div id="fund-table"></div></section><div class="directory-footnote">${icon('shield')}<p>Reporting dates and sources travel with each figure. Returns are not forecasts. ${saved ? 'Saved funds are not synced across devices.' : 'Select two or three plans to compare, or bookmark a fund for later.'}</p></div>`;
      $('#search-funds').addEventListener('input', e => { state.search = e.target.value; state.page = 1; fundTable(); });
      $('#view-filter')?.addEventListener('change', e => { applyFundView(e.target.value); state.page = 1; fundTable(); });
      $('#amc-filter').addEventListener('change', e => { ui.amc = e.target.value; state.page = 1; fundTable(); });
      $('#quality-filter').addEventListener('change', e => { ui.quality = e.target.value; state.page = 1; fundTable(); });
      $('#sort-funds').addEventListener('change', e => { state.sort = e.target.value; ui.direction = ['family', 'ter'].includes(state.sort) ? 'asc' : 'desc'; fundTable(); });
      $('#reset-directory').addEventListener('click', resetDirectory);
      fundTable(); syncButtons();
    };
    fundTable = function () {
      if (!$('#fund-table')) return;
      const q = state.search.trim().toLowerCase(), saved = ui.view === 'saved';
      let rows = state.funds.filter(f => (!saved || ui.saved.includes(f.code)) && (saved || ((state.plan === 'All' || f.plan === state.plan) && (state.option === 'All' || f.option === state.option))) && (!q || `${f.name} ${f.family} ${f.amc} ${f.code}`.toLowerCase().includes(q)) && (!ui.amc || f.amc === ui.amc) && (!ui.quality || (ui.quality === 'missing' ? !portfolio(f) : ui.quality === 'complete' ? !!portfolio(f)?.complete : !!portfolio(f) && !portfolio(f).complete)));
      rows = sortFunds(rows, state.sort, ui.direction);
      const pageCount = Math.max(1, Math.ceil(rows.length / 25)); state.page = Math.min(Math.max(1, state.page), pageCount);
      const shown = rows.slice((state.page - 1) * 25, state.page * 25);
      $('#result-count').textContent = `${new Set(rows.map(f => f.family)).size} funds · ${rows.length} plans & options`;
      const header = (key, text) => `<th scope="col" ${state.sort === key ? `aria-sort="${ui.direction === 'asc' ? 'ascending' : 'descending'}"` : ''} class="${key === 'family' ? '' : 'right'}"><button class="sort-heading" data-sort="${key}">${E(text)} <span aria-hidden="true">${state.sort === key ? ui.direction === 'asc' ? '↑' : '↓' : '↕'}</span></button></th>`;
      $('#fund-table').innerHTML = !rows.length ? empty(saved && !ui.saved.length ? 'Your research starts here.' : 'No funds match these filters.', saved && !ui.saved.length ? 'Save a fund using its bookmark button. Your shortlist stays in this browser.' : 'Try a broader search or reset the filters.', saved && !ui.saved.length ? '<a class="primary-link" href="#/">Explore funds →</a>' : '<button id="empty-reset">Reset filters</button>') : `<div class="table-wrap directory-table-wrap" tabindex="0" role="region" aria-label="Fund comparison table"><table class="fund-table directory-table"><caption class="sr-only">Fund research directory. Column heading buttons sort. Missing values always appear last.</caption><thead><tr><th scope="col" class="select-cell"><span class="sr-only">Select for comparison</span>${icon('compare')}</th>${header('family', 'Fund / plan')}${header('nav', 'NAV')}${header('aum', 'AUM · ₹ Cr')}${header('ter', 'Expense')}${header('1', '1Y return')}${header('3', '3Y CAGR')}${header('5', '5Y CAGR')}<th scope="col" class="save-cell"><span class="sr-only">Save fund</span></th></tr></thead><tbody>${shown.map(f => { const fee = feeFor(f); return `<tr data-fund-href="/fund/${f.code}" class="fund-row"><td class="select-cell"><label class="compare-check"><input type="checkbox" data-compare="${f.code}" ${ui.comparison.includes(f.code) ? 'checked' : ''} aria-label="Compare ${E(f.family)} ${E(f.plan)} ${E(f.option)}"></label></td><td class="fund-name-cell"><div class="fund-name">${fundMark(f)}<div><a class="fund-title" href="#/fund/${f.code}">${E(f.family)}</a><div class="fund-detail">${E(f.plan)} <span>·</span> ${E(f.option_label || f.option)}</div></div></div></td><td data-label="NAV" class="right"><strong>${f.nav ? '₹' + N(f.nav.value, 4) : '—'}</strong><div class="fund-detail">${dated(f.nav)}</div></td><td data-label="AUM · ₹ Cr" class="right"><strong>${N(f.metrics?.aum?.value, 0)}</strong><div class="fund-detail">${dated(f.metrics?.aum)}</div></td><td data-label="Expense" class="right"><strong>${fee ? N(fee.value) + '%' : '—'}</strong><div class="fund-detail">${fee ? dated(fee, expenseName(fee)) : 'Not available'}</div></td>${['1', '3', '5'].map(year => `<td data-label="${year === '1' ? '1Y return' : year + 'Y CAGR'}" class="right return-cell ${cls(f.returns?.[year])}">${P(f.returns?.[year])}</td>`).join('')}<td class="save-cell">${saveButton(f)}</td></tr>`; }).join('')}</tbody></table></div><div class="pagination"><span>${(state.page - 1) * 25 + 1}–${Math.min(state.page * 25, rows.length)} of ${rows.length} plans & options</span><div><button id="prev" aria-label="Previous page" ${state.page === 1 ? 'disabled' : ''}>${icon('back')}</button><span>Page ${state.page} of ${pageCount}</span><button id="next" aria-label="Next page" ${state.page === pageCount ? 'disabled' : ''}>${icon('arrow')}</button></div></div>`;
      $('#empty-reset')?.addEventListener('click', resetDirectory);
      document.querySelectorAll('[data-sort]').forEach(b => b.addEventListener('click', () => {
        if (state.sort === b.dataset.sort) ui.direction = ui.direction === 'asc' ? 'desc' : 'asc';
        else { state.sort = b.dataset.sort; ui.direction = ['family', 'ter'].includes(state.sort) ? 'asc' : 'desc'; }
        state.page = 1; fundTable(); $('#sort-funds').value = state.sort; $(`[data-sort="${state.sort}"]`)?.focus({preventScroll: true});
      }));
      $('#prev')?.addEventListener('click', () => { state.page--; fundTable(); $('#next')?.focus({preventScroll: true}); });
      $('#next')?.addEventListener('click', () => { state.page++; fundTable(); $('#prev')?.focus({preventScroll: true}); });
      bindFundRows(); updateDock();
    };
    bindFundRows = function () {
      document.querySelectorAll('[data-fund-href]').forEach(row => row.addEventListener('click', e => {
        if (e.target.closest('a,button,input,select,label,summary') || e.ctrlKey || e.metaKey || e.shiftKey || String(window.getSelection())) return;
        location.hash = row.dataset.fundHref;
      }));
    };
    async function renderCompare() {
      const raw = (location.hash.split('/')[2] || '').split(',').filter(Boolean);
      const requested = raw.length ? codes(raw).slice(0, MAX_COMPARE) : ui.comparison;
      const available = requested.filter(code => state.funds.some(f => f.code === code));
      ui.comparison = available;
      const funds = available.map(code => state.funds.find(f => f.code === code));
      $('#breadcrumb').textContent = 'Research desk / Compare plans'; document.title = 'Compare funds · Smallcap Ledger'; selectedNav('compare');
      $('#main').innerHTML = `${heading('SIDE BY SIDE', 'Compare with context.', 'Up to three plans. Their own reporting dates. No opaque scores or rankings.', funds.length > 1 ? '<button class="secondary-button" id="share-comparison">Copy comparison link</button>' : '')}${funds.length < 2 ? `<section class="panel">${empty('Choose at least two plans.', 'Use the comparison checkboxes in Explore or your saved shortlist. Direct, Regular and IDCW remain distinct plans/options.', '<a href="#/" class="primary-link">Choose funds →</a>')}</section>` : `${funds.some(f => f.option !== 'Growth') ? '<div class="callout warning">This comparison includes a non-Growth option. NAV alone is not total return; unsupported return cells remain unavailable.</div>' : ''}${new Set(funds.map(f => f.plan)).size > 1 ? '<p class="comparison-note">You are comparing different plan types. Check the plan labels and expenses before interpreting returns.</p>' : ''}<div class="table-wrap compare-table-wrap" tabindex="0" role="region" aria-label="Side-by-side fund comparison"><table class="compare-table"><caption class="sr-only">Latest retained values for each selected plan; reporting dates may differ.</caption><thead><tr><th scope="col">The essentials<span>Figures are not necessarily<br>from the same reporting date.</span></th>${funds.map(f => `<th scope="col">${fundMark(f)}<a class="compare-name" href="#/fund/${f.code}">${E(f.family)}</a><span>${E(f.plan)} · ${E(f.option_label || f.option)}</span><button class="text-button" data-remove-compare="${f.code}">Remove</button></th>`).join('')}</tr></thead><tbody>${[
        ['NAV', f => `<strong>${f.nav ? '₹' + N(f.nav.value, 4) : '—'}</strong><small>${dated(f.nav)}</small>`],
        ['AUM · ₹ crore', f => `<strong>${N(f.metrics?.aum?.value, 0)}</strong><small>${dated(f.metrics?.aum)}</small>`],
        ['Annual expense', f => { const fee = feeFor(f); return `<strong>${fee ? N(fee.value) + '%' : '—'}</strong><small>${fee ? dated(fee, expenseName(fee)) : 'Not available'}</small>`; }],
        ...['1', '3', '5'].map(year => [year === '1' ? '1-year return' : year + '-year CAGR', f => `<strong class="${cls(f.returns?.[year])}">${P(f.returns?.[year])}</strong><small>${f.returns?.[year] != null && f.nav ? 'Through ' + D(f.nav.date) : 'Eligible history unavailable'}</small>`]),
        ['Reported benchmark', f => `<span>${E(f.metrics?.benchmark?.value || 'Not verified')}</span><small>${dated(f.metrics?.benchmark)}</small>`],
        ['Latest portfolio', f => { const p = portfolio(f); return p ? `<span>${D(p.as_of)}</span><small class="${p.complete ? '' : 'warning-text'}">${p.complete ? 'Complete' : 'Partial'} disclosure</small>` : 'Not available'; }],
        ['Explore further', f => `<div class="compare-links"><a href="#/fund/${f.code}/performance">Performance →</a><a href="#/fund/${f.code}/portfolio">Portfolio →</a><a href="#/fund/${f.code}/fees">Fees & sources →</a></div>`]
      ].map(([label, cell]) => `<tr><th scope="row">${label}</th>${funds.map(f => `<td>${cell(f)}</td>`).join('')}</tr>`).join('')}</tbody></table></div><p class="footer-note">AUM is fund-wide: do not add it across plans of the same fund. Each plan uses its own retained NAV history; missing values are not zero. Comparison links contain scheme codes, not your saved shortlist.</p>`}${raw.length && (raw.length !== requested.length || available.length !== requested.length || raw.length > MAX_COMPARE) ? '<p class="callout warning">Some requested plans could not be included. Only valid, available plans are shown, up to a maximum of three.</p>' : ''}`;
      $('#share-comparison')?.addEventListener('click', async () => {
        const url = new URL(location.href); url.hash = comparisonURL();
        try { await navigator.clipboard.writeText(url.href); toast('Comparison link copied.'); }
        catch { let field = $('#comparison-link'); if (!field) { field = document.createElement('input'); field.id = 'comparison-link'; field.readOnly = true; field.setAttribute('aria-label', 'Comparison link to copy'); $('#main').append(field); } field.value = url.href; field.focus(); field.select(); toast('Copy the selected comparison link.'); }
      });
      updateDock();
    }
    fundHeader = function () {
      const f = state.fund;
      return `<section class="fund-hero"><div class="fund-hero-main"><a class="fund-back" href="#/">${icon('back')} All funds</a><div class="fund-identity">${fundMark(f)}<div><div class="eyebrow">${E(f.amc)}</div><h1>${E(f.family)}</h1><p class="fund-subtitle">Small-cap equity <span>·</span> ${E(f.plan)} <span>·</span> ${E(f.option_label || f.option)} <span>·</span> AMFI ${f.code}</p></div></div></div><div class="fund-actions"><div>${compareButton(f)}${saveButton(f)}</div><label><span>Plan & option</span><select id="plan-picker" aria-label="Plan and option">${f.plans.map(p => `<option value="${p.code}" ${p.code === f.code ? 'selected' : ''}>${E(p.plan)} · ${E(p.option_label || p.option)}</option>`).join('')}</select></label></div></section><nav class="tabs fund-tabs" aria-label="Fund sections">${[['overview','Overview'],['performance','Performance'],['portfolio','Portfolio'],['fees','Fees & AUM'],['news','AMC documents']].map(([v,t]) => `<a ${state.tab === v ? 'class="active" aria-current="page"' : ''} href="#/fund/${f.code}/${v}">${t}</a>`).join('')}</nav><div id="busy-area">${busy()}</div><div id="fund-content"></div>`;
    };
    renderOverview = function () {
      base.renderOverview(); const f = state.fund, p = state.perf;
      decorateSummary(f, p);
      const title = $('.comparison-overview .panel-head > div');
      if (title) title.insertAdjacentHTML('afterbegin', '<div class="eyebrow">THE LONGER VIEW</div>');
      const dl = $('.minimal-facts .facts');
      if (dl) {
        const keys = ['managers', 'benchmark', 'risk', 'minimum_sip', 'fund_launch'];
        keys.forEach((key, i) => { const dd = dl.children[i]?.querySelector('dd'), m = f.metrics[key]; if (dd && m?.source) dd.insertAdjacentHTML('beforeend', `<small>${dated(m)}</small>`); });
        const pp = portfolio(f), last = dl.lastElementChild?.querySelector('dd');
        if (pp && last) last.innerHTML = `<a href="#/fund/${f.code}/portfolio">${D(pp.as_of)} →</a><small>${pp.complete ? 'Complete' : 'Partial'} disclosure</small>`;
      }
      bindDisclosures();
    };
    function decorateSummary(f, p = null) {
      const cells = document.querySelectorAll('#fund-content .summary-panel > .summary-strip > div');
      const ms = p ? [f.nav, f.metrics.aum, feeFor(f)] : [f.metrics.aum, feeFor(f), f.metrics.exit_load];
      ms.forEach((m, i) => {
        const cell = cells[i]; if (!cell) return;
        if (i === (p ? 2 : 1)) $('span', cell).textContent = expenseName(m);
        let small = $('small', cell); if (!small) { small = document.createElement('small'); cell.append(small); }
        small.innerHTML = m ? dated(m) : p && i === 0 && p.latest_nav ? E(D(p.latest_nav[0])) : 'Not available';
      });
      if (p) ['1Y','3Y','5Y'].forEach((key, i) => { const cell = cells[i + 3], r = p.stats?.returns?.[key]; if (cell) cell.insertAdjacentHTML('beforeend', `<small>${r?.end ? 'Through ' + D(r.end) : 'Eligible history unavailable'}</small>`); });
    }
    function bindDisclosures() {
      document.querySelectorAll('#fund-content details').forEach((d, i) => {
        const key = `${state.fund?.code}:${state.tab}:${i}`;
        if (ui.details.has(key)) d.open = ui.details.get(key);
        d.addEventListener('toggle', () => { if (d.isConnected) ui.details.set(key, d.open); });
      });
    }
    renderPerformance = function () { base.renderPerformance(); bindDisclosures(); };
    refreshPerformance = async function () {
      const token = state.token, request = ++ui.performanceRequest;
      document.querySelectorAll('#fund-content details').forEach((d, i) => ui.details.set(`${state.fund?.code}:${state.tab}:${i}`, d.open));
      if (state.range === 'Custom' && state.customStart && state.customEnd && state.customStart > state.customEnd) { toast('The start date must come before the end date.'); return; }
      if (state.monthly != null && (!Number.isFinite(state.monthly) || state.monthly < 100 || state.monthly > 100000000)) { state.monthly = ui.monthly; toast('Enter a monthly SIP between ₹100 and ₹10 crore.'); return; }
      ui.monthly = state.monthly || 10000;
      $('#fund-content')?.setAttribute('aria-busy', 'true');
      try { const p = await getPerformance(); if (token !== state.token || request !== ui.performanceRequest) return; state.perf = p; renderPerformance(); }
      catch (e) { if (token === state.token && request === ui.performanceRequest) toast(e.message); }
      finally { if (token === state.token && request === ui.performanceRequest) $('#fund-content')?.setAttribute('aria-busy', 'false'); }
    };
    loadHoldings = async function (id) {
      const token = state.token; await base.loadHoldings(id); if (token !== state.token || state.tab !== 'portfolio' || ($('#snapshot-picker') && String($('#snapshot-picker').value) !== String(id))) return;
      const table = $('.holdings-table'); if (!table || $('#search-holdings')) return;
      const bar = document.createElement('div'); bar.className = 'holdings-search';
      bar.innerHTML = `<label class="search-control">${icon('search')}<input type="search" id="search-holdings" aria-label="Search holdings, ISIN or sector" placeholder="Search holdings, ISIN or sector"></label><span id="holding-result" role="status"></span>`;
      table.closest('.table-wrap').before(bar);
      $('#search-holdings').addEventListener('input', e => { const q = e.target.value.trim().toLowerCase(); let visible = 0; table.querySelectorAll('tbody tr').forEach(row => { row.hidden = !row.textContent.toLowerCase().includes(q); if (!row.hidden) visible++; }); $('#holding-result').textContent = visible + ' holdings shown'; });
      bindDisclosures();
    };
    renderFees = function () { base.renderFees(); decorateSummary(state.fund); bindDisclosures(); };
    renderNews = function (docs) {
      docs = docs.filter(d => d.kind !== 'news');
      $('#fund-content').innerHTML = `<section class="panel documents-panel"><div class="panel-head"><div><div class="eyebrow">STRAIGHT FROM THE FUND HOUSE</div><h2>AMC documents</h2><p class="small muted">Factsheets, portfolios, disclosures and commentary. No third-party news.</p></div><span id="document-count" class="small muted" role="status"></span></div><div class="document-toolbar"><label class="search-control">${icon('search')}<input id="document-search" type="search" aria-label="Search AMC documents" placeholder="Search titles, types or fund-house commentary" value="${E(state.newsSearch)}"></label><select id="document-filter" aria-label="Document type">${['All','Factsheets','Portfolio','Market views','Disclosures','Source pages'].map(x => `<option ${x === state.newsFilter ? 'selected' : ''}>${x}</option>`).join('')}</select></div><div id="doc-list"></div></section><p class="footer-note">“First found” is a discovery date, not a publication date. The original link may change over time; archived copies and source evidence remain separately identified.</p>`;
      const filters = {'Factsheets':['factsheet'], 'Portfolio':['portfolio'], 'Market views':['market view'], 'Disclosures':['disclosure','scheme document'], 'Source pages':['source page']};
      function list() {
        const q = state.newsSearch.trim().toLowerCase();
        const rows = docs.filter(d => (state.newsFilter === 'All' ? d.kind !== 'source page' : filters[state.newsFilter]?.includes(d.kind)) && (!q || `${d.title} ${d.kind} ${d.scope} ${d.origin}`.toLowerCase().includes(q)));
        $('#document-count').textContent = rows.length + ' documents';
        $('#doc-list').innerHTML = rows.map(d => {
          const versions = d.versions || [], latest = versions[0], saved = number(d.saved_version_count) ?? versions.length;
          return `<article class="document-row"><div class="document-type" aria-hidden="true">${d.kind === 'portfolio' ? icon('data') : icon('save')}</div><div class="document-body"><div class="document-meta">${E(d.kind)} <span>·</span> ${d.scope === 'AMC' ? 'Fund-house-wide' : 'Fund-specific'}</div><h3>${source(d.url, d.title, 'document-title')}</h3><div class="document-date">${d.published_at ? 'Published ' + D(d.published_at) : 'Publication date not supplied · first found ' + D(d.first_seen)}</div><div class="doc-actions">${source(d.url, 'Open original')}${latest ? `<a href="/api/archive/${E(latest.hash)}">Saved copy ↓</a>` : saved ? '<span>Archived evidence retained</span>' : '<span class="muted">Original link only · no saved copy</span>'}${saved > versions.length && HOSTED ? projectLink('/releases/tag/tracker-history', 'More archived versions') : ''}${versions.length > 1 ? `<details><summary>${versions.length} saved versions</summary><div class="version-list">${versions.map(v => `<a href="/api/archive/${E(v.hash)}">${stamp(v.observed_at)} · ${bytesLabel(v.bytes)}</a>`).join('')}</div></details>` : ''}</div></div></article>`;
        }).join('') || empty('No documents in this view.', 'Try another document type or a different search.');
      }
      $('#document-filter').addEventListener('change', e => { state.newsFilter = e.target.value; list(); });
      $('#document-search').addEventListener('input', e => { state.newsSearch = e.target.value; list(); }); list();
    };
    renderHostedArchive = function () {
      const c = state.status?.counts || {}, all = new Set(state.funds.map(f => f.family)).size;
      const coverage = [['NAV history', c.nav_points, 'dated observations'], ['AUM', c.aum_funds, `of ${all} fund families`], ['Expenses', c.fee_funds, `of ${all} fund families`], ['Portfolios', c.portfolios, 'retained snapshots']];
      $('#breadcrumb').textContent = 'Research desk / Data & sources'; document.title = 'Data & sources · Smallcap Ledger';
      $('#main').innerHTML = `${heading('EVIDENCE, NOT ASSUMPTIONS', 'Know what is behind the numbers.', 'Source coverage, retained evidence and reporting dates in one place.', projectLink('/releases/tag/tracker-history', 'Open historical archive'))}<section class="panel coverage-summary">${coverage.map(([label, value, note]) => `<div><span>${label}</span><strong>${N(value, 0)}</strong><small>${note}</small></div>`).join('')}</section><div class="two-columns equal"><section class="panel"><div class="eyebrow">FRESHNESS</div><h2>Different numbers. Different dates.</h2><dl class="facts"><div class="fact"><dt>Latest NAV</dt><dd>${D(c.latest_nav_date)}</dd></div><div class="fact"><dt>Snapshot built</dt><dd>${stamp(state.status?.server_time)}</dd></div><div class="fact"><dt>Source checks</dt><dd><a href="#/settings">View individual check results →</a></dd></div></dl><p class="footer-note">A website build is not a new fund report. AUM, expenses and portfolios keep their own reporting dates.</p></section><section class="panel"><div class="eyebrow">RETENTION</div><h2>Storage, clearly separated.</h2><dl class="facts"><div class="fact"><dt>Database</dt><dd>${c.database_bytes == null ? 'Not available' : bytesLabel(c.database_bytes)}</dd></div><div class="fact"><dt>Source evidence</dt><dd>${c.archive_bytes == null ? 'Not available' : bytesLabel(c.archive_bytes)}</dd></div><div class="fact"><dt>Total retained</dt><dd>${c.total_storage_bytes == null ? 'Not available' : bytesLabel(c.total_storage_bytes)}</dd></div></dl><p class="footer-note">Uncompressed logical storage, not the size of the website or daily download. Original evidence and database checkpoints are separate.</p></section></div>${benchmarkCoverage()}<details class="panel methodology" open><summary>How to read this website</summary><div class="method-grid"><div><h3>Returns</h3><p>Growth returns use retained NAVs after fund expenses. Multi-year periods are annualized. Tax and exit loads are excluded. Past returns are not forecasts.</p></div><div><h3>Benchmarks</h3><p>The reported benchmark comes first. Missing reported TRI history stays unavailable; an alternate comparison must be selected explicitly.</p></div><div><h3>Plans & options</h3><p>Direct and Regular plans stay separate. IDCW needs complete distribution history for total-return analysis. Fund-wide AUM must not be added across plans.</p></div><div><h3>Evidence & gaps</h3><p>Missing is not zero. Partial portfolios are labelled. Document publication dates and discovery dates are distinct. Sources remain attached to figures.</p></div></div></details><details class="panel"><summary>Recent collection activity</summary><div id="logs" class="logs section-space">${logs()}</div></details>`;
    };
    renderHostedSettings = function () {
      const sources = state.status?.sources || [];
      const counts = sources.reduce((sum, s) => { sum[sourceState(s)]++; return sum; }, {checked: 0, attention: 0, pending: 0, inactive: 0});
      $('#breadcrumb').textContent = 'Data & sources / Update status'; document.title = 'Update status · Smallcap Ledger';
      $('#main').innerHTML = `${heading('COLLECTION STATUS', 'Freshness you can inspect.', 'A source check is not a guarantee that every field was extracted.', projectLink('/actions/workflows/daily.yml', 'View workflow runs'))}<div class="status-banner">${icon('clock')}<div><strong>Scheduled collection · ${E(state.status?.hosting?.schedule || 'See workflow schedule')}</strong><span>Snapshot built ${stamp(state.status?.server_time)}. Scheduled starts may be delayed.</span></div></div><section class="panel no-pad source-panel"><div class="source-summary"><span><b>${counts.checked}</b> checked</span><span class="warning-text"><b>${counts.attention}</b> need attention</span><span><b>${counts.pending}</b> pending / unknown</span><span><b>${counts.inactive}</b> inactive</span></div><div class="directory-toolbar"><label class="search-control">${icon('search')}<input type="search" id="source-search" aria-label="Search sources" placeholder="Search fund house, source or check result"></label><select id="source-filter" aria-label="Filter source status"><option value="all">All sources</option><option value="attention">Needs attention</option><option value="checked">Checked</option><option value="pending">Pending / unknown</option><option value="inactive">Inactive</option></select></div><div id="source-results" role="status" class="source-result-count"></div><div id="source-rows"></div></section>`;
      function list() {
        const q = $('#source-search').value.trim().toLowerCase(), filter = $('#source-filter').value;
        const rows = sources.filter(s => (filter === 'all' || sourceState(s) === filter) && (!q || `${s.amc_match} ${s.label} ${s.status} ${s.detail}`.toLowerCase().includes(q)));
        $('#source-results').textContent = rows.length + ' source checks';
        $('#source-rows').innerHTML = rows.map(s => `<details class="source-row"><summary><span><strong>${E(s.amc_match)}</strong><small>${E(s.label)}</small></span><span class="source-check-time">${stamp(s.last_checked)}</span><span class="badge ${sourceState(s) === 'checked' ? 'green' : sourceState(s) === 'attention' ? 'amber' : ''}">${E(s.status || 'Pending')}</span></summary><div class="source-row-detail"><p>${E(s.detail || 'No check detail recorded.')}</p><small>Last checked ${stamp(s.last_checked)}</small><p>${source(s.url, 'Open source page')}</p></div></details>`).join('') || empty('No sources match.', 'Try another search or status filter.');
      }
      $('#source-search').addEventListener('input', list); $('#source-filter').addEventListener('change', list); list();
    };
    route = async function () {
      const page = (location.hash || '#/').split('/')[1], previousView = ui.view;
      ui.view = page === 'saved' ? 'saved' : page === 'compare' ? 'compare' : page === 'fund' ? 'fund' : page || 'funds';
      if (!['saved', 'compare'].includes(page)) { await base.route(); syncButtons(); return; }
      const token = ++state.token;
      $('#main').setAttribute('aria-busy', 'true'); $('#main').innerHTML = '<div class="loading" role="status"><span class="spinner" aria-hidden="true"></span>Opening your research desk…</div>';
      try {
        await loadFunds(); if (token !== state.token) return;
        if (page === 'saved') { if (previousView !== 'saved') { state.search = ''; ui.amc = ''; ui.quality = ''; state.page = 1; } renderDashboard(); }
        else await renderCompare();
      }
      catch (e) { if (token === state.token) $('#main').innerHTML = empty('This view could not be opened.', e.message, '<a href="#/">Return to Explore →</a>'); }
      finally { if (token === state.token) { $('#main').setAttribute('aria-busy', 'false'); $('#main').focus({preventScroll: true}); syncButtons(); } }
    };
    // Replace the original hash listener rather than registering two routers.
    window.removeEventListener('hashchange', base.route);
    window.addEventListener('hashchange', route);
    document.addEventListener('click', e => {
      const button = e.target.closest('[data-save],[data-compare],[data-remove-compare],[data-open-comparison],[data-clear-comparison]'); if (!button) return;
      if (button.hasAttribute('data-save')) toggleSave(Number(button.dataset.save));
      else if (button.hasAttribute('data-compare')) toggleCompare(Number(button.dataset.compare));
      else if (button.hasAttribute('data-remove-compare')) { ui.comparison = ui.comparison.filter(code => code !== Number(button.dataset.removeCompare)); if (ui.view === 'compare') location.hash = comparisonURL(); syncButtons(); }
      else if (button.hasAttribute('data-open-comparison') && ui.comparison.length >= 2) location.hash = comparisonURL();
      else if (button.hasAttribute('data-clear-comparison')) { ui.comparison = []; syncButtons(); }
    });
    document.querySelector('.skip-link')?.addEventListener('click', e => { e.preventDefault(); $('#main')?.focus(); });
    document.addEventListener('keydown', e => { if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey && !e.target.closest('input,select,textarea,[contenteditable="true"]') && $('#search-funds')) { e.preventDefault(); $('#search-funds').focus(); } });
    window.addEventListener('storage', e => { if (e.key === SAVED_KEY) { try { ui.saved = codes(JSON.parse(e.newValue || '[]')); } catch { ui.saved = []; } if (ui.view === 'saved') fundTable(); syncButtons(); } });
  }
  window.LedgerResearch = {install, codes, number, safeURL, sortFunds, sourceState, version: '2026-09-25-desk-2'};
  if (typeof document !== 'undefined' && typeof window.route === 'function') {
    install();
    shell();
    route();
  }
})();
