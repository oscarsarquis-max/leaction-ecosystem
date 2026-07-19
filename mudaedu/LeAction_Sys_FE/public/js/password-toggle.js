(function (global) {
    'use strict';

    function setInputType(input, type) {
        try {
            input.type = type;
        } catch (e) { /* IE legado */ }
        input.setAttribute('type', type);
    }

    function bindToggle(input, btn) {
        if (!input || !btn) return;

        var visible = false;

        function renderIcon() {
            btn.innerHTML = '<i class="fas fa-' + (visible ? 'eye-slash' : 'eye') + '"></i>';
            btn.setAttribute('aria-label', visible ? 'Ocultar' : 'Mostrar');
            btn.setAttribute('title', visible ? 'Ocultar' : 'Mostrar');
        }

        function applyVisibility(show) {
            visible = !!show;
            if (input.dataset.pwdMasked === '1') {
                if (visible) {
                    setInputType(input, 'text');
                    input.value = input.dataset.pwdPlain || '';
                    input.readOnly = true;
                } else {
                    setInputType(input, 'password');
                    input.value = input.dataset.pwdDisplay || '••••••••';
                    input.readOnly = true;
                }
            } else {
                setInputType(input, visible ? 'text' : 'password');
            }
            renderIcon();
        }

        btn.replaceWith(btn.cloneNode(true));
        btn = input.parentNode.querySelector('.pwd-field__toggle');
        btn.addEventListener('mousedown', function (e) {
            e.preventDefault();
        });
        btn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            applyVisibility(!visible);
        });

        renderIcon();
        input._pwdToggleApply = applyVisibility;
    }

    function wrapInput(input) {
        if (!input) return null;
        var existing = input.closest('.pwd-field');
        if (existing) {
            var existingBtn = existing.querySelector('.pwd-field__toggle');
            if (existingBtn) bindToggle(input, existingBtn);
            return existing;
        }

        var wrap = document.createElement('div');
        wrap.className = 'pwd-field';
        if (input.id === 'h-credential') wrap.classList.add('pwd-field--header');

        var parent = input.parentNode;
        parent.insertBefore(wrap, input);
        wrap.appendChild(input);
        input.classList.add('pwd-field__input');

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'pwd-field__toggle';
        wrap.appendChild(btn);

        bindToggle(input, btn);
        return wrap;
    }

    function setMaskedValue(input, plainValue) {
        if (!input) return;
        var v = String(plainValue || '');
        wrapInput(input);
        input.dataset.pwdMasked = '1';
        input.dataset.pwdPlain = v;
        input.dataset.pwdDisplay = v ? '•'.repeat(Math.min(Math.max(v.length, 8), 12)) : '••••••••';
        input.readOnly = true;
        setInputType(input, 'password');
        input.value = input.dataset.pwdDisplay;
        if (typeof input._pwdToggleApply === 'function') {
            input._pwdToggleApply(false);
        }
    }

    function clearMasked(input) {
        if (!input) return;
        delete input.dataset.pwdMasked;
        delete input.dataset.pwdPlain;
        delete input.dataset.pwdDisplay;
        input.readOnly = false;
        input.value = '';
        setInputType(input, 'password');
        if (typeof input._pwdToggleApply === 'function') {
            input._pwdToggleApply(false);
        }
    }

    function init(root) {
        var scope = root || document;
        scope.querySelectorAll('input[data-pwd-toggle]').forEach(function (input) {
            wrapInput(input);
        });
    }

    global.MudaEduPasswordToggle = {
        init: init,
        wrap: wrapInput,
        setMaskedValue: setMaskedValue,
        clearMasked: clearMasked
    };
    global.PanelDXPasswordToggle = global.MudaEduPasswordToggle;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { init(document); });
    } else {
        init(document);
    }
})(window);
