/**
 * MeetAssistant — Upload page logic
 *
 * Features:
 *  - Drag & drop + click-to-pick file upload
 *  - Client-side validation (size, type)
 *  - Template card picker
 *  - 3-stage progress (upload → transcribe → summarize) via XHR
 *  - Result tabs with Markdown rendering, copy, feedback
 *  - Cancel, toast notifications, keyboard a11y
 */
(function () {
  'use strict';

  // ---- State ----
  const state = {
    selectedFile: null,
    selectedTemplate: 'product',
    xhr: null,
    isProcessing: false,
    lastResult: null,
  };

  const MAX_SIZE = 100 * 1024 * 1024; // 100 MB
  const ALLOWED = ['wav', 'mp3', 'pcm', 'opus', 'webm'];

  // ---- Template catalog (icon + name + desc + type) ----
  const TEMPLATES = [
    { type: 'product', name: '产品会议', icon: 'briefcase', desc: '产品规划、需求讨论、功能评审' },
    { type: 'business', name: '商务会议', icon: 'trending-up', desc: '商务谈判、合作洽谈、销售会议' },
    { type: 'technical', name: '技术会议', icon: 'code', desc: '技术评审、架构设计、代码审查' },
    { type: 'management', name: '管理会议', icon: 'users', desc: '团队管理、项目管理、战略规划' },
    { type: 'marketing', name: '市场营销', icon: 'message-square', desc: '市场策略、营销活动、品牌推广' },
    { type: 'finance', name: '财务会议', icon: 'dollar', desc: '财务分析、预算规划、成本控制' },
    { type: 'testcase', name: '用例评审', icon: 'list', desc: '测试用例评审、测试策略制定' },
    { type: 'requirement', name: '需求评审', icon: 'file', desc: '需求分析、需求变更讨论' },
    { type: 'general', name: '通用会议', icon: 'message-square', desc: '一般性会议、跨部门协作' },
  ];

  // ---- DOM ----
  const $ = (sel) => document.querySelector(sel);
  const dom = {
    form: $('#processForm'),
    uploadZone: $('#uploadZone'),
    fileInput: $('#audioFile'),
    filePreview: $('#filePreview'),
    fileName: $('#fileName'),
    fileMeta: $('#fileMeta'),
    removeFile: $('#removeFile'),
    templateSelect: $('#templateSelect'),
    templateGrid: $('#templateGrid'),
    processBtn: $('#processBtn'),
    cancelBtn: $('#cancelBtn'),
    progressSection: $('#progressSection'),
    stepUpload: $('#stepUpload'),
    stepTranscribe: $('#stepTranscribe'),
    stepSummarize: $('#stepSummarize'),
    uploadProgressBar: $('#uploadProgressBar'),
    uploadProgressLabel: $('#uploadProgressLabel'),
    resultSection: $('#resultSection'),
    tabButtons: document.querySelectorAll('[role="tab"]'),
    tabPanels: document.querySelectorAll('[role="tabpanel"]'),
    transcriptionText: $('#transcriptionText'),
    summaryText: $('#summaryText'),
    copyTranscription: $('#copyTranscription'),
    copySummary: $('#copySummary'),
    feedbackSummary: $('#feedbackSummary'),
    feedbackButtons: document.querySelectorAll('#feedbackSummary [data-vote]'),
    downloadZip: $('#downloadZip'),
    downloadTranscription: $('#downloadTranscription'),
    downloadSummary: $('#downloadSummary'),
    errorBanner: $('#errorBanner'),
    errorText: $('#errorText'),
  };

  // ---- Helpers ----
  function fmtSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  }
  function getExt(name) {
    return name.includes('.') ? name.split('.').pop().toLowerCase() : '';
  }
  function setStep(stepEl, status, detail) {
    stepEl.setAttribute('data-status', status);
    if (detail !== undefined) {
      const detailEl = stepEl.querySelector('.step-detail');
      if (detailEl) detailEl.textContent = detail;
    }
  }
  function resetSteps() {
    setStep(dom.stepUpload, 'pending');
    setStep(dom.stepTranscribe, 'pending');
    setStep(dom.stepSummarize, 'pending');
    dom.uploadProgressBar.style.width = '0%';
    dom.uploadProgressLabel.textContent = '准备中…';
  }
  function showError(msg) {
    dom.errorText.textContent = msg;
    dom.errorBanner.hidden = false;
    if (window.toast) window.toast.error(msg);
  }
  function clearError() {
    dom.errorBanner.hidden = true;
  }

  // ---- File selection ----
  function handleFileSelect(file) {
    clearError();
    if (!file) return;
    const ext = getExt(file.name);
    if (!ALLOWED.includes(ext)) {
      showError(`不支持的文件格式 .${ext}。支持：${ALLOWED.map((e) => `.${e}`).join(', ')}`);
      return;
    }
    if (file.size > MAX_SIZE) {
      showError(`文件过大（${fmtSize(file.size)}）。最大支持 ${fmtSize(MAX_SIZE)}。`);
      return;
    }
    state.selectedFile = file;
    dom.fileName.textContent = file.name;
    dom.fileMeta.textContent = `${fmtSize(file.size)} · .${ext}`;
    dom.filePreview.hidden = false;
    dom.uploadZone.hidden = true;
    dom.processBtn.disabled = false;
  }

  function removeFile() {
    state.selectedFile = null;
    state.lastResult = null;
    dom.fileInput.value = '';
    dom.filePreview.hidden = true;
    dom.uploadZone.hidden = false;
    dom.processBtn.disabled = true;
    dom.resultSection.hidden = true;
    dom.progressSection.hidden = true;
    clearError();
  }

  // ---- Templates (progressive enhancement) ----
  function renderTemplates() {
    // Build the card grid, hide the <select>
    const selectEl = dom.templateSelect;
    if (selectEl) {
      selectEl.hidden = true;
      selectEl.setAttribute('aria-hidden', 'true');
      // Don't disable — we still keep it as a hidden fallback for noscript users
      selectEl.tabIndex = -1;
    }
    dom.templateGrid.hidden = false;
    dom.templateGrid.innerHTML = '';
    TEMPLATES.forEach((t) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'template-card';
      btn.setAttribute('aria-pressed', String(t.type === state.selectedTemplate));
      btn.setAttribute('data-template', t.type);
      btn.innerHTML = `
        <span class="template-card-icon" data-lucide="${t.icon}"></span>
        <span class="template-card-name">${t.name}</span>
        <span class="template-card-desc">${t.desc}</span>
      `;
      btn.addEventListener('click', () => {
        state.selectedTemplate = t.type;
        // Sync the hidden <select> too (in case form ever submits natively)
        if (selectEl) selectEl.value = t.type;
        document.querySelectorAll('.template-card').forEach((el) => {
          el.setAttribute('aria-pressed', String(el.getAttribute('data-template') === t.type));
        });
      });
      dom.templateGrid.appendChild(btn);
    });
    if (window.appIcons) window.appIcons.render(dom.templateGrid);
  }

  // ---- Drag & drop + click to pick ----
  function setupDragDrop() {
    const zone = dom.uploadZone;
    ['dragenter', 'dragover'].forEach((evt) =>
      zone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        zone.setAttribute('data-dragover', 'true');
      })
    );
    ['dragleave', 'drop'].forEach((evt) =>
      zone.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (evt === 'dragleave' && e.target !== zone) return;
        zone.setAttribute('data-dragover', 'false');
      })
    );
    zone.addEventListener('drop', (e) => {
      const file = e.dataTransfer.files && e.dataTransfer.files[0];
      if (file) handleFileSelect(file);
    });
    // Click anywhere on zone to open file picker
    zone.addEventListener('click', (e) => {
      if (e.target.closest('label[for="audioFile"]')) return; // label already triggers it
      dom.fileInput.click();
    });
  }

  // ---- Process (XHR with upload progress) ----
  function processAudio() {
    if (!state.selectedFile) {
      showError('请先选择音频文件');
      return;
    }
    if (state.isProcessing) return;

    state.isProcessing = true;
    state.lastResult = null;
    clearError();
    dom.processBtn.disabled = true;
    dom.processBtn.hidden = true;
    dom.cancelBtn.hidden = false;
    dom.resultSection.hidden = true;
    dom.progressSection.hidden = false;
    resetSteps();

    const fd = new FormData();
    fd.append('file', state.selectedFile);
    fd.append('template', state.selectedTemplate);

    const xhr = new XMLHttpRequest();
    state.xhr = xhr;

    // Stage 1: upload progress
    setStep(dom.stepUpload, 'active', '上传中…');
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        dom.uploadProgressBar.style.width = `${pct}%`;
        dom.uploadProgressLabel.textContent = `${pct}% · ${fmtSize(e.loaded)} / ${fmtSize(e.total)}`;
      }
    });
    xhr.upload.addEventListener('load', () => {
      setStep(dom.stepUpload, 'complete', '上传完成');
      dom.uploadProgressBar.style.width = '100%';
      dom.uploadProgressLabel.textContent = '100%';
      // Stage 2: transcribing (server-side)
      setStep(dom.stepTranscribe, 'active', '转录中…');
    });

    // Network stages
    xhr.addEventListener('loadstart', () => {
      dom.uploadProgressLabel.textContent = '准备中…';
    });

    xhr.addEventListener('load', () => {
      let result;
      try {
        result = JSON.parse(xhr.responseText);
      } catch (_e) {
        setStep(dom.stepSummarize, 'pending');
        setStep(dom.stepTranscribe, 'pending');
        finishProcessing(false, '服务器响应格式错误');
        return;
      }

      if (result.success) {
        setStep(dom.stepTranscribe, 'complete', '转录完成');
        setStep(dom.stepSummarize, 'complete', '总结完成');
        state.lastResult = result;
        renderResult(result);
        finishProcessing(true);
      } else {
        setStep(dom.stepSummarize, 'pending');
        finishProcessing(false, result.error || '处理失败');
      }
    });

    xhr.addEventListener('error', () => {
      finishProcessing(false, '网络错误，请检查连接后重试');
    });

    xhr.addEventListener('abort', () => {
      setStep(dom.stepUpload, 'pending', '已取消');
      dom.uploadProgressLabel.textContent = '已取消';
      if (window.toast) window.toast.info('处理已取消');
    });

    xhr.addEventListener('timeout', () => {
      finishProcessing(false, '请求超时');
    });

    xhr.timeout = 300000; // 5 min
    xhr.open('POST', '/process');
    xhr.send(fd);
  }

  function cancelProcess() {
    if (state.xhr) {
      state.xhr.abort();
      state.xhr = null;
    }
    state.isProcessing = false;
    dom.processBtn.disabled = false;
    dom.processBtn.hidden = false;
    dom.cancelBtn.hidden = true;
    dom.progressSection.hidden = true;
  }

  function finishProcessing(success, errorMsg) {
    state.isProcessing = false;
    state.xhr = null;
    dom.processBtn.disabled = false;
    dom.processBtn.hidden = false;
    dom.cancelBtn.hidden = true;

    if (!success) {
      dom.progressSection.hidden = true;
      showError(errorMsg || '处理失败');
      setStep(dom.stepSummarize, 'pending');
    } else {
      if (window.toast) window.toast.success('处理完成');
    }
  }

  // ---- Result rendering ----
  function renderResult(result) {
    dom.transcriptionText.textContent = result.transcription || '(无转录内容)';
    if (window.markdown && result.summary) {
      dom.summaryText.innerHTML = window.markdown.render(result.summary);
    } else {
      dom.summaryText.textContent = result.summary || '(无总结内容)';
    }

    // Download links (v2 API: use IDs)
    if (result.transcription_id) {
      dom.downloadTranscription.href = `/download/transcription/${result.transcription_id}`;
      dom.downloadTranscription.hidden = false;
    }
    if (result.summary_id) {
      dom.downloadSummary.href = `/download/summary/${result.summary_id}`;
      dom.downloadSummary.hidden = false;
    }
    // v2 does not generate ZIP files; hide the button
    dom.downloadZip.hidden = true;

    // Reset feedback state
    if (dom.feedbackSummary) {
      dom.feedbackButtons.forEach((b) => b.setAttribute('aria-pressed', 'false'));
    }

    dom.resultSection.hidden = false;
    dom.progressSection.hidden = true;

    // Switch to transcription tab by default
    switchTab('transcription');
    dom.resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function switchTab(name) {
    dom.tabButtons.forEach((btn) => {
      const selected = btn.getAttribute('data-tab') === name;
      btn.setAttribute('aria-selected', String(selected));
      btn.tabIndex = selected ? 0 : -1;
    });
    dom.tabPanels.forEach((panel) => {
      panel.hidden = panel.getAttribute('data-tab-panel') !== name;
    });
  }

  // ---- Actions ----
  async function copyToClipboard(text, label) {
    try {
      await navigator.clipboard.writeText(text);
      if (window.toast) window.toast.success(`${label}已复制到剪贴板`);
    } catch (_e) {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try {
        document.execCommand('copy');
        if (window.toast) window.toast.success(`${label}已复制`);
      } catch (_err) {
        if (window.toast) window.toast.error('复制失败');
      }
      ta.remove();
    }
  }

  // ---- Form submission (XHR with progress; native form post as fallback) ----
  function setupFormSubmission() {
    // Use form submit event to intercept; if JS fails, native form post still works
    if (!dom.form) return;
    dom.form.addEventListener('submit', (e) => {
      // Only intercept when we have a file and not yet processing
      if (!state.selectedFile) {
        // Let browser show native :invalid validation for required file input
        return;
      }
      if (state.isProcessing) {
        e.preventDefault();
        return;
      }
      // Prevent default native submission; we'll use XHR for progress
      e.preventDefault();
      processAudio();
    });

    // Fallback: direct click handler on the process button.
    // Some browser extensions or edge cases can swallow the form's submit event
    // (e.g. when the button is dragged by an inspector tool). Binding a click
    // handler directly on the button ensures the request is still fired.
    if (dom.processBtn) {
      dom.processBtn.addEventListener('click', (e) => {
        // If the click also triggers a form submit, the submit handler will run
        // processAudio() and the flag below will short-circuit this handler.
        if (e._maClickHandled) return;
        if (!state.selectedFile) {
          // Let the browser show native validation for the required file input
          return;
        }
        if (state.isProcessing) {
          e.preventDefault();
          return;
        }
        e._maClickHandled = true;
        e.preventDefault();
        processAudio();
      });
    }
  }

  function setupActions() {
    dom.fileInput.addEventListener('change', (e) => handleFileSelect(e.target.files[0]));
    dom.removeFile.addEventListener('click', removeFile);
    dom.cancelBtn.addEventListener('click', cancelProcess);

    dom.tabButtons.forEach((btn) => {
      btn.addEventListener('click', () => switchTab(btn.getAttribute('data-tab')));
      btn.addEventListener('keydown', (e) => {
        const tabs = Array.from(dom.tabButtons);
        const idx = tabs.indexOf(btn);
        if (e.key === 'ArrowRight') {
          e.preventDefault();
          tabs[(idx + 1) % tabs.length].focus();
        } else if (e.key === 'ArrowLeft') {
          e.preventDefault();
          tabs[(idx - 1 + tabs.length) % tabs.length].focus();
        }
      });
    });

    dom.copyTranscription.addEventListener('click', () => {
      if (state.lastResult) copyToClipboard(state.lastResult.transcription, '转录文本');
    });
    dom.copySummary.addEventListener('click', () => {
      if (state.lastResult) copyToClipboard(state.lastResult.summary, '总结内容');
    });

    if (dom.feedbackSummary) {
      dom.feedbackButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
          const vote = btn.getAttribute('data-vote');
          const wasPressed = btn.getAttribute('aria-pressed') === 'true';
          dom.feedbackButtons.forEach((b) => b.setAttribute('aria-pressed', 'false'));
          if (!wasPressed) {
            btn.setAttribute('aria-pressed', 'true');
            if (window.toast) window.toast.success(vote === 'up' ? '感谢您的反馈' : '已记录，我们会改进');
          }
        });
      });
    }
  }

  // ---- Init ----
  document.addEventListener('DOMContentLoaded', () => {
    renderTemplates();
    setupDragDrop();
    setupFormSubmission();
    setupActions();
  });
})();
