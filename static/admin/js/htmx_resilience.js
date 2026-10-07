/**
 * Siva Gayathri Tours & Travels — HTMX Enterprise Resilience & Toast Notifications
 * Intercepts HTMX network events, response errors, timeouts, and triggers.
 */

(function () {
    'use strict';

    function getOrCreateToastContainer() {
        let container = document.getElementById('sg-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'sg-toast-container';
            container.className = 'fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none';
            document.body.appendChild(container);
        }
        return container;
    }

    function showToast(message, type = 'error', title = 'System Alert') {
        const container = getOrCreateToastContainer();
        const toast = document.createElement('div');
        toast.className = 'pointer-events-auto flex items-start gap-3 p-3.5 rounded-xl shadow-2xl border text-sm transition-all duration-300 transform translate-x-4 opacity-0';

        let bgClass, borderClass, textClass, iconName;
        if (type === 'error') {
            bgClass = 'bg-rose-950/90 text-rose-100 backdrop-blur-md';
            borderClass = 'border-rose-700/60';
            textClass = 'text-rose-400';
            iconName = 'error';
        } else if (type === 'warning') {
            bgClass = 'bg-amber-950/90 text-amber-100 backdrop-blur-md';
            borderClass = 'border-amber-700/60';
            textClass = 'text-amber-400';
            iconName = 'warning';
        } else if (type === 'info') {
            bgClass = 'bg-sky-950/90 text-sky-100 backdrop-blur-md';
            borderClass = 'border-sky-700/60';
            textClass = 'text-sky-400';
            iconName = 'info';
        } else {
            bgClass = 'bg-emerald-950/90 text-emerald-100 backdrop-blur-md';
            borderClass = 'border-emerald-700/60';
            textClass = 'text-emerald-400';
            iconName = 'check_circle';
        }

        toast.className += ` ${bgClass} ${borderClass}`;

        toast.innerHTML = `
            <span class="material-symbols-outlined ${textClass} text-xl shrink-0 mt-0.5">${iconName}</span>
            <div class="flex-1">
                <div class="font-bold text-xs uppercase tracking-wider mb-0.5 ${textClass}">${title}</div>
                <div class="text-xs font-medium leading-relaxed">${message}</div>
            </div>
            <button type="button" class="shrink-0 text-slate-400 hover:text-white transition-colors" onclick="this.parentElement.remove()">
                <span class="material-symbols-outlined text-sm">close</span>
            </button>
        `;

        container.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.remove('translate-x-4', 'opacity-0');
            toast.classList.add('translate-x-0', 'opacity-100');
        });

        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.classList.remove('translate-x-0', 'opacity-100');
            toast.classList.add('translate-x-4', 'opacity-0');
            setTimeout(() => toast.remove(), 350);
        }, 5000);
    }

    // Attach to HTMX events
    document.addEventListener('htmx:responseError', function (evt) {
        const xhr = evt.detail.xhr;
        const status = xhr ? xhr.status : 0;
        let msg = 'Live calculation or fragment request failed.';
        
        if (status === 400) {
            try {
                const data = JSON.parse(xhr.responseText);
                msg = data.error || 'Invalid parameters supplied for calculation.';
            } catch (e) {
                msg = 'Validation error during reactive calculation (400).';
            }
            showToast(msg, 'warning', 'Validation Warning');
        } else if (status === 403) {
            showToast('Permission denied or CSRF session expired. Please refresh the page.', 'error', 'Authorization Error');
        } else if (status === 404) {
            showToast('The requested resource or endpoint was not found.', 'warning', 'Resource Missing');
        } else if (status >= 500) {
            showToast('Internal server error during live fragment update. Details recorded.', 'error', 'Server Error');
        } else {
            showToast(`Unexpected error (${status}) during live recalculation.`, 'error', 'Network Notice');
        }
    });

    document.addEventListener('htmx:sendError', function (evt) {
        showToast('Network connection lost or server unreachable. Live updates paused.', 'error', 'Offline / Disconnected');
    });

    document.addEventListener('htmx:timeout', function (evt) {
        showToast('The calculation request timed out. Please check your connectivity.', 'warning', 'Timeout');
    });

    // Expose utility globally for application code
    window.SGToast = { show: showToast };
})();
