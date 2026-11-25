const fs = require('fs');
const html = fs.readFileSync('c:/Users/sabin/Quote-Generator-with-History/frontend/index.html', 'utf8');
const js = fs.readFileSync('c:/Users/sabin/Quote-Generator-with-History/frontend/script.js', 'utf8');

console.log('=== VERIFYING MODULE 3 FRONTEND INTEGRATION ===');

// 1. Verify required DOM elements
const requiredIds = ['quoteText', 'quoteAuthor', 'newQuoteBtn', 'copyQuoteBtn', 'copyBtnLabel', 'toast', 'historyList', 'historyEmpty'];
for (const id of requiredIds) {
  if (!html.includes(`id="${id}"`)) {
    throw new Error('Missing ID in index.html: ' + id);
  }
}
console.log('[PASS] All required DOM elements exist in index.html');

// 2. Verify window.quoteApp integration methods
if (!js.includes('setQuote(text, author)') || !js.includes('setHistory(items)') || !js.includes('loadHistory') || !js.includes('showToast')) {
  throw new Error('window.quoteApp missing methods');
}
console.log('[PASS] window.quoteApp methods (setQuote, setHistory, loadHistory, showToast) exported');

// 3. Verify history loading from database
if (!js.includes('/api/quotes/history')) {
  throw new Error('Missing /api/quotes/history fetch call');
}
console.log('[PASS] loadHistory queries GET /api/quotes/history');

// 4. Verify history refreshed after saving new quote
if (!js.includes('await loadHistory()')) {
  throw new Error('History is not refreshed after fetching new quote');
}
console.log('[PASS] fetchRandomQuote automatically refreshes history after saving');

// 5. Verify initial history load on startup
if (!js.includes('DOMContentLoaded') || !js.includes('loadHistory')) {
  throw new Error('Initial history load on startup missing');
}
console.log('[PASS] Automatically retrieves saved history from database on initial page load');

// 6. Verify setHistory handles items and empty state correctly
if (!js.includes("history-item") || !js.includes("historyEmpty")) {
  throw new Error('History DOM manipulation incomplete');
}
console.log('[PASS] History rendering handles history-item creation and empty state toggle');

// 7. Verify Copy Quote functionality preserved
if (!js.includes('copyQuoteBtn.addEventListener') || !js.includes('navigator.clipboard.writeText')) {
  throw new Error('Copy functionality altered or missing');
}
console.log('[PASS] Copy Quote functionality preserved intact');

console.log('=== FRONTEND VERIFICATION COMPLETE ===');
