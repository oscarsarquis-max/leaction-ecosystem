(function () {
    'use strict';

    function normalizePath(path) {
        if (!path || path === '#') return '';
        var p = path.split('?')[0].split('#')[0];
        if (p.length > 1 && p.endsWith('/')) p = p.slice(0, -1);
        return p;
    }

    function pathMatchesCurrent(linkPath, currentPath) {
        if (!linkPath) return false;
        if (linkPath === currentPath) return true;
        if (currentPath.indexOf(linkPath + '/') === 0) return true;
        return false;
    }

    function closeSiblingMenus(item) {
        var parentUl = item.parentElement;
        if (!parentUl) return;
        parentUl.querySelectorAll(':scope > .menu-item.is-open').forEach(function (openItem) {
            if (openItem !== item) openItem.classList.remove('is-open');
        });
    }

    function ensureChevron(trigger) {
        if (trigger.querySelector('.submenu-chevron')) return;
        var chevron = document.createElement('i');
        chevron.className = 'fas fa-chevron-down submenu-chevron';
        chevron.setAttribute('aria-hidden', 'true');
        trigger.appendChild(chevron);
    }

    function initSubmenus() {
        var sidebar = document.getElementById('sidebar-menu');
        if (!sidebar) return;

        var currentPath = normalizePath(window.location.pathname);

        sidebar.querySelectorAll('.menu-item').forEach(function (item) {
            var submenu = item.querySelector(':scope > .submenu');
            var trigger = item.querySelector(':scope > a.submenu-toggle');
            if (!submenu || !trigger) return;

            item.classList.add('has-children');
            ensureChevron(trigger);

            trigger.setAttribute('role', 'button');
            trigger.setAttribute('aria-expanded', 'false');

            trigger.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();

                var willOpen = !item.classList.contains('is-open');
                closeSiblingMenus(item);
                item.classList.toggle('is-open', willOpen);
                trigger.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
            });

            submenu.querySelectorAll('a[href]').forEach(function (link) {
                var href = normalizePath(link.getAttribute('href'));
                if (pathMatchesCurrent(href, currentPath)) {
                    item.classList.add('is-open');
                    trigger.setAttribute('aria-expanded', 'true');
                }
            });
        });
    }

    window.PanelDXSidebarSubmenu = {
        closeAll: function () {
            document.querySelectorAll('#sidebar-menu .menu-item.is-open').forEach(function (item) {
                item.classList.remove('is-open');
                var trigger = item.querySelector(':scope > a.submenu-toggle');
                if (trigger) trigger.setAttribute('aria-expanded', 'false');
            });
        },
        init: initSubmenus
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSubmenus);
    } else {
        initSubmenus();
    }
})();
