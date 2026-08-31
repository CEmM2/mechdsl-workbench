(() => {
  'use strict';

  const byId = (id) => document.getElementById(id);
  const source = byId('source-input');
  const energy = byId('energy-source');
  const runButton = byId('run-button');
  const exampleSelect = byId('example-select');
  const maxSourceBytes = Number(document.body.dataset.maxSourceBytes || 262144);
  const initialMode = document.body.dataset.initialMode || 'mechanics';

  let mode = initialMode;
  let generatedSource = '';
  let generatedFilename = 'mechdsl_generated.py';
  let lastDiagnosticText = '';
  let previewSerial = 0;
  let previewTimer = null;

  function utf8Size(value) {
    return new TextEncoder().encode(value).length;
  }

  function updateEditorChrome(textarea, gutter, counter) {
    const count = Math.max(1, textarea.value.split('\n').length);
    gutter.textContent = Array.from({ length: count }, (_, index) => String(index + 1)).join('\n');
    gutter.scrollTop = textarea.scrollTop;
    const size = utf8Size(textarea.value);
    counter.textContent = `${size.toLocaleString()} / ${maxSourceBytes.toLocaleString()} bytes`;
    counter.classList.toggle('limit-warning', size > maxSourceBytes);
  }

  function bindEditor(textarea, gutter, counter, onInput) {
    const update = () => {
      updateEditorChrome(textarea, gutter, counter);
      onInput?.();
    };
    textarea.addEventListener('input', update);
    textarea.addEventListener('scroll', () => { gutter.scrollTop = textarea.scrollTop; });
    textarea.addEventListener('keydown', (event) => {
      if (event.key === 'Tab') {
        event.preventDefault();
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        textarea.setRangeText('  ', start, end, 'end');
        textarea.dispatchEvent(new Event('input'));
      }
    });
    updateEditorChrome(textarea, gutter, counter);
  }

  function setActivity(message, kind = 'neutral') {
    const target = byId('activity-status');
    target.textContent = message;
    target.dataset.kind = kind;
  }

  function switchTab(name) {
    document.querySelectorAll('.tab').forEach((tab) => {
      const selected = tab.dataset.tab === name;
      tab.classList.toggle('active', selected);
      tab.setAttribute('aria-selected', String(selected));
    });
    document.querySelectorAll('.tab-panel').forEach((panel) => {
      const selected = panel.id === `panel-${name}`;
      panel.classList.toggle('active', selected);
      panel.hidden = !selected;
    });
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    let data;
    try {
      data = await response.json();
    } catch (_error) {
      throw new Error(`Server returned ${response.status} without a JSON response`);
    }
    if (!response.ok && data.ok !== false) {
      throw new Error(`Server returned HTTP ${response.status}`);
    }
    return data;
  }

  function schedulePreview() {
    clearTimeout(previewTimer);
    previewTimer = setTimeout(refreshPreview, 220);
  }

  async function refreshPreview() {
    const serial = ++previewSerial;
    try {
      const data = await requestJson('/api/preview', {
        method: 'POST',
        body: JSON.stringify({ mode, source: source.value })
      });
      if (serial !== previewSerial) return;
      if (!data.ok) {
        renderDiagnostic(data.diagnostic || { message: 'Preview failed', stage: 'preview' });
        return;
      }

      byId('preview-body').innerHTML = data.body_html;
      byId('preview-note').textContent = data.note || '';
      byId('directive-heading').textContent = data.directive_heading || 'Directives';
      renderDirectives(data.directives || [], data.empty_directive_message || 'No directives found.');
      renderPreviewWarnings(data.warnings || []);

      if (mode === 'mechanics' && window.MathJax && typeof window.MathJax.typesetPromise === 'function') {
        window.MathJax.typesetClear?.([byId('preview-body')]);
        window.MathJax.typesetPromise([byId('preview-body')]).catch(() => {});
      }
    } catch (error) {
      byId('preview-note').textContent = `Preview unavailable: ${error.message}`;
    }
  }

  function renderDirectives(directives, emptyMessage) {
    const container = byId('directive-cards');
    container.replaceChildren();
    if (!directives.length) {
      const empty = document.createElement('p');
      empty.className = 'muted';
      empty.textContent = emptyMessage;
      container.appendChild(empty);
      return;
    }
    directives.forEach((directive) => {
      const card = document.createElement('article');
      card.className = 'directive-card';
      const title = document.createElement('strong');
      title.textContent = directive.title;
      const summary = document.createElement('span');
      summary.textContent = directive.summary;
      const raw = document.createElement('code');
      raw.textContent = directive.raw;
      card.append(title, summary, raw);
      container.appendChild(card);
    });
  }

  function renderPreviewWarnings(warnings) {
    const target = byId('preview-warnings');
    target.hidden = warnings.length === 0;
    target.replaceChildren();
    warnings.forEach((warning) => {
      const row = document.createElement('p');
      row.textContent = warning;
      target.appendChild(row);
    });
  }

  function modeConfig(targetMode = mode) {
    return targetMode === 'mechanics'
      ? {
          action: 'Compile', running: 'Compiling through MechDSL…', completed: 'Compilation completed.',
          failed: 'Compilation failed.', endpoint: '/api/compile', sourceHeading: 'Mechanics LaTeX source',
          sourceLabel: 'Problem source', sourceHelp: 'Enter LaTeX containing MechDSL mechanics directives.',
          translationLabel: 'Compiler View', generatedLabel: 'Generated Taichi', filename: 'mechdsl_problem.tex'
        }
      : {
          action: 'Transpile', running: 'Transpiling through algo2code…', completed: 'Transpilation completed.',
          failed: 'Transpilation failed.', endpoint: '/api/transpile', sourceHeading: 'Algorithm LaTeX source',
          sourceLabel: 'Algpseudocode source', sourceHelp: 'Enter LaTeX containing an algorithmic environment and algo2code directives.',
          translationLabel: 'Transpiler View', generatedLabel: 'Generated Taichi', filename: 'algorithm.tex'
        };
  }

  function applyModeChrome() {
    const config = modeConfig();
    document.body.dataset.mode = mode;
    document.querySelectorAll('.mode-button').forEach((button) => {
      const selected = button.dataset.mode === mode;
      button.classList.toggle('active', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
    byId('source-heading').textContent = config.sourceHeading;
    byId('source-label').textContent = config.sourceLabel;
    byId('source-help').textContent = config.sourceHelp;
    byId('translation-tab-label').textContent = config.translationLabel;
    byId('generated-tab-label').textContent = config.generatedLabel;
    runButton.querySelector('.button-label').textContent = config.action;
    byId('toggle-energy').hidden = mode !== 'mechanics';
    if (mode !== 'mechanics') {
      byId('energy-section').hidden = true;
      byId('toggle-energy').setAttribute('aria-expanded', 'false');
    }
    filterExampleOptions();
  }

  function filterExampleOptions() {
    let first = null;
    Array.from(exampleSelect.options).forEach((option) => {
      const visible = option.dataset.mode === mode;
      option.hidden = !visible;
      option.disabled = !visible;
      if (visible && first === null) first = option;
    });
    if (!exampleSelect.selectedOptions.length || exampleSelect.selectedOptions[0].dataset.mode !== mode) {
      if (first) exampleSelect.value = first.value;
    }
  }

  function draftKey(targetMode = mode) {
    return `mechdsl-workbench:draft:v2:${targetMode}`;
  }

  function saveDraft() {
    try {
      localStorage.setItem(draftKey(), JSON.stringify({
        source: source.value,
        energy: mode === 'mechanics' ? energy.value : ''
      }));
    } catch (_error) {
      // Local storage is optional; private browser modes sometimes disable it.
    }
  }

  function readDraft(targetMode) {
    try {
      const raw = localStorage.getItem(draftKey(targetMode));
      if (!raw) return null;
      const value = JSON.parse(raw);
      return value && typeof value.source === 'string' ? value : null;
    } catch (_error) {
      return null;
    }
  }

  async function switchMode(nextMode) {
    if (nextMode === mode) return;
    saveDraft();
    mode = nextMode;
    applyModeChrome();
    resetOutputForMode();

    const draft = readDraft(mode);
    if (draft) {
      source.value = draft.source;
      energy.value = typeof draft.energy === 'string' ? draft.energy : '';
      byId('example-description').textContent = `Restored local ${mode} draft.`;
      updateAllEditorChrome();
      schedulePreview();
      return;
    }
    const first = Array.from(exampleSelect.options).find((option) => option.dataset.mode === mode);
    if (first) await loadExample(first.value);
  }

  async function loadExample(exampleId) {
    setActivity('Loading example…', 'working');
    try {
      const data = await requestJson(`/api/examples/${encodeURIComponent(exampleId)}`);
      const example = data.example;
      if (example.mode !== mode) {
        mode = example.mode;
        applyModeChrome();
      }
      exampleSelect.value = example.id;
      source.value = example.source || '';
      energy.value = example.energy_source || '';
      const hasEnergy = Boolean(example.energy_source);
      byId('energy-section').hidden = !hasEnergy;
      byId('toggle-energy').setAttribute('aria-expanded', String(hasEnergy));
      byId('example-description').textContent = example.description || '';
      updateAllEditorChrome();
      resetOutputForMode();
      saveDraft();
      await refreshPreview();
      setActivity('Example loaded.', 'success');
    } catch (error) {
      renderDiagnostic({ severity: 'error', stage: 'http', category: error.name, message: error.message });
      switchTab('diagnostics');
      setActivity('Example could not be loaded.', 'error');
    }
  }

  async function runCurrentSource() {
    const sourceBytes = utf8Size(source.value);
    const energyBytes = utf8Size(energy.value);
    const config = modeConfig();
    if (!source.value.trim()) {
      renderDiagnostic({
        severity: 'error', stage: 'input', category: 'EmptySource',
        message: mode === 'mechanics' ? 'Enter a mechanics source before compiling.' : 'Enter an algorithm source before transpiling.'
      });
      switchTab('diagnostics');
      return;
    }
    if (sourceBytes > maxSourceBytes || (mode === 'mechanics' && energyBytes > maxSourceBytes)) {
      renderDiagnostic({
        severity: 'error', stage: 'input', category: 'SourceTooLarge',
        message: `Each source is limited to ${maxSourceBytes.toLocaleString()} bytes.`
      });
      switchTab('diagnostics');
      return;
    }

    runButton.disabled = true;
    runButton.classList.add('busy');
    setActivity(config.running, 'working');

    const payload = mode === 'mechanics'
      ? {
          problem_source: source.value,
          energy_source: energy.value.trim() ? energy.value : null,
          profile: 'mvp'
        }
      : { algorithm_source: source.value, backend: 'taichi' };

    try {
      const data = await requestJson(config.endpoint, {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (data.ok) {
        renderSuccess(data);
        setActivity(config.completed, 'success');
      } else {
        renderDiagnostic(data.diagnostic || {
          stage: mode === 'mechanics' ? 'compiler' : 'transpiler',
          category: 'UnknownFailure',
          message: config.failed
        });
        switchTab('diagnostics');
        setActivity(config.failed, 'error');
      }
    } catch (error) {
      renderDiagnostic({
        severity: 'error', stage: 'http', category: error.name, message: error.message
      });
      switchTab('diagnostics');
      setActivity(`${config.action} request failed.`, 'error');
    } finally {
      runButton.disabled = false;
      runButton.classList.remove('busy');
      saveDraft();
    }
  }

  function renderSuccess(data) {
    generatedSource = data.generated_source || data.emitted_source || data.code || '';
    byId('generated-output').textContent = generatedSource || '# The integration API returned an empty source string.';
    const lineCount = Number.isInteger(data.line_count)
      ? data.line_count
      : (generatedSource ? generatedSource.split('\n').length : 0);

    if (data.result_kind === 'transpile' || mode === 'algorithm') {
      const validity = data.valid_python ? 'valid Python' : 'Python validation failed';
      byId('generated-meta').textContent = `${lineCount.toLocaleString()} lines · ${data.entry_point || 'unknown entry point'} · ${validity}`;
      generatedFilename = `${safeFilename(data.entry_point || 'algorithm')}.py`;
      byId('run-summary').textContent = `${data.entry_point || 'algorithm'} · ${lineCount.toLocaleString()} lines`;
    } else {
      byId('generated-meta').textContent = `${lineCount.toLocaleString()} lines · semantic hash ${shortHash(data.content_hash)}`;
      generatedFilename = 'mechdsl_generated.py';
      byId('run-summary').textContent = `${formatElement(data.element_ir_summary)} · ${shortHash(data.content_hash)}`;
    }

    byId('copy-generated').disabled = !generatedSource;
    byId('download-generated').disabled = !generatedSource;
    renderTranslationView(data);
    clearDiagnostic();
    switchTab('generated');
  }

  function renderTranslationView(data) {
    let entries;
    let raw;
    if (data.result_kind === 'transpile' || mode === 'algorithm') {
      entries = [
        ['Entry point', data.entry_point],
        ['Backend', data.backend || 'taichi'],
        ['Generated lines', data.line_count],
        ['Valid Python', data.valid_python ? 'Yes' : 'No']
      ];
      raw = {
        code: data.code,
        entry_point: data.entry_point,
        line_count: data.line_count,
        valid_python: data.valid_python,
        backend: data.backend
      };
    } else {
      const summary = data.element_ir_summary || {};
      entries = [
        ['Element', summary.element_type],
        ['Dimension', summary.dim],
        ['Nodes', summary.n_nodes],
        ['Quadrature points', summary.n_quadrature_points],
        ['Formulation', summary.formulation],
        ['Derived energy', data.derived_energy_present ? 'Yes' : 'No'],
        ['Semantic hash', data.content_hash]
      ];
      raw = {
        element_ir_summary: summary,
        content_hash: data.content_hash,
        derived_energy_present: data.derived_energy_present
      };
    }

    const list = byId('translation-summary');
    list.replaceChildren();
    entries.forEach(([label, value]) => {
      const dt = document.createElement('dt');
      const dd = document.createElement('dd');
      dt.textContent = label;
      dd.textContent = value ?? 'Not reported';
      list.append(dt, dd);
    });
    byId('translation-raw').textContent = JSON.stringify(raw, null, 2);
    byId('translation-empty').hidden = true;
    byId('translation-result').hidden = false;
  }

  function resetOutputForMode() {
    generatedSource = '';
    generatedFilename = mode === 'mechanics' ? 'mechdsl_generated.py' : 'algorithm.py';
    byId('generated-output').textContent = '# Generated source will appear here.';
    byId('generated-meta').textContent = `Run the ${mode} source to generate Taichi.`;
    byId('copy-generated').disabled = true;
    byId('download-generated').disabled = true;
    byId('translation-empty').hidden = false;
    byId('translation-result').hidden = true;
    byId('run-summary').textContent = 'No translation yet';
    clearDiagnostic();
    switchTab('preview');
  }

  function renderDiagnostic(diagnostic) {
    const normalized = {
      severity: diagnostic.severity || 'error',
      stage: diagnostic.stage || 'unknown',
      category: diagnostic.category || 'CompilerError',
      code: diagnostic.code || '',
      message: diagnostic.message || 'Unknown failure',
      line: diagnostic.line ?? null,
      column: diagnostic.column ?? null,
      source_excerpt: diagnostic.source_excerpt || '',
      technical_details: diagnostic.technical_details || ''
    };
    byId('diagnostic-stage').textContent = normalized.stage;
    byId('diagnostic-category').textContent = normalized.category;
    byId('diagnostic-code').textContent = normalized.code;
    byId('diagnostic-message').textContent = normalized.message;

    const location = byId('diagnostic-location');
    if (normalized.line !== null) {
      location.textContent = `Line ${normalized.line}${normalized.column !== null ? `, column ${normalized.column}` : ''}`;
      location.hidden = false;
    } else {
      location.hidden = true;
    }

    const excerpt = byId('diagnostic-excerpt');
    excerpt.textContent = normalized.source_excerpt;
    excerpt.hidden = !normalized.source_excerpt;

    const detailsWrap = byId('diagnostic-details-wrap');
    byId('diagnostic-details').textContent = normalized.technical_details;
    detailsWrap.hidden = !normalized.technical_details;

    byId('diagnostic-empty').hidden = true;
    byId('diagnostic-result').hidden = false;
    byId('diagnostic-count').hidden = false;
    byId('copy-diagnostic').disabled = false;
    lastDiagnosticText = [
      `${normalized.stage}: ${normalized.category}${normalized.code ? ` (${normalized.code})` : ''}`,
      normalized.message,
      normalized.line !== null ? `Line ${normalized.line}${normalized.column !== null ? `, column ${normalized.column}` : ''}` : '',
      normalized.source_excerpt,
      normalized.technical_details
    ].filter(Boolean).join('\n\n');
  }

  function clearDiagnostic() {
    lastDiagnosticText = '';
    byId('diagnostic-empty').hidden = false;
    byId('diagnostic-result').hidden = true;
    byId('diagnostic-count').hidden = true;
    byId('copy-diagnostic').disabled = true;
  }

  async function copyText(value, successMessage) {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setActivity(successMessage, 'success');
    } catch (_error) {
      setActivity('Clipboard access was denied.', 'error');
    }
  }

  function downloadText(filename, value) {
    const blob = new Blob([value], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function safeFilename(value) {
    return String(value).replace(/[^A-Za-z0-9_.-]+/g, '_').replace(/^_+|_+$/g, '') || 'algorithm';
  }

  function shortHash(value) {
    return typeof value === 'string' && value ? `${value.slice(0, 10)}…` : 'no hash';
  }

  function formatElement(summary) {
    if (!summary) return 'Unknown element';
    const element = summary.element_type || 'element';
    const dim = summary.dim ? `${summary.dim}D` : '';
    return [element, dim].filter(Boolean).join(' · ');
  }

  async function refreshCapabilities() {
    const banner = byId('compiler-banner');
    banner.className = 'compiler-banner checking';
    byId('compiler-banner-text').textContent = 'Checking installed MechDSL toolchain…';
    try {
      const data = await requestJson('/api/capabilities');
      const status = data.status || {};
      banner.className = `compiler-banner ${status.compatible ? 'ready' : 'warning'}`;
      byId('compiler-banner-text').textContent = status.message || 'Capability check completed.';
      document.body.dataset.mechanicsReady = String(Boolean(status.mechanics_ready));
      document.body.dataset.algorithmReady = String(Boolean(status.algorithm_ready));
    } catch (error) {
      banner.className = 'compiler-banner warning';
      byId('compiler-banner-text').textContent = `Capability check failed: ${error.message}`;
    }
  }

  function updateAllEditorChrome() {
    updateEditorChrome(source, byId('source-lines'), byId('source-size'));
    updateEditorChrome(energy, byId('energy-lines'), byId('energy-size'));
  }

  document.querySelectorAll('.tab').forEach((tab) => {
    tab.addEventListener('click', () => switchTab(tab.dataset.tab));
  });
  document.querySelectorAll('.mode-button').forEach((button) => {
    button.addEventListener('click', () => switchMode(button.dataset.mode));
  });
  exampleSelect.addEventListener('change', () => loadExample(exampleSelect.value));
  runButton.addEventListener('click', runCurrentSource);
  byId('refresh-capabilities').addEventListener('click', refreshCapabilities);
  byId('toggle-energy').addEventListener('click', () => {
    const section = byId('energy-section');
    section.hidden = !section.hidden;
    byId('toggle-energy').setAttribute('aria-expanded', String(!section.hidden));
    if (!section.hidden) updateEditorChrome(energy, byId('energy-lines'), byId('energy-size'));
  });
  byId('download-source').addEventListener('click', () => downloadText(modeConfig().filename, source.value));
  byId('copy-generated').addEventListener('click', () => copyText(generatedSource, 'Generated source copied.'));
  byId('download-generated').addEventListener('click', () => downloadText(generatedFilename, generatedSource));
  byId('copy-diagnostic').addEventListener('click', () => copyText(lastDiagnosticText, 'Diagnostic copied.'));
  document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      runCurrentSource();
    }
  });

  bindEditor(source, byId('source-lines'), byId('source-size'), () => {
    saveDraft();
    schedulePreview();
  });
  bindEditor(energy, byId('energy-lines'), byId('energy-size'), saveDraft);

  applyModeChrome();
  const initialDraft = readDraft(mode);
  if (initialDraft) {
    source.value = initialDraft.source;
    energy.value = typeof initialDraft.energy === 'string' ? initialDraft.energy : '';
    byId('example-description').textContent = `Restored local ${mode} draft.`;
    updateAllEditorChrome();
  }
  refreshPreview();
})();
