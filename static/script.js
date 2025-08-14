(function() {
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => Array.from(document.querySelectorAll(sel));

    const adForm = $('#ad-form');
    const advForm = $('#advanced-form');
    const insightsForm = $('#insights-form');
    const resultDiv = $('#result');
    const resultsCard = $('#results-card');
    const backdrop = $('#backdrop');
    const toast = $('#toast');
    const copyBtn = $('#copy-result-btn');
    const clearBtn = $('#clear-btn');
    const formatBtn = $('#format-json-btn');
    const aiCopyBtn = $('#ai-copy-btn');
    const aiImageBtn = $('#ai-image-btn');
    const voiceBtn = $('#voice-btn');

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
        if (show) backdrop.hidden = !show;
        else backdrop.hidden = true;
    }

    function showToast(message) {
        toast.textContent = message;
        toast.hidden = false;
        setTimeout(() => { toast.hidden = true; }, 2200);
    }

    function renderResult(data) {
        resultsCard.hidden = false;
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
            if (!description) { showToast('Please enter a description'); return; }
            showSpinner(true);
            resultsCard.hidden = true;
            resultDiv.textContent = 'Working...';
            try {
                const data = await postJSON('/api/create-ad', { description });
                renderResult(data);
            } catch (err) {
                renderResult({ error: err.message });
            } finally { showSpinner(false); }
        });
    }

    // Advanced form: direct payload
    if (advForm) {
        advForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const raw = $('#advanced-json').value.trim();
            if (!raw) { showToast('Paste a JSON payload'); return; }
            let payload = null;
            try { payload = JSON.parse(raw); } catch (e) { showToast('Invalid JSON'); return; }
            showSpinner(true);
            resultsCard.hidden = true;
            resultDiv.textContent = 'Working...';
            try {
                const data = await postJSON('/api/create-ad-advanced', payload);
                renderResult(data);
            } catch (err) {
                renderResult({ error: err.message });
            } finally { showSpinner(false); }
        });
    }

    // Insights form: analyze & suggest copy
    if (insightsForm) {
        insightsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const level = $('#insights-level').value;
            const ids = ($('#insights-ids').value || '').split(',').map(s => s.trim()).filter(Boolean);
            const date_preset = $('#insights-preset').value;
            showSpinner(true);
            try {
                const data = await postJSON('/api/ai/insights-suggest', { fetch: { level, ids, date_preset } });
                renderResult(data);
            } catch (err) {
                renderResult({ error: err.message });
            } finally { showSpinner(false); }
        });
    }

    // AI Copy button
    if (aiCopyBtn) {
        aiCopyBtn.addEventListener('click', async () => {
            const brief = $('#ad-description').value.trim();
            if (!brief) { showToast('Enter a brief first'); return; }
            showSpinner(true);
            try {
                const data = await postJSON('/api/ai/copy', { prompt: brief });
                renderResult(data);
                const copy = data?.result?.text;
                if (copy) {
                    // Also inject into advanced JSON if present
                    const adv = $('#advanced-json');
                    if (adv && adv.value.trim()) {
                        try {
                            const obj = JSON.parse(adv.value);
                            obj.ad_copy = copy;
                            adv.value = JSON.stringify(obj, null, 2);
                        } catch {}
                    }
                }
            } catch (e) {
                renderResult({ error: e.message });
            } finally { showSpinner(false); }
        });
    }

    // AI Image button
    if (aiImageBtn) {
        aiImageBtn.addEventListener('click', async () => {
            const brief = $('#ad-description').value.trim();
            if (!brief) { showToast('Enter a brief first'); return; }
            showSpinner(true);
            try {
                const data = await postJSON('/api/ai/image', { prompt: brief, size: '1024x1024', n: 1 });
                renderResult(data);
                // Just inform user how to use base64 in advanced payload
                showToast('Image (base64) ready in response. Add as image_base64 in advanced payload.');
            } catch (e) {
                renderResult({ error: e.message });
            } finally { showSpinner(false); }
        });
    }

    // Voice input (Web Speech API)
    if (voiceBtn && 'webkitSpeechRecognition' in window) {
        const rec = new window.webkitSpeechRecognition();
        rec.continuous = false;
        rec.interimResults = true;
        rec.lang = 'en-US';
        let collecting = false;

        voiceBtn.addEventListener('click', () => {
            if (!collecting) {
                rec.start(); collecting = true; voiceBtn.textContent = '⏹ Stop';
            } else {
                rec.stop(); collecting = false; voiceBtn.textContent = '🎤 Voice';
            }
        });
        rec.onresult = (ev) => {
            let txt = '';
            for (let i=0; i<ev.results.length; i++) {
                const res = ev.results[i];
                if (res.isFinal) txt += res[0].transcript;
            }
            if (txt) {
                const ta = $('#ad-description');
                ta.value = (ta.value ? ta.value + ' ' : '') + txt.trim();
            }
        };
        rec.onend = () => { collecting = false; voiceBtn.textContent = '🎤 Voice'; };
    } else if (voiceBtn) {
        voiceBtn.addEventListener('click', () => showToast('Voice not supported in this browser'));
    }

    // Utilities
    if (copyBtn) {
        copyBtn.addEventListener('click', async () => {
            if (!lastResponse) return;
            try {
                await navigator.clipboard.writeText(JSON.stringify(lastResponse, null, 2));
                showToast('Copied');
            } catch (e) { showToast('Copy failed'); }
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            const ta = $('#ad-description'); if (ta) ta.value = '';
            resultsCard.hidden = true; resultDiv.textContent = '';
        });
    }

    if (formatBtn) {
        formatBtn.addEventListener('click', () => {
            const ta = $('#advanced-json'); if (!ta || !ta.value.trim()) return;
            try { const obj = JSON.parse(ta.value); ta.value = JSON.stringify(obj, null, 2); showToast('Formatted'); }
            catch { showToast('Invalid JSON'); }
        });
    }
})();
