/**
 * Quote Generator – Module 4 (Testing, Error Handling & Polish)
 *
 * Handles UI interactions, communication with FastAPI backend,
 * automatic quote persistence, history loading, error handling with retries,
 * and status indicators.
 */

(function () {
  'use strict';

  // ── Configuration ───────────────────────────────────────
  const API_BASE = 'http://localhost:8000';

  // ── DOM References ──────────────────────────────────────
  const quoteText           = document.getElementById('quoteText');
  const quoteAuthor         = document.getElementById('quoteAuthor');
  const quoteErrorContainer = document.getElementById('quoteErrorContainer');
  const errorDetailText     = document.getElementById('errorDetailText');
  const retryBtn            = document.getElementById('retryBtn');
  const newQuoteBtn         = document.getElementById('newQuoteBtn');
  const copyQuoteBtn        = document.getElementById('copyQuoteBtn');
  const copyBtnLabel        = document.getElementById('copyBtnLabel');
  const toast               = document.getElementById('toast');
  const historyList         = document.getElementById('historyList');
  const historyEmpty        = document.getElementById('historyEmpty');
  const historyBadge        = document.getElementById('historyBadge');
  const backendStatusPill   = document.getElementById('backendStatusPill');

  // ── State ───────────────────────────────────────────────
  let currentQuote  = '';
  let currentAuthor = '';
  let isFetching    = false;
  let toastTimer    = null;

  // ── Toast helper with type support ──────────────────────
  function showToast(message, type = 'info', durationMs = 3000) {
    if (toastTimer) clearTimeout(toastTimer);

    toast.className = 'toast visible';
    if (type === 'error') {
      toast.classList.add('toast-error');
    } else if (type === 'success') {
      toast.classList.add('toast-success');
    } else {
      toast.classList.add('toast-info');
    }

    toast.textContent = message;

    toastTimer = setTimeout(() => {
      toast.classList.remove('visible');
    }, durationMs);
  }

  // ── Backend Connectivity Check ──────────────────────────
  async function checkBackendHealth() {
    try {
      const response = await fetch(`${API_BASE}/health`, { method: 'GET' });
      if (response.ok) {
        updateBackendStatus(true);
      } else {
        updateBackendStatus(false);
      }
    } catch {
      updateBackendStatus(false);
    }
  }

  function updateBackendStatus(isOnline) {
    if (!backendStatusPill) return;
    const textEl = backendStatusPill.querySelector('.status-text');
    if (isOnline) {
      backendStatusPill.classList.remove('offline');
      backendStatusPill.setAttribute('title', 'Backend & Database Connected');
      if (textEl) textEl.textContent = 'Connected';
    } else {
      backendStatusPill.classList.add('offline');
      backendStatusPill.setAttribute('title', 'Backend Offline – start uvicorn on port 8000');
      if (textEl) textEl.textContent = 'Offline';
    }
  }

  // ── User-friendly Error Parser ──────────────────────────
  function parseErrorMessage(err, status) {
    if (!navigator.onLine) {
      return 'You appear to be offline. Please verify your internet connection.';
    }

    if (err && err.name === 'TypeError' && err.message.includes('fetch')) {
      return 'Backend server is unreachable. Please verify FastAPI is running on port 8000.';
    }

    if (status === 504) {
      return 'The external quote service timed out. Please try again.';
    }

    if (status === 502) {
      return 'The external quote service is temporarily unreachable.';
    }

    if (status === 503) {
      return 'Database service is currently unavailable.';
    }

    if (status === 500) {
      return 'A server or database error occurred. Please try again.';
    }

    return err.message || 'Unable to load quote at this time.';
  }

  // ── Fetch Quote History from Database ───────────────────
  async function loadHistory() {
    try {
      const response = await fetch(`${API_BASE}/api/quotes/history`);
      if (!response.ok) {
        throw new Error(`History returned HTTP ${response.status}`);
      }
      const items = await response.json();
      window.quoteApp.setHistory(items);
      updateBackendStatus(true);
    } catch (err) {
      // Don't show toast on initial load failure to avoid intrusive banners,
      // but ensure empty state is displayed and status is updated
      updateBackendStatus(false);
      if (!currentQuote && historyList && historyEmpty) {
        historyEmpty.style.display = '';
      }
    }
  }

  // ── Fetch a random quote from the backend ───────────────
  async function fetchRandomQuote() {
    if (isFetching) return;
    isFetching = true;

    // Visual loading state
    newQuoteBtn.classList.add('loading');
    newQuoteBtn.disabled = true;

    // Hide previous error state
    if (quoteErrorContainer) {
      quoteErrorContainer.classList.add('hidden');
    }

    let responseStatus = null;

    try {
      const response = await fetch(`${API_BASE}/api/quotes/random`);
      responseStatus = response.status;

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const detail = errorData?.detail || `Server error (${response.status})`;
        throw new Error(detail);
      }

      const data = await response.json();

      if (!data || (!data.quote && !data.quote_text)) {
        throw new Error('Received an invalid or empty quote from server.');
      }

      // Display quote using standard setQuote
      const quoteTextVal = data.quote || data.quote_text || '';
      const authorVal = data.author || 'Unknown';
      window.quoteApp.setQuote(quoteTextVal, authorVal);

      updateBackendStatus(true);

      // Refresh quote history list
      await loadHistory();

    } catch (err) {
      const friendlyMessage = parseErrorMessage(err, responseStatus);

      quoteText.classList.add('fade-out');
      quoteAuthor.classList.add('fade-out');

      setTimeout(() => {
        quoteText.textContent = 'Could not load a quote.';
        quoteAuthor.textContent = '';
        currentQuote  = '';
        currentAuthor = '';

        if (errorDetailText) {
          errorDetailText.textContent = friendlyMessage;
        }
        if (quoteErrorContainer) {
          quoteErrorContainer.classList.remove('hidden');
        }

        quoteText.classList.remove('fade-out');
        quoteAuthor.classList.remove('fade-out');
      }, 200);

      showToast(`⚠ ${friendlyMessage}`, 'error', 4500);
      updateBackendStatus(false);

    } finally {
      setTimeout(() => {
        newQuoteBtn.classList.remove('loading');
        newQuoteBtn.disabled = false;
        isFetching = false;
      }, 300);
    }
  }

  // ── Event Listeners ─────────────────────────────────────
  newQuoteBtn.addEventListener('click', fetchRandomQuote);

  if (retryBtn) {
    retryBtn.addEventListener('click', fetchRandomQuote);
  }

  // ── Copy Quote ──────────────────────────────────────────
  copyQuoteBtn.addEventListener('click', async () => {
    if (!currentQuote) {
      showToast('Generate a quote first!', 'info');
      return;
    }

    const textToCopy = currentAuthor
      ? `"${currentQuote}" — ${currentAuthor}`
      : `"${currentQuote}"`;

    try {
      await navigator.clipboard.writeText(textToCopy);
      showCopiedState();
      showToast('✓ Copied quote to clipboard', 'success');
    } catch {
      fallbackCopy(textToCopy);
    }
  });

  function showCopiedState() {
    const copyIcon  = copyQuoteBtn.querySelector('.copy-icon');
    const checkIcon = copyQuoteBtn.querySelector('.check-icon');

    copyIcon.classList.add('hidden');
    checkIcon.classList.remove('hidden');
    copyBtnLabel.textContent = 'Copied!';
    copyQuoteBtn.classList.add('copied');

    setTimeout(() => {
      copyIcon.classList.remove('hidden');
      checkIcon.classList.add('hidden');
      copyBtnLabel.textContent = 'Copy Quote';
      copyQuoteBtn.classList.remove('copied');
    }, 2000);
  }

  function fallbackCopy(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity  = '0';
    textarea.style.pointerEvents = 'none';
    document.body.appendChild(textarea);
    textarea.select();

    try {
      const successful = document.execCommand('copy');
      if (successful) {
        showCopiedState();
        showToast('✓ Copied quote to clipboard', 'success');
      } else {
        showToast('Unable to copy – please copy manually', 'error');
      }
    } catch {
      showToast('Unable to copy – please copy manually', 'error');
    }

    document.body.removeChild(textarea);
  }

  // ── Public API ──────────────────────────────────────────
  window.quoteApp = {
    /**
     * Display a quote on the card.
     * @param {string} text   – The quote body.
     * @param {string} author – The author name.
     */
    setQuote(text, author) {
      currentQuote  = text;
      currentAuthor = author;

      // Hide any previous error container
      if (quoteErrorContainer) {
        quoteErrorContainer.classList.add('hidden');
      }

      quoteText.classList.add('fade-out');
      quoteAuthor.classList.add('fade-out');

      setTimeout(() => {
        quoteText.textContent   = `"${text}"`;
        quoteAuthor.textContent = author ? `— ${author}` : '';
        quoteText.classList.remove('fade-out');
        quoteAuthor.classList.remove('fade-out');
      }, 250);
    },

    /**
     * Render history items into the history list.
     * @param {Array<{text: string, quote?: string, quote_text?: string, author: string, created_at?: string}>} items
     */
    setHistory(items) {
      if (!historyList || !historyEmpty) return;

      if (!items || items.length === 0) {
        historyEmpty.style.display = '';
        if (historyBadge) {
          historyBadge.classList.add('hidden');
        }
        historyList.querySelectorAll('.history-item').forEach((el) => el.remove());
        return;
      }

      historyEmpty.style.display = 'none';

      // Update badge count
      if (historyBadge) {
        historyBadge.textContent = items.length;
        historyBadge.classList.remove('hidden');
      }

      historyList.querySelectorAll('.history-item').forEach((el) => el.remove());

      items.forEach((item) => {
        const text = item.text || item.quote_text || item.quote || '';
        const author = item.author || 'Unknown';
        const formattedDate = formatDate(item.created_at);

        const el = document.createElement('div');
        el.className = 'history-item';
        el.innerHTML = `
          <div class="history-item-content">
            <p class="history-item-quote">"${escapeHtml(text)}"</p>
            <div class="history-item-meta">
              <span class="history-item-author">— ${escapeHtml(author)}</span>
              ${formattedDate ? `<span class="history-item-date">• ${escapeHtml(formattedDate)}</span>` : ''}
            </div>
          </div>`;
        historyList.appendChild(el);
      });
    },

    /** Load and refresh history manually. */
    loadHistory,

    /** Show a toast notification with optional type ('info' | 'success' | 'error'). */
    showToast,

    /** Check health and update status pill. */
    checkBackendHealth,
  };

  /** Minimal HTML-escape helper */
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  /** Format ISO date string into readable time and date */
  function formatDate(isoStr) {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) return '';
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  }

  // ── Initial load ─────────────────────────────────────────
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      checkBackendHealth();
      loadHistory();
    });
  } else {
    checkBackendHealth();
    loadHistory();
  }
})();
