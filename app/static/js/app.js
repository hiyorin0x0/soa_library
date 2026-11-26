/**
 * LibCore Smooth Navigation Engine (PJAX + View Transitions) & Command Palette
 */
(function () {
    'use strict';

    const activeCharts = new Set();
    let navAbortController = null;

    window.LibCore = {
        registerChart(chart) {
            if (chart) activeCharts.add(chart);
            return chart;
        },
        destroyCharts() {
            activeCharts.forEach(c => {
                try { c.destroy(); } catch (_) {}
            });
            activeCharts.clear();
        },
    };

    function progressStart() {
        const bar = document.getElementById('navProgress');
        if (!bar) return;
        bar.style.transition = 'none';
        bar.style.width = '0%';
        bar.classList.add('is-active');
        requestAnimationFrame(() => {
            bar.style.transition = 'width 0.35s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.2s ease';
            bar.style.width = '72%';
        });
    }

    function progressDone() {
        const bar = document.getElementById('navProgress');
        if (!bar) return;
        bar.style.width = '100%';
        setTimeout(() => {
            bar.classList.remove('is-active');
            setTimeout(() => { bar.style.width = '0%'; }, 200);
        }, 160);
    }

    function closeMobileDrawer() {
        document.getElementById('sidebar')?.classList.remove('show');
        document.getElementById('sidebarBackdrop')?.classList.remove('show');
    }

    function autoDismissAlerts(root = document) {
        setTimeout(() => {
            root.querySelectorAll('.alert-dismissible').forEach(el => {
                try { bootstrap.Alert.getOrCreateInstance(el).close(); } catch (_) {}
            });
        }, 5500);
    }

    function animateNumbers(root = document) {
        root.querySelectorAll('[data-count]').forEach(el => {
            const target = parseInt(el.getAttribute('data-count'), 10);
            if (isNaN(target) || target <= 0) return;
            const duration = 360;
            const start = performance.now();
            function tick(now) {
                const p = Math.min(1, (now - start) / duration);
                const eased = 1 - Math.pow(1 - p, 3);
                el.textContent = Math.round(target * eased).toLocaleString('vi-VN');
                if (p < 1) requestAnimationFrame(tick);
                else el.textContent = target.toLocaleString('vi-VN');
            }
            requestAnimationFrame(tick);
        });
    }

    function runPageScripts(container) {
        container.querySelectorAll('script[data-page-script]').forEach(oldScript => {
            const fresh = document.createElement('script');
            Array.from(oldScript.attributes).forEach(attr => fresh.setAttribute(attr.name, attr.value));
            fresh.textContent = oldScript.textContent;
            oldScript.replaceWith(fresh);
        });
    }

    function syncNavigationState(nextDoc, targetUrl) {
        document.title = nextDoc.title;

        const curTopTitle = document.getElementById('topbarTitle');
        const nextTopTitle = nextDoc.getElementById('topbarTitle');
        if (curTopTitle && nextTopTitle) {
            curTopTitle.textContent = nextTopTitle.textContent;
        }

        const path = new URL(targetUrl, window.location.origin).pathname;
        document.querySelectorAll('#sidebar .sidebar-link, #mobileTabBar .mob-tab, .opac-navbar .nav-link').forEach(link => {
            const href = link.getAttribute('href');
            if (!href) return;
            const linkPath = new URL(href, window.location.origin).pathname;
            const nextEquivalent = nextDoc.querySelector(`a[href="${href}"].sidebar-link, a[href="${href}"].mob-tab, .opac-navbar a[href="${href}"].nav-link`);
            if (nextEquivalent) {
                link.classList.toggle('active', nextEquivalent.classList.contains('active'));
            } else {
                link.classList.toggle('active', linkPath === path);
            }
        });
    }

    async function smoothNavigate(url, push = true) {
        const currentShell = document.body.dataset.shell || '';
        if (navAbortController) navAbortController.abort();
        navAbortController = new AbortController();

        progressStart();
        closeMobileDrawer();

        try {
            const response = await fetch(url, {
                headers: { 'X-Requested-With': 'LibCorePJAX' },
                signal: navAbortController.signal,
                credentials: 'same-origin',
            });

            if (response.redirected && new URL(response.url).pathname === '/login') {
                window.location.href = response.url;
                return;
            }
            const contentType = response.headers.get('Content-Type') || '';
            if (!response.ok || !contentType.includes('text/html')) {
                window.location.href = url;
                return;
            }

            const html = await response.text();
            const parser = new DOMParser();
            const nextDoc = parser.parseFromString(html, 'text/html');
            const nextShell = nextDoc.body.dataset.shell || '';
            const curViewport = document.getElementById('pageViewport');
            const nextViewport = nextDoc.getElementById('pageViewport');

            if (!curViewport || !nextViewport || currentShell !== nextShell) {
                window.location.href = response.url || url;
                return;
            }

            const performSwap = () => {
                window.LibCore.destroyCharts();
                document.querySelectorAll('#topbar [data-bs-toggle="dropdown"]').forEach(btn => {
                    try { bootstrap.Dropdown.getInstance(btn)?.hide(); } catch (_) {}
                });
                document.querySelectorAll('.modal-backdrop, body > .modal[data-portaled="1"]').forEach(el => el.remove());
                document.body.classList.remove('modal-open');
                document.body.style.removeProperty('overflow');
                document.body.style.removeProperty('padding-right');

                curViewport.innerHTML = nextViewport.innerHTML;
                syncNavigationState(nextDoc, response.url || url);
                if (push) {
                    window.history.pushState({ libcore: true }, '', response.url || url);
                }
                window.scrollTo({ top: 0, behavior: 'instant' });
                runPageScripts(curViewport);
                animateNumbers(curViewport);
                autoDismissAlerts(curViewport);
            };

            if (document.startViewTransition && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                curViewport.classList.add('is-vt');
                try {
                    await document.startViewTransition(performSwap).finished;
                } finally {
                    curViewport.classList.remove('is-vt');
                }
            } else {
                performSwap();
                curViewport.classList.remove('page-enter');
                void curViewport.offsetWidth;
                curViewport.classList.add('page-enter');
                curViewport.addEventListener('animationend', () => curViewport.classList.remove('page-enter'), { once: true });
            }
        } catch (err) {
            if (err.name !== 'AbortError') {
                window.location.href = url;
            }
        } finally {
            progressDone();
        }
    }

    function shouldInterceptLink(anchor, event) {
        if (!anchor || event.defaultPrevented) return false;
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return false;
        if (anchor.hasAttribute('download') || anchor.dataset.noPjax !== undefined) return false;
        const target = anchor.getAttribute('target');
        if (target && target !== '_self') return false;
        const href = anchor.getAttribute('href');
        if (!href || href.startsWith('#') || href.startsWith('javascript:') || href.startsWith('mailto:')) return false;
        const url = new URL(href, window.location.origin);
        if (url.origin !== window.location.origin) return false;
        if (url.pathname === '/logout' || url.pathname.endsWith('/export') || url.pathname.endsWith('/print')) return false;
        return true;
    }

    document.addEventListener('click', event => {
        const anchor = event.target.closest('a');
        if (shouldInterceptLink(anchor, event)) {
            event.preventDefault();
            smoothNavigate(anchor.href, true);
        }
    });

    document.addEventListener('submit', event => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || event.defaultPrevented) return;
        if (form.dataset.noPjax !== undefined) return;
        const method = (form.getAttribute('method') || 'GET').toUpperCase();
        if (method !== 'GET') return;
        const action = form.getAttribute('action') || window.location.pathname;
        const url = new URL(action, window.location.origin);
        if (url.origin !== window.location.origin) return;
        const params = new URLSearchParams(new FormData(form));
        url.search = params.toString();
        event.preventDefault();
        smoothNavigate(url.toString(), true);
    });

    window.addEventListener('popstate', () => {
        smoothNavigate(window.location.href, false);
    });

    // Ensure Bootstrap modals are always direct children of <body> so they never get trapped under modal-backdrop
    document.addEventListener('show.bs.modal', event => {
        const modal = event.target;
        if (modal && modal.parentElement !== document.body) {
            modal.dataset.portaled = '1';
            document.body.appendChild(modal);
        }
    });

    // ---- Sidebar & Command Palette ----
    function initShellControls() {
        const sidebar = document.getElementById('sidebar');
        const backdrop = document.getElementById('sidebarBackdrop');
        document.getElementById('sidebarToggle')?.addEventListener('click', () => {
            sidebar?.classList.toggle('show');
            backdrop?.classList.toggle('show');
        });
        backdrop?.addEventListener('click', closeMobileDrawer);

        // Command Palette
        const cmdModal = document.getElementById('cmdPalette');
        const cmdInput = document.getElementById('cmdInput');
        const cmdResults = document.getElementById('cmdResults');
        if (!cmdModal || !cmdInput || !cmdResults) return;

        function openCmd() {
            cmdModal.classList.add('open');
            cmdInput.value = '';
            renderDefaultCommands();
            setTimeout(() => cmdInput.focus(), 40);
        }
        function closeCmd() {
            cmdModal.classList.remove('open');
        }

        document.getElementById('cmdTrigger')?.addEventListener('click', openCmd);
        cmdModal.addEventListener('click', e => {
            if (e.target === cmdModal) closeCmd();
        });

        document.addEventListener('keydown', e => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                cmdModal.classList.contains('open') ? closeCmd() : openCmd();
            } else if (e.key === 'Escape' && cmdModal.classList.contains('open')) {
                closeCmd();
            }
        });

        function esc(s) {
            return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
        }

        function renderDefaultCommands() {
            cmdResults.innerHTML = `
                <div class="px-2 py-1 text-uppercase fw-bold" style="font-size:10.5px;color:#64748B">Thao tác nhanh</div>
                <a href="/loans/create" class="cmd-item"><span><i class="fas fa-plus-circle me-2 text-primary"></i>Lập phiếu mượn sách</span><span class="text-muted small">/loans/create</span></a>
                <a href="/loans/reservations" class="cmd-item"><span><i class="fas fa-bookmark me-2 text-primary"></i>Danh sách đặt trước sách</span><span class="text-muted small">/loans/reservations</span></a>
                <a href="/books/create" class="cmd-item"><span><i class="fas fa-book-medical me-2 text-primary"></i>Thêm sách mới vào kho</span><span class="text-muted small">/books/create</span></a>
                <a href="/members/create" class="cmd-item"><span><i class="fas fa-id-card me-2 text-primary"></i>Cấp thẻ độc giả mới</span><span class="text-muted small">/members/create</span></a>
                <a href="/members/clearance" class="cmd-item"><span><i class="fas fa-graduation-cap me-2 text-primary"></i>Thanh lý thẻ ra trường</span><span class="text-muted small">/members/clearance</span></a>
                <a href="/catalog" class="cmd-item"><span><i class="fas fa-compass me-2 text-primary"></i>Mở Cổng tra cứu OPAC</span><span class="text-muted small">/catalog</span></a>
            `;
        }

        let searchTimer;
        cmdInput.addEventListener('input', () => {
            clearTimeout(searchTimer);
            const q = cmdInput.value.trim();
            if (q.length < 2) {
                renderDefaultCommands();
                return;
            }
            searchTimer = setTimeout(async () => {
                try {
                    const [bRes, mRes] = await Promise.all([
                        fetch(`/api/v1/books/search?q=${encodeURIComponent(q)}&limit=5`).then(r => r.json()),
                        fetch(`/api/v1/members/search?q=${encodeURIComponent(q)}&limit=5`).then(r => r.json()),
                    ]);
                    const books = bRes.data || [];
                    const members = mRes.data || [];
                    let html = '';
                    if (books.length) {
                        html += '<div class="px-2 py-1 text-uppercase fw-bold" style="font-size:10.5px;color:#64748B">Tài liệu</div>';
                        html += books.map(b => `
                            <a href="/books/${b.id}" class="cmd-item">
                                <div class="text-truncate"><i class="fas fa-book me-2 text-muted"></i><strong>${esc(b.title)}</strong> <span class="text-muted small">— ${esc(b.author)}</span></div>
                                <span class="code-chip">${esc(b.isbn)}</span>
                            </a>
                        `).join('');
                    }
                    if (members.length) {
                        html += '<div class="px-2 pt-2 pb-1 text-uppercase fw-bold" style="font-size:10.5px;color:#64748B">Độc giả</div>';
                        html += members.map(m => `
                            <a href="/members/${m.id}" class="cmd-item">
                                <div class="text-truncate"><i class="fas fa-user-graduate me-2 text-muted"></i><strong>${esc(m.full_name)}</strong> <span class="text-muted small">${esc(m.faculty)}</span></div>
                                <span class="code-chip">${esc(m.student_id || m.code)}</span>
                            </a>
                        `).join('');
                    }
                    cmdResults.innerHTML = html || '<div class="p-4 text-center text-muted small">Không tìm thấy kết quả phù hợp.</div>';
                } catch (_) {}
            }, 180);
        });

        cmdResults.addEventListener('click', e => {
            if (e.target.closest('a')) closeCmd();
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        initShellControls();
        const vp = document.getElementById('pageViewport');
        if (vp) {
            runPageScripts(vp);
            animateNumbers(vp);
            autoDismissAlerts(vp);
        }
    });
})();
