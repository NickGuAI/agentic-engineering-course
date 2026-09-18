'use strict';

const $ = (id) => document.getElementById(id);
const sourceNames = {openai_news: 'OpenAI News', anthropic_news: 'Anthropic News', anthropic_engineering: 'Anthropic Engineering'};
const modeNames = {live: 'Live research', snapshot_replay: 'Saved-source replay', fixture: 'Offline demo', demo: 'Offline demo'};
const statusNames = {complete: 'Complete', partial: 'Partial coverage', blocked: 'Blocked', empty: 'No updates'};
let state = {csrf_token: '', runs: [], running: null};
let selectedRun = null;
let currentRun = null;
let selectionSequence = 0;
let pollTimer = null;
let watchedJob = null;
let requestPending = false;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}
function replace(id, ...nodes) { $(id).replaceChildren(...nodes); }
function formatNumber(value) { return Number.isFinite(value) ? value.toLocaleString('en-US') : 'Unknown'; }
function fixture(mode) { return /fixture|demo|synthetic/i.test(mode || ''); }
function modeName(mode) { return fixture(mode) ? 'Offline demo' : (modeNames[mode] || 'Saved run'); }
function formatDate(value, withTime = false) {
  if (!value) return 'Date unavailable';
  const date = new Date(/^\d{4}-\d{2}-\d{2}$/.test(value) ? `${value}T12:00:00Z` : value);
  if (Number.isNaN(date.getTime())) return 'Date unavailable';
  const options = {month: 'short', day: 'numeric', year: 'numeric', timeZone: 'America/New_York'};
  if (withTime) Object.assign(options, {hour: 'numeric', minute: '2-digit', timeZoneName: 'short'});
  return date.toLocaleString('en-US', options);
}
function safeSourceUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && ['openai.com', 'www.anthropic.com'].includes(url.hostname) && !url.username && !url.password && !url.port ? url.href : null;
  } catch (_) { return null; }
}
function publisher(url, articleId, manifest) {
  const entry = (manifest.selected_articles || []).find((article) => article.article_id === articleId);
  if (entry && sourceNames[entry.source_id]) return sourceNames[entry.source_id];
  const approved = safeSourceUrl(url);
  if (!approved) return 'Publisher';
  return approved.includes('openai.com') ? 'OpenAI' : 'Anthropic';
}
async function api(path, options = {}) {
  const response = await fetch(path, {credentials: 'same-origin', cache: 'no-store', ...options});
  let body;
  try { body = await response.json(); } catch (_) { throw new Error('The local server returned an unreadable response. Refresh to try again.'); }
  if (!response.ok) {
    let message = 'The local server could not complete this request.';
    if (response.status === 409) message = 'A research run is already in progress. Wait for it to finish.';
    else if (response.status === 403) message = 'Your local session needs a refresh. Refresh the page, then try again.';
    else if (response.status === 404) message = 'That saved run is unavailable.';
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return body;
}
function showError(message) {
  $('connection-error').hidden = !message;
  $('connection-error').textContent = message || '';
}
function setBusy(busy) {
  $('run-button').disabled = busy;
  $('demo-button').disabled = busy;
  $('days').disabled = busy;
  $('max-items').disabled = busy;
  $('run-button').firstElementChild.textContent = busy ? 'Research in progress' : 'Run research';
}
function showJob(job) {
  const running = job && job.status === 'running';
  setBusy(Boolean(running || requestPending));
  if (!job) return;
  $('job-status').hidden = false;
  $('job-status').classList.toggle('is-running', Boolean(running));
  $('job-status').classList.toggle('has-error', job.status === 'failed');
  if (running) $('job-status').textContent = job.kind === 'demo' ? 'Running the offline harness demonstration…' : 'Collecting sources, preparing evidence, and checking the briefing. This can take a few minutes.';
  else if (job.status === 'failed') $('job-status').textContent = 'The run stopped. Any saved diagnostics are available in the run history.';
  else $('job-status').textContent = job.kind === 'demo' ? 'Offline demonstration finished. Its saved runs are ready to inspect.' : 'Research finished. The saved result is ready to inspect.';
}
function renderHistory() {
  const history = $('run-history');
  history.replaceChildren();
  if (!state.runs.length) {
    history.append(element('p', 'muted small', 'Your runs will be saved here.'));
    return;
  }
  for (const run of state.runs) {
    const button = element('button', 'history-run');
    button.type = 'button';
    button.setAttribute('aria-current', String(run.run_id === selectedRun));
    button.setAttribute('aria-label', `${modeName(run.mode)}, ${formatDate(run.as_of)}, ${statusNames[run.status] || run.status}`);
    const top = element('span', 'history-run-top');
    const dot = element('span', `history-status ${['partial', 'blocked', 'empty'].includes(run.status) ? run.status : ''}`);
    dot.setAttribute('aria-hidden', 'true');
    top.append(element('span', '', modeName(run.mode)), dot);
    button.append(top, element('span', 'history-run-sub', `${formatDate(run.as_of)} · ${run.items || 0} update${run.items === 1 ? '' : 's'}`));
    button.title = run.run_id;
    button.addEventListener('click', () => loadRun(run.run_id));
    history.append(button);
  }
}
function metric(value, label, suffix = '') {
  const card = element('div', 'metric');
  const number = element('div', 'metric-value', value);
  if (suffix) number.append(element('small', '', ` ${suffix}`));
  card.append(number, element('div', 'metric-label', label));
  return card;
}
function emptyState(title, message) {
  const card = element('div', 'empty-state');
  card.append(element('span', 'empty-mark', '◌'), element('h3', '', title), element('p', '', message));
  return card;
}
function renderArticle(article, index, manifest, isDemo) {
  const card = element('article', 'article-card');
  const meta = element('div', 'article-meta');
  meta.append(element('span', 'publisher', publisher(article.url, article.article_id, manifest)), element('span', '', '·'), element('time', '', formatDate(article.published_at)), element('span', 'article-number', String(index + 1).padStart(2, '0')));
  const title = element('h4', '', article.title);
  card.append(meta, title, element('p', 'article-summary', article.summary));
  if (article.relevance) {
    const relevance = element('div', 'relevance');
    const text = String(article.relevance).replace(/^(?:\s*interpretation\s*:\s*)+/i, '');
    relevance.append(element('div', 'relevance-label', 'Why it matters · interpretation'), element('p', '', text));
    card.append(relevance);
  }
  const footer = element('div', 'article-footer');
  const url = safeSourceUrl(article.url);
  if (url && !isDemo) {
    const link = element('a', 'source-link', 'Read the original ↗');
    link.href = url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    footer.append(link);
  } else footer.append(element('span', 'muted small', isDemo ? 'Synthetic source · offline example' : 'Source link unavailable'));
  const ids = Array.isArray(article.evidence_ids) ? article.evidence_ids : [];
  const evidence = element('span', 'evidence-label', `${ids.length} evidence reference${ids.length === 1 ? '' : 's'}`);
  evidence.title = ids.join(', ');
  footer.append(evidence);
  card.append(footer);
  return card;
}
function sourceDescription(source) {
  if (source.error_code === 'http_403') return 'Access unavailable · HTTP 403';
  if (source.status === 'error') return source.error_code ? `Unavailable · ${source.error_code.replaceAll('_', ' ')}` : 'Source unavailable';
  if (source.coverage_limited) return 'Checked · limited coverage';
  return source.status === 'ok' ? 'Checked successfully' : 'Status unavailable';
}
function renderWarnings(warnings, status) {
  const section = $('warning-section');
  section.replaceChildren();
  section.hidden = !warnings.length && !['partial', 'blocked'].includes(status);
  section.classList.toggle('blocked', status === 'blocked');
  if (section.hidden) return;
  const detail = element('details');
  const title = status === 'blocked' ? 'This run could not finalize a trustworthy digest' : status === 'partial' ? 'A useful briefing, with gaps in coverage' : 'Run notes';
  detail.append(element('summary', '', `${title}${warnings.length ? ` · ${warnings.length} note${warnings.length === 1 ? '' : 's'}` : ''}`));
  if (status === 'partial') detail.append(element('p', '', 'Only available, checked evidence is included. Missing coverage does not mean there were no updates.'));
  if (warnings.length) {
    const list = element('ul');
    for (const warning of warnings) list.append(element('li', '', typeof warning === 'string' ? warning : JSON.stringify(warning)));
    detail.append(list);
  }
  section.append(detail);
}
function detailRow(label, value) {
  const row = element('div');
  row.append(element('dt', '', label), element('dd', '', value));
  return row;
}
function renderRun(data) {
  const manifest = data.manifest || {};
  const digest = data.digest || {};
  const statusRecord = data.status || {};
  const usage = data.usage || {};
  const counters = usage.counters || {};
  const verification = data.verification || {};
  const listing = state.runs.find((run) => run.run_id === selectedRun) || {};
  const mode = statusRecord.mode || manifest.mode || listing.mode;
  const status = statusRecord.status || digest.status || listing.status || 'blocked';
  const isDemo = fixture(mode);
  const items = Array.isArray(digest.items) ? digest.items : [];
  const sources = Array.isArray(manifest.sources) ? manifest.sources : [];
  const sourceCount = sources.filter((source) => source.status === 'ok').length;
  const modelCalls = counters.model_calls ?? listing.model_calls;
  const applicationTokens = counters.application_input_tokens ?? listing.input_tokens_estimated;
  const providerTokens = listing.provider_tokens;
  const cacheHits = usage.cache_hits ?? listing.cache_hits;
  $('briefing-title').textContent = isDemo ? 'An offline demonstration' : 'Your research briefing';
  $('briefing-date').textContent = digest.window || `Saved ${formatDate(manifest.as_of || listing.as_of, true)}`;
  replace('run-badges', element('span', `badge ${['complete', 'partial', 'blocked'].includes(status) ? status : ''}`, statusNames[status] || 'Saved run'), element('span', `badge ${isDemo ? 'fixture' : ''}`, modeName(mode)));
  $('demo-notice').hidden = !isDemo;
  replace('summary-metrics', metric(formatNumber(items.length), 'Updates in this digest'), metric(`${sourceCount}/${sources.length}`, 'Sources checked successfully'), metric(formatNumber(modelCalls), isDemo ? 'Scripted calls · simulated' : 'Model calls'), metric(formatNumber(applicationTokens), 'Application input tokens', 'est.'));
  $('coverage-section').hidden = !sources.length;
  $('coverage-summary').textContent = sources.length ? `${sources.length} approved source${sources.length === 1 ? '' : 's'}` : '';
  replace('source-list', ...sources.map((source) => {
    const chip = element('div', `source-chip ${source.status === 'error' ? 'source-error' : ''}`);
    const text = element('div');
    text.append(element('div', 'source-name', sourceNames[source.source_id] || source.source_id), element('div', 'source-state', sourceDescription(source)));
    chip.append(element('div', 'source-initial', source.source_id === 'openai_news' ? 'O' : 'A'), text);
    return chip;
  }));
  const warnings = [...new Set([...(statusRecord.warnings || []), ...(digest.warnings || [])])];
  renderWarnings(warnings, status);
  $('article-count').textContent = `${items.length} update${items.length === 1 ? '' : 's'}${isDemo ? ' · synthetic' : ''}`;
  if (items.length) replace('articles', ...items.map((item, index) => renderArticle(item, index, manifest, isDemo)));
  else if (status === 'empty') replace('articles', emptyState('A quiet window in the checked sources', 'No eligible updates were found for this run. Try a longer lookback window.'));
  else replace('articles', emptyState('No digest was finalized', 'This run stopped before it could publish a trustworthy result. Review the coverage and run notes above.'));
  $('run-details').hidden = false;
  replace('token-details', detailRow('Application input · estimated', formatNumber(applicationTokens)), detailRow(isDemo ? 'Provider tokens' : 'Provider total · reported', isDemo ? 'Not applicable · simulated' : (providerTokens == null ? 'Unknown' : formatNumber(providerTokens))), detailRow('Validated summary cache hits', formatNumber(cacheHits)), detailRow('Model calls', formatNumber(modelCalls)));
  $('token-note').textContent = isDemo ? 'This demo uses scripted outputs. Its estimates are not real LLM usage.' : 'Input estimates use UTF-8 bytes ÷ 3. Provider totals include extra model context and output; the two figures are not interchangeable. Unknown usage is not zero.';
  const checkArea = $('verification-details');
  checkArea.replaceChildren();
  checkArea.append(element('p', `verification-line ${verification.passed === false ? 'failed' : ''}`, verification.passed === true ? '✓ Current artifact checks passed' : verification.passed === false ? 'Checks did not pass' : 'No completed verification available'));
  const checks = element('div', 'check-tags');
  for (const check of verification.checks || []) checks.append(element('span', 'check-tag', String(check).replaceAll('_', ' ')));
  checkArea.append(checks);
  const model = manifest.model || usage.model || {};
  $('run-identity').textContent = `${selectedRun}${model.model ? `  ·  ${model.model}` : ''}${model.reasoning ? ` / ${model.reasoning} reasoning` : ''}  ·  Human review: ${verification.human_review || statusRecord.human_acceptance || 'pending'}`;
}
async function loadRun(id) {
  const sequence = ++selectionSequence;
  selectedRun = id;
  renderHistory();
  $('articles').classList.add('is-loading');
  try {
    const data = await api(`/api/runs/${encodeURIComponent(id)}`);
    if (sequence !== selectionSequence) return;
    currentRun = data;
    renderRun(data);
    showError('');
  } catch (error) {
    if (sequence === selectionSequence) showError(error.message);
  } finally {
    if (sequence === selectionSequence) $('articles').classList.remove('is-loading');
  }
}
async function refreshState({chooseLatest = false} = {}) {
  try {
    state = await api('/api/state');
    state.runs = Array.isArray(state.runs) ? state.runs : [];
    showError('');
    const stillSelected = !chooseLatest && state.runs.find((run) => run.run_id === selectedRun);
    const preferred = stillSelected || state.runs.find((run) => !fixture(run.mode) && run.items > 0) || state.runs[0];
    if (preferred) await loadRun(preferred.run_id);
    else {
      selectedRun = null;
      currentRun = null;
      selectionSequence += 1;
      $('briefing-title').textContent = 'Your research briefing';
      $('briefing-date').textContent = 'Your first briefing starts here.';
      $('article-count').textContent = '';
      for (const id of ['coverage-section', 'warning-section', 'demo-notice', 'run-details']) $(id).hidden = true;
      replace('summary-metrics');
      replace('run-badges');
      replace('articles', emptyState('Make room for the important updates', 'Run research to collect recent AI news, or try the offline demo to explore the harness.'));
    }
    renderHistory();
    if (state.running) {
      showJob(state.running);
      watchJob(state.running.id);
    } else if (!watchedJob) setBusy(requestPending);
  } catch (error) {
    showError('Could not reach the local research server. Make sure it is running, then refresh.');
  }
}
function watchJob(id) {
  if (watchedJob === id) return;
  watchedJob = id;
  clearTimeout(pollTimer);
  pollTimer = setTimeout(() => pollJob(id), 1600);
}
async function pollJob(id) {
  if (watchedJob !== id) return;
  try {
    const body = await api(`/api/jobs/${encodeURIComponent(id)}`);
    const job = body.job || body;
    showJob(job);
    if (job.status === 'running') {
      pollTimer = setTimeout(() => pollJob(id), 1800);
      return;
    }
    watchedJob = null;
    await refreshState();
    const ids = Array.isArray(job.run_ids) ? job.run_ids : [];
    const idToShow = job.run_id || ids[ids.length - 1];
    if (idToShow) await loadRun(idToShow);
    showJob(job);
  } catch (error) {
    if (error.status === 404) {
      clearTimeout(pollTimer);
      pollTimer = null;
      watchedJob = null;
      state.running = null;
      $('job-status').hidden = true;
      setBusy(requestPending);
      await refreshState();
      showError('The server may have restarted, so this job’s status is unavailable. Saved runs remain accessible.');
      return;
    }
    showError('Connection interrupted while the run was in progress. Reconnecting to the local server…');
    pollTimer = setTimeout(() => pollJob(id), 4000);
  }
}
async function startJob(kind) {
  if (requestPending || watchedJob) return;
  requestPending = true;
  setBusy(true);
  showError('');
  try {
    const data = await api('/api/jobs', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': state.csrf_token}, body: JSON.stringify({kind, days: Number($('days').value), max_items: Number($('max-items').value)})});
    const job = data.job || data;
    showJob(job);
    watchJob(job.id);
  } catch (error) {
    await refreshState();
    showError(error.message);
  } finally {
    requestPending = false;
    setBusy(Boolean(watchedJob));
  }
}
$('research-form').addEventListener('submit', (event) => { event.preventDefault(); startJob('live'); });
$('demo-button').addEventListener('click', () => startJob('demo'));
$('refresh-button').addEventListener('click', () => refreshState());
refreshState();
