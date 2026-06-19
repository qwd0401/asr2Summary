/**
 * Minimal Markdown renderer
 * - Supports headings, bold, italic, code, lists, paragraphs
 * - Used to render meeting summaries server-rendered as Markdown text
 */
(function () {
  'use strict';

  function escapeHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function renderInline(text) {
    let s = escapeHtml(text);
    // Bold **...**
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // Italic *...*
    s = s.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
    // Inline code `...`
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    // Bold label patterns like **会议类型**：
    s = s.replace(/<strong>([^<]+)<\/strong>：/g, '<strong>$1</strong>：');
    return s;
  }

  function render(markdown) {
    if (!markdown) return '';
    const lines = markdown.split(/\r?\n/);
    const out = [];
    let para = [];
    let inList = false;
    let listType = null;

    function flushPara() {
      if (para.length) {
        out.push(`<p>${renderInline(para.join(' '))}</p>`);
        para = [];
      }
    }
    function closeList() {
      if (inList) {
        out.push(`</${listType}>`);
        inList = false;
        listType = null;
      }
    }

    for (let i = 0; i < lines.length; i++) {
      const raw = lines[i];
      const line = raw.trim();
      if (!line) {
        flushPara();
        closeList();
        continue;
      }

      // Headings
      const h = line.match(/^(#{1,4})\s+(.+)$/);
      if (h) {
        flushPara();
        closeList();
        out.push(`<h${h[1].length}>${renderInline(h[2])}</h${h[1].length}>`);
        continue;
      }

      // Unordered list
      const ul = line.match(/^[-*]\s+(.+)$/);
      if (ul) {
        flushPara();
        if (!inList) {
          out.push('<ul>');
          inList = true;
          listType = 'ul';
        } else if (listType !== 'ul') {
          closeList();
          out.push('<ul>');
          inList = true;
          listType = 'ul';
        }
        out.push(`<li>${renderInline(ul[1])}</li>`);
        continue;
      }

      // Ordered list
      const ol = line.match(/^\d+\.\s+(.+)$/);
      if (ol) {
        flushPara();
        if (!inList) {
          out.push('<ol>');
          inList = true;
          listType = 'ol';
        } else if (listType !== 'ol') {
          closeList();
          out.push('<ol>');
          inList = true;
          listType = 'ol';
        }
        out.push(`<li>${renderInline(ol[1])}</li>`);
        continue;
      }

      closeList();
      para.push(line);
    }

    flushPara();
    closeList();
    return out.join('\n');
  }

  window.markdown = { render };
})();
