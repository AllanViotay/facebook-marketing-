(function() {
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => Array.from(document.querySelectorAll(sel));

    const adForm = $('#ad-form');
    const advForm = $('#advanced-form');
    const resultDiv = $('#result');
    const resultsCard = $('#results-card');
    const backdrop = $('#backdrop');
    const toast = $('#toast');
    const copyBtn = $('#copy-result-btn');
    const clearBtn = $('#clear-btn');
    const formatBtn = $('#format-json-btn');

    let lastResponse = null;

    // Tabs
    $$('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            $$('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const target = tab.dataset.tab;
            $$('.tab-content').forEach(c => {
                const isActive = c.id === `tab-${target}`;
                c.classList.toggle('active', isActive);
                c.setAttribute('aria-hidden', String(!isActive));
            });
        });
    });

    function showSpinner(show) {
        if (show) {
            backdrop.removeAttribute('hidden');
        } else {
            backdrop.setAttribute('hidden', '');
        }
    }

    function showToast(message) {
        toast.textContent = message;
        toast.removeAttribute('hidden');
        setTimeout(() => { toast.setAttribute('hidden', ''); }, 2200);
    }

    function renderResult(data) {
        resultsCard.removeAttribute('hidden');
        lastResponse = data;
        try {
            const pretty = JSON.stringify(data, null, 2);
            resultDiv.textContent = pretty;
        } catch (e) {
            resultDiv.textContent = String(data);
        }
    }

    async function postJSON(url, payload) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }

    // Basic form: AI + create
    if (adForm) {
        adForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const description = $('#ad-description').value.trim();
            if (!description) {
                showToast('Please enter a description');
                return;
            }
            showSpinner(true);
            resultsCard.setAttribute('hidden', '');
            resultDiv.textContent = 'Working...';
            try {
                const data = await postJSON('/api/create-ad', { description });
                renderResult(data);
            } catch (err) {
                renderResult({ error: err.message });
            } finally {
                showSpinner(false);
            }
        });
    }

    // Advanced form: direct payload
    if (advForm) {
        advForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const raw = $('#advanced-json').value.trim();
            if (!raw) {
                showToast('Paste a JSON payload');
                return;
            }
            let payload = null;
            try {
                payload = JSON.parse(raw);
            } catch (e) {
                showToast('Invalid JSON');
                return;
            }
            showSpinner(true);
            resultsCard.setAttribute('hidden', '');
            resultDiv.textContent = 'Working...';
            try {
                const data = await postJSON('/api/create-ad-advanced', payload);
                renderResult(data);
            } catch (err) {
                renderResult({ error: err.message });
            } finally {
                showSpinner(false);
            }
        });
    }

    // Utilities
    if (copyBtn) {
        copyBtn.addEventListener('click', async () => {
            if (!lastResponse) return;
            try {
                await navigator.clipboard.writeText(JSON.stringify(lastResponse, null, 2));
                showToast('Copied');
            } catch (e) {
                showToast('Copy failed');
            }
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            const ta = $('#ad-description');
            if (ta) ta.value = '';
            resultsCard.setAttribute('hidden', '');
            resultDiv.textContent = '';
        });
    }

    if (formatBtn) {
        formatBtn.addEventListener('click', () => {
            const ta = $('#advanced-json');
            if (!ta || !ta.value.trim()) return;
            try {
                const obj = JSON.parse(ta.value);
                ta.value = JSON.stringify(obj, null, 2);
                showToast('Formatted');
            } catch (e) {
                showToast('Invalid JSON');
            }
        });
    }
})();
