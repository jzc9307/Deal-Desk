const byId = id => document.getElementById(id);
const money = value => new Intl.NumberFormat('en-MY', {style: 'currency', currency: 'MYR'}).format(value);
let busy = false;
let inputFormat = 'json';
let drafts = {json: '', csv: ''};
let board = null;
let selectedGroup = null;

function message(value, error = false) {
  byId('status').textContent = value;
  byId('status').classList.toggle('error', error);
}

// Imported text is never inserted as HTML.
function text(tag, value, parent, className) {
  const node = document.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  parent.appendChild(node);
  return node;
}

function showCosts(settings) {
  byId('cost-assumptions').textContent = `Default shipping ${money(settings.default_shipping_myr)}; resale fee ${(settings.resale_fee_rate * 100).toFixed(1)}% of the scenario. Imported shipping overrides the default.`;
}

function setFormat(format) {
  drafts[inputFormat] = byId('records').value;
  inputFormat = format;
  byId('records').value = drafts[format];
  byId('csv-upload').hidden = format !== 'csv';
  document.querySelectorAll('[data-format]').forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.format === format));
  });
}
document.querySelectorAll('[data-format]').forEach(button => {
  button.addEventListener('click', () => setFormat(button.dataset.format));
});

async function sample() {
  try {
    const reply = await fetch('/api/sample');
    if (!reply.ok) throw Error('Example unavailable');
    const data = await reply.json();
    showCosts(data.cost_assumptions);
    drafts = {json: JSON.stringify(data.listings, null, 2), csv: data.csv};
    byId('records').value = drafts[inputFormat];
    byId('csv-file').value = '';
    message(`Loaded ${data.listings.length} fictional examples. Build the board to compare them.`);
  } catch (_) {
    message('Could not load the local example.', true);
  }
}
byId('sample').addEventListener('click', sample);

byId('csv-file').addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 200000) {
    message('Choose a UTF-8 CSV file no larger than 200 KB.', true);
    return;
  }
  try {
    const content = await file.text();
    if (content.length > 150000) throw Error('CSV text must be at most 150,000 characters.');
    setFormat('csv');
    drafts.csv = content;
    byId('records').value = content;
    message(`Loaded ${file.name}. Review the fields, then build the board.`);
  } catch (error) {
    message(error.message || 'Could not read the file.', true);
  }
});

byId('valuation').addEventListener('change', () => {
  const manual = byId('valuation').value === 'manual';
  byId('manual-field').hidden = !manual;
  byId('resale').required = manual;
  byId('estimate-hint').textContent = manual
    ? 'This one estimate applies to every product. Filter to one product first if their values differ.'
    : "A scenario based on the imported group's median. It is not a completed-sale valuation.";
});

function renderGroups() {
  const area = byId('groups');
  area.replaceChildren();
  byId('clear-group').hidden = !selectedGroup;
  for (const group of board.groups) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'group-card';
    button.dataset.groupId = group.id;
    button.setAttribute('aria-pressed', String(selectedGroup === group.id));
    button.setAttribute('aria-label', `View group ${group.name}, ${group.variant}`);
    text('span', group.variant, button, 'group-variant');
    text('h4', group.name, button);
    text('span', 'Estimated fair-price band', button, 'band-label');
    const band = group.asking_price_band;
    text('strong', `${money(band.low)}–${money(band.high)}`, button, 'band-value');
    text('span', `Median ${money(band.estimate)} · ${group.sample_count} asks · ${group.visible_count} ranked`, button, 'band-meta');
    text('span', group.sample_count === 1 ? 'Single ask ±10% · illustrative only'
      : group.sample_count >= 4 ? 'Middle 50% of imported asks' : 'Observed imported asking-price range',
      button, 'band-method');
    if (group.warning) text('span', group.warning, button, 'group-warning');
    button.addEventListener('click', () => {
      selectedGroup = selectedGroup === group.id ? null : group.id;
      renderGroups();
      renderOffers();
      [...byId('groups').querySelectorAll('button')].find(item => item.dataset.groupId === group.id)?.focus();
    });
    area.appendChild(button);
  }
  if (!board.groups.length) {
    const empty = text('div', 'No comparable product groups. Check the set-aside rows or broaden the query.', area, 'board-empty');
    empty.setAttribute('role', 'status');
  }
}

function renderOffers() {
  const items = board.offers.filter(item => !selectedGroup || item.group_id === selectedGroup);
  const order = byId('sort').value;
  items.sort((left, right) => order === 'price'
    ? left.price - right.price || left.rank - right.rank
    : order === 'margin' ? right.margin_pct - left.margin_pct || left.rank - right.rank
      : right.profit - left.profit || left.rank - right.rank);
  const results = byId('results');
  results.replaceChildren();
  byId('ranking-count').textContent = `${items.length} of ${board.offers.length} ranked rows · estimates only`;
  items.forEach((item, index) => {
    const row = document.createElement('article');
    row.className = 'opportunity';
    const heading = document.createElement('div');
    heading.className = 'opportunity-heading';
    row.appendChild(heading);
    text('span', String(index + 1).padStart(2, '0'), heading, 'rank-number');
    const identity = document.createElement('div');
    heading.appendChild(identity);
    const link = text('a', item.title, identity);
    link.href = item.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    text('span', `${item.marketplace} · ${item.condition || 'Condition unstated'} · ${item.product_group}`, identity, 'offer-meta');
    text('span', item.review_flags.length ? 'Review condition' : 'Check details', heading,
      item.review_flags.length ? 'review-badge flagged' : 'review-badge');

    const amounts = document.createElement('div');
    amounts.className = 'offer-amounts';
    row.appendChild(amounts);
    for (const [label, value, className] of [
      ['ASKING', money(item.price), ''],
      [item.landed_cost_verified ? 'EST. TOTAL' : 'MIN. TOTAL', money(item.total_cost), ''],
      ['RESALE SCENARIO', money(item.resale_estimate), ''],
      ['EST. PROFIT', (item.profit > 0 ? '+' : '') + money(item.profit), item.profit > 0 ? 'positive' : 'negative'],
    ]) {
      const cell = document.createElement('div');
      amounts.appendChild(cell);
      text('span', label, cell);
      text('strong', value, cell, className);
    }
    const notes = document.createElement('div');
    notes.className = 'offer-notes';
    row.appendChild(notes);
    text('span', `${item.margin_pct}% return on cost · ${item.estimate_basis === 'manual' ? 'manual estimate' : 'group asking median'}`, notes);
    text('span', 'Imported · unverified', notes);
    if (item.review_flags.length) {
      const flags = document.createElement('ul');
      flags.className = 'review-flags';
      item.review_flags.forEach(flag => text('li', flag, flags));
      row.appendChild(flags);
    }
    results.appendChild(row);
  });
  if (!items.length) {
    text('div', 'No rows in this view. Clear the product selection or raise the asking-price ceiling.', results, 'board-empty');
  }
}
byId('sort').addEventListener('change', () => { if (board) renderOffers(); });
byId('clear-group').addEventListener('click', () => {
  selectedGroup = null;
  renderGroups();
  renderOffers();
});

function renderBoard(data) {
  board = data;
  selectedGroup = null;
  showCosts(data.cost_assumptions);
  for (const key of ['submitted', 'retained', 'rejected']) byId(key).textContent = data[key];
  byId('raw').textContent = JSON.stringify(data, null, 2);
  byId('rejections').replaceChildren();
  byId('rejections-section').hidden = !data.discarded.length;
  byId('rejections-count').textContent = `(${data.discarded.length})`;
  for (const item of data.discarded) {
    const row = document.createElement('article');
    row.className = 'rejection-row';
    text('strong', item.title, row);
    text('p', item.reason, row);
    byId('rejections').appendChild(row);
  }
  renderGroups();
  renderOffers();
}

byId('compareForm').addEventListener('submit', async event => {
  event.preventDefault();
  if (busy) return;
  let payload = {
    query: byId('query').value.trim(),
    max_price: byId('budget').value ? Number(byId('budget').value) : null,
    resale_estimate: byId('valuation').value === 'manual' ? Number(byId('resale').value) : null,
  };
  try {
    if (inputFormat === 'json') payload.listings = JSON.parse(byId('records').value);
    else payload.csv_text = byId('records').value;
  } catch (_) {
    message('The pasted records are not valid JSON. Choose CSV for comma-separated rows.', true);
    return;
  }

  busy = true;
  const buttons = [byId('run'), byId('quick-run'), byId('sample'), byId('csv-file'), ...document.querySelectorAll('[data-format]')];
  buttons.forEach(button => { button.disabled = true; });
  byId('run').textContent = 'Building your board…';
  byId('quick-run').textContent = 'Building…';
  message('Validating rows, grouping products and calculating scenarios…');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(inputFormat === 'csv' ? '/api/import-csv' : '/api/compare', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      signal: controller.signal, body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw Error(data.detail?.message || data.detail?.[0]?.msg || 'Check the imported fields and price settings.');
    }
    renderBoard(data);
    message(`Board ready: ${data.retained} ranked rows in ${data.groups.length} product groups. No provider request was sent.`);
  } catch (error) {
    message(error.name === 'AbortError' ? 'The local comparison reached its time limit.' : error.message, true);
  } finally {
    clearTimeout(timeout);
    busy = false;
    buttons.forEach(button => { button.disabled = false; });
    byId('run').textContent = 'Build deal board ↗';
    byId('quick-run').textContent = 'Build board ↗';
  }
});

sample();

