(function () {
    'use strict';

    var STORAGE_KEY = 'sidebarState';
    var WIDTH_EXPANDED = '260px';
    var WIDTH_COLLAPSED = '70px';

    function getSidebar() {
        return document.getElementById('sidebar-menu');
    }

    function getContent() {
        return document.querySelector('main .content');
    }

    function getContextInner() {
        return document.querySelector('.context-bar__inner');
    }

    function getToggles() {
        return Array.prototype.slice.call(document.querySelectorAll('[data-sidebar-toggle]'));
    }

    function isCollapsed() {
        return document.body.classList.contains('sidebar-collapsed');
    }

    function applySidebarState(collapsed) {
        var sidebar = getSidebar();
        var content = getContent();
        var contextInner = getContextInner();

        document.body.classList.toggle('sidebar-collapsed', collapsed);

        if (sidebar) {
            sidebar.classList.toggle('is-collapsed', collapsed);
            if (collapsed) {
                sidebar.style.setProperty('width', WIDTH_COLLAPSED, 'important');
                sidebar.style.setProperty('max-width', WIDTH_COLLAPSED, 'important');
            } else {
                sidebar.style.removeProperty('width');
                sidebar.style.removeProperty('max-width');
            }
        }

        if (content) {
            if (collapsed) {
                content.style.setProperty('margin-left', WIDTH_COLLAPSED, 'important');
            } else {
                content.style.removeProperty('margin-left');
            }
        }

        if (contextInner) {
            if (collapsed) {
                contextInner.style.setProperty('margin-left', WIDTH_COLLAPSED, 'important');
            } else {
                contextInner.style.removeProperty('margin-left');
            }
        }

        getToggles().forEach(function (btn) {
            btn.setAttribute('aria-label', collapsed ? 'Expandir menu lateral' : 'Recolher menu lateral');
            btn.title = collapsed ? 'Expandir menu' : 'Recolher menu';
            btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        });

        try {
            localStorage.setItem(STORAGE_KEY, collapsed ? 'collapsed' : 'expanded');
        } catch (e) { /* ignore */ }

        if (collapsed) {
            document.querySelectorAll('#sidebar-menu .menu-item.is-open').forEach(function (item) {
                item.classList.remove('is-open');
                var trigger = item.querySelector(':scope > a.submenu-toggle');
                if (trigger) trigger.setAttribute('aria-expanded', 'false');
            });
        }
    }

    function restoreSidebarState() {
        try {
            if (localStorage.getItem(STORAGE_KEY) === 'collapsed') {
                applySidebarState(true);
            }
        } catch (e) { /* ignore */ }
    }

    function bindSidebarToggle() {
        getToggles().forEach(function (btn) {
            if (btn.dataset.sidebarBound === '1') return;
            btn.dataset.sidebarBound = '1';
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                applySidebarState(!isCollapsed());
            });
        });
    }

    function init() {
        restoreSidebarState();
        bindSidebarToggle();
    }

    window.MudaEduSidebar = {
        toggle: function () { applySidebarState(!isCollapsed()); },
        collapse: function () { applySidebarState(true); },
        expand: function () { applySidebarState(false); }
    };
    window.PanelDXSidebar = window.MudaEduSidebar;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
