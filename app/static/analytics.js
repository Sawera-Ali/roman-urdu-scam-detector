'use strict';
(() => {
  const get = (id) => document.getElementById(id);
  const ns = 'http://www.w3.org/2000/svg';
  const date = (value) => new Date(/Z$|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`).toLocaleString();
  const label = (value) => value === 'Scam' ? 'Scam' : 'Authentic';
  const confidence = (value) => value === null ? 'Unavailable' : `${value.toFixed(1)}%`;
  let requestNumber = 0;
  function svg(tag, attributes, parent, text) {
    const element = document.createElementNS(ns, tag);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
    if (text !== undefined) element.textContent = text;
    parent.append(element);
    return element;
  }
  function tooltip(element, text) {
    element.setAttribute('tabindex', '0');
    element.setAttribute('aria-label', text);
    svg('title', {}, element, text);
    ['mouseenter', 'focus', 'click'].forEach((event) => element.addEventListener(event, () => {
      get('chartTooltip').textContent = text;
    }));
  }
  function render(data) {
    get('totalScans').textContent = data.total_scans.toLocaleString();
    get('totalScam').textContent = data.total_scam.toLocaleString();
    get('totalAuthentic').textContent = data.total_authentic.toLocaleString();
    get('scamRate').textContent = `${data.scam_percentage}%`;
    get('analyticsEmpty').hidden = data.total_scans !== 0;
    get('analyticsCharts').hidden = data.total_scans === 0;
    get('chartTooltip').textContent = 'Hover over, tap, or focus a chart mark for details.';
    const donut = get('distributionChart');
    donut.replaceChildren();
    get('distributionLegend').replaceChildren();
    const circumference = 2 * Math.PI * 80;
    let offset = 0;
    [['Scam', data.total_scam, data.scam_percentage, 'scam-mark'], ['Authentic', data.total_authentic, data.authentic_percentage, 'authentic-mark']].forEach(([name, count, percentage, className]) => {
      if (count) {
        const length = count / data.total_scans * circumference;
        const mark = svg('circle', { cx: 120, cy: 120, r: 80, fill: 'none', 'stroke-width': 28, class: className,
          'stroke-dasharray': `${length} ${circumference - length}`, 'stroke-dashoffset': -offset, transform: 'rotate(-90 120 120)' }, donut);
        tooltip(mark, `${name}: ${count} scans (${percentage}%)`);
        offset += length;
      }
      const line = document.createElement('p');
      line.className = name === 'Scam' ? 'scam-key' : 'authentic-key';
      line.textContent = `${name}: ${count} (${percentage}%)`;
      get('distributionLegend').append(line);
    });
    svg('text', { x: 120, y: 120, 'text-anchor': 'middle', class: 'donut-total' }, donut, data.total_scans);
    svg('text', { x: 120, y: 143, 'text-anchor': 'middle' }, donut, 'saved scans');
    const trend = get('confidenceChart');
    trend.replaceChildren();
    [0, 25, 50, 75, 100].forEach((tick) => {
      const y = 195 - tick * 1.65;
      svg('line', { x1: 42, y1: y, x2: 575, y2: y, class: 'chart-gridline' }, trend);
      svg('text', { x: 34, y: y + 4, 'text-anchor': 'end' }, trend, `${tick}%`);
    });
    const rows = data.recent_scans;
    rows.forEach((row, index) => {
      const x = rows.length === 1 ? 310 : 55 + index * 505 / (rows.length - 1);
      if (row.confidence !== null) {
        const mark = svg('circle', { cx: x, cy: 195 - row.confidence * 1.65, r: 6,
          class: row.prediction === 'Scam' ? 'scam-point' : 'authentic-point' }, trend);
        tooltip(mark, `Scan #${row.id} · ${label(row.prediction)} · ${confidence(row.confidence)} model confidence · ${date(row.timestamp)}`);
      }
      if (index === 0 || index === rows.length - 1 || rows.length <= 5) {
        svg('text', { x, y: 220, 'text-anchor': 'middle' }, trend, `#${row.id}`);
      }
    });
    if (rows.length && rows.every((row) => row.confidence === null)) {
      svg('text', { x: 310, y: 110, 'text-anchor': 'middle' }, trend, 'No confidence available for these scans');
    }
    get('scanHistory').replaceChildren(...[...rows].reverse().map((row) => {
      const tr = document.createElement('tr');
      [`#${row.id}`, label(row.prediction), confidence(row.confidence), date(row.timestamp)].forEach((value, index) => {
        const td = document.createElement('td');
        td.textContent = value;
        if (index === 1) td.className = row.prediction === 'Scam' ? 'scam-key' : 'authentic-key';
        tr.append(td);
      });
      return tr;
    }));
  }
  async function refresh() {
    const current = ++requestNumber;
    get('refreshAnalytics').disabled = true;
    get('analyticsStatus').textContent = 'Updating scan history…';
    try {
      const response = await fetch('/api/analytics', { cache: 'no-store', signal: AbortSignal.timeout(10000) });
      const data = await response.json();
      if (current !== requestNumber) return;
      if (!response.ok) throw new Error(data.error || 'Analytics are unavailable. Please retry.');
      render(data);
      get('analyticsContent').hidden = false;
      get('analyticsStatus').textContent = `Updated ${new Date().toLocaleTimeString()} · Saved scans across all sessions on this local app.`;
    } catch (error) {
      if (current !== requestNumber) return;
      get('analyticsContent').hidden = true;
      get('analyticsStatus').textContent = error.name === 'TimeoutError' ? 'Analytics request timed out. Please retry.' : (error instanceof TypeError ? 'Could not load analytics. Check the local server and retry.' : error.message);
    } finally {
      if (current === requestNumber) get('refreshAnalytics').disabled = false;
    }
  }
  get('refreshAnalytics').addEventListener('click', refresh);
  document.addEventListener('scan-completed', refresh);
  window.addEventListener('hashchange', () => { if (location.hash === '#dashboard') refresh(); });
  window.addEventListener('focus', refresh);
  refresh();
})();
