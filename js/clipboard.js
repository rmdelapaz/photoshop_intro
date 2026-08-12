/**
 * Copy to Clipboard — dark/light aware via CSS variables
 */
(function() {
    'use strict';

    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('pre code').forEach(function(codeBlock) {
            const wrapper = document.createElement('div');
            wrapper.className = 'code-block-wrapper';
            const pre = codeBlock.parentElement;
            pre.parentNode.insertBefore(wrapper, pre);
            wrapper.appendChild(pre);

            const btn = document.createElement('button');
            btn.className = 'copy-button';
            btn.textContent = 'Copy';
            btn.setAttribute('aria-label', 'Copy code to clipboard');
            wrapper.appendChild(btn);

            btn.addEventListener('click', function() {
                const text = codeBlock.textContent || codeBlock.innerText;
                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(text)
                        .then(() => feedback(btn, true))
                        .catch(() => fallback(text, btn));
                } else {
                    fallback(text, btn);
                }
            });
        });
    });

    function fallback(text, btn) {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;opacity:0;';
        document.body.appendChild(ta);
        ta.focus(); ta.select();
        try { feedback(btn, document.execCommand('copy')); }
        catch (_) { feedback(btn, false); }
        document.body.removeChild(ta);
    }

    function feedback(btn, ok) {
        const orig = btn.textContent;
        btn.textContent = ok ? '✓ Copied!' : '✗ Failed';
        btn.classList.add(ok ? 'copy-ok' : 'copy-fail');
        setTimeout(() => {
            btn.textContent = orig;
            btn.classList.remove('copy-ok', 'copy-fail');
        }, 2000);
    }

    // Inject styles using CSS variables
    const s = document.createElement('style');
    s.textContent = `
        .code-block-wrapper { position: relative; margin: 1em 0; }
        .code-block-wrapper pre { padding-right: 70px; margin: 0; }
        .copy-button {
            position: absolute;
            top: 8px;
            right: 8px;
            padding: 4px 10px;
            background: var(--text-light, #64748b);
            color: #fff;
            border: none;
            border-radius: 4px;
            font-size: 0.75rem;
            cursor: pointer;
            opacity: 0.7;
            transition: opacity 0.2s, background-color 0.2s;
            z-index: 10;
        }
        .copy-button:hover { opacity: 1; background: var(--primary-color, #3b82f6); transform: none; box-shadow: none; }
        .copy-button.copy-ok { background: var(--success-border, #22c55e); opacity: 1; }
        .copy-button.copy-fail { background: var(--danger-border, #ef4444); opacity: 1; }
        @media print { .copy-button { display: none; } }
    `;
    document.head.appendChild(s);
})();
