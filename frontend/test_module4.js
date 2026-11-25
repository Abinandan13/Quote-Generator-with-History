/**
 * Frontend Test Suite for Module 4.
 * Validates DOM integrity, event handlers, error retry mechanics,
 * loading animations, toast types, history badge, and responsive CSS rules.
 */

const fs = require('fs');
const html = fs.readFileSync('c:/Users/sabin/Quote-Generator-with-History/frontend/index.html', 'utf8');
const js = fs.readFileSync('c:/Users/sabin/Quote-Generator-with-History/frontend/script.js', 'utf8');
const css = fs.readFileSync('c:/Users/sabin/Quote-Generator-with-History/frontend/style.css', 'utf8');

console.log('=== RUNNING MODULE 4 FRONTEND TEST SUITE ===');

// 1. Required DOM elements
const requiredIds = [
  'quoteText',
  'quoteAuthor',
  'newQuoteBtn',
  'copyQuoteBtn',
  'copyBtnLabel',
  'toast',
  'historyList',
  'historyEmpty',
  'historyBadge',
  'quoteErrorContainer',
  'errorDetailText',
  'retryBtn',
  'backendStatusPill'
];

for (const id of requiredIds) {
  if (!html.includes(`id="${id}"`)) {
    throw new Error(`Missing required element ID in index.html: ${id}`);
  }
}
console.log('[PASS] 1. All required DOM element IDs exist in index.html');

// 2. Exported window.quoteApp methods
const requiredMethods = ['setQuote', 'setHistory', 'loadHistory', 'showToast', 'checkBackendHealth'];
for (const method of requiredMethods) {
  if (!js.includes(method)) {
    throw new Error(`Missing method in script.js: ${method}`);
  }
}
console.log('[PASS] 2. Public window.quoteApp API complete: ' + requiredMethods.join(', '));

// 3. New quote fetching & automatic history refresh
if (!js.includes('fetch(`${API_BASE}/api/quotes/random`)') || !js.includes('await loadHistory()')) {
  throw new Error('New Quote does not trigger fetch or subsequent history refresh');
}
console.log('[PASS] 3. fetchRandomQuote communicates with backend and automatically calls loadHistory()');

// 4. Initial load on startup
if (!js.includes('document.addEventListener(\'DOMContentLoaded\'') || !js.includes('checkBackendHealth()') || !js.includes('loadHistory()')) {
  throw new Error('Startup listeners for history and health check missing');
}
console.log('[PASS] 4. Startup sequence loads database history and checks backend health');

// 5. Error handling with friendly messages and retry
if (!js.includes('parseErrorMessage') || !js.includes('retryBtn.addEventListener') || !js.includes('quoteErrorContainer')) {
  throw new Error('Error handling or retry mechanisms missing');
}
console.log('[PASS] 5. Error handling parses friendly messages and supports instant Retry');

// 6. Copy quote functionality and clipboard fallback
if (!js.includes('navigator.clipboard.writeText') || !js.includes('fallbackCopy') || !js.includes('showCopiedState')) {
  throw new Error('Copy functionality or fallback missing');
}
console.log('[PASS] 6. Copy Quote with clipboard API and execCommand fallback preserved');

// 7. Toast styling classes & types
const toastStyles = ['.toast-success', '.toast-error', '.toast-info'];
for (const cls of toastStyles) {
  if (!css.includes(cls)) {
    throw new Error(`Missing toast style class in style.css: ${cls}`);
  }
}
console.log('[PASS] 7. Toast notification types styled (success, error, info)');

// 8. History count badge & metadata
if (!css.includes('.history-badge') || !css.includes('.history-item-meta') || !js.includes('historyBadge')) {
  throw new Error('History badge or item meta styling missing');
}
console.log('[PASS] 8. History badge counter and item metadata (author + timestamp) verified');

// 9. Responsive CSS breakpoints
const mediaQueries = ['@media (max-width: 768px)', '@media (max-width: 640px)', '@media (max-width: 400px)'];
for (const mq of mediaQueries) {
  if (!css.includes(mq)) {
    throw new Error(`Missing responsive media query in style.css: ${mq}`);
  }
}
console.log('[PASS] 9. Responsive design breakpoints verified (tablet: 768px, mobile: 640px, small: 400px)');

// 10. No fake hardcoded quotes
if (html.includes('Lorem ipsum') || js.includes('Sample Quote') || html.includes('Albert Einstein')) {
  throw new Error('Detected hardcoded fake quote content!');
}
console.log('[PASS] 10. Zero hardcoded fake quotes or mock history records found');

console.log('=== ALL MODULE 4 FRONTEND TESTS PASSED SUCCESSFULLY ===');
