/**
 * 📱 TravelERP Driver Portal — Offline IndexedDB Queue & Auto-Sync Engine
 * =======================================================================
 * Enables chauffeurs to log milestones, fuel slips, toll receipts, guest PINs,
 * and passenger boarding passes even in complete network deadzones (ghat roads/highways).
 * Automatically flushes and synchronizes all mutations sequentially with the
 * Operations Control Room when network connectivity is restored.
 */

(function(window) {
  'use strict';

  const DB_NAME = 'TravelErpDriverDB';
  const DB_VERSION = 1;
  const STORE_NAME = 'offline_queue';

  let dbInstance = null;

  function openDatabase() {
    return new Promise((resolve, reject) => {
      if (dbInstance) return resolve(dbInstance);

      if (!window.indexedDB) {
        console.warn('[OfflineSync] IndexedDB not supported on this browser.');
        return reject(new Error('IndexedDB not supported'));
      }

      const req = window.indexedDB.open(DB_NAME, DB_VERSION);

      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          const store = db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
          store.createIndex('timestamp', 'timestamp', { unique: false });
          store.createIndex('status', 'status', { unique: false });
        }
      };

      req.onsuccess = (e) => {
        dbInstance = e.target.result;
        resolve(dbInstance);
      };

      req.onerror = (e) => {
        console.error('[OfflineSync] Failed to open IndexedDB:', e.target.error);
        reject(e.target.error);
      };
    });
  }

  // Add an action to the local offline queue
  async function queueMutation(mutation) {
    try {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);

        const record = {
          url: mutation.url,
          method: mutation.method || 'POST',
          headers: mutation.headers || { 'Content-Type': 'application/json' },
          body: mutation.body,
          actionName: mutation.actionName || 'Duty Milestone',
          tripId: mutation.tripId,
          timestamp: Date.now(),
          createdAtStr: new Date().toLocaleTimeString(),
          status: 'pending'
        };

        const addReq = store.add(record);
        addReq.onsuccess = () => {
          console.log('[OfflineSync] Successfully queued mutation locally:', record.actionName);
          updateQueueBadge();
          resolve(addReq.result);
        };
        addReq.onerror = (err) => reject(err);
      });
    } catch (err) {
      console.error('[OfflineSync] Error queueing mutation:', err);
      throw err;
    }
  }

  // Fetch all pending mutations
  async function getPendingMutations() {
    try {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const req = store.getAll();
        req.onsuccess = () => resolve(req.result || []);
        req.onerror = (err) => reject(err);
      });
    } catch (err) {
      return [];
    }
  }

  // Remove a completed mutation
  async function removeMutation(id) {
    try {
      const db = await openDatabase();
      return new Promise((resolve, reject) => {
        const tx = db.transaction(STORE_NAME, 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        const req = store.delete(id);
        req.onsuccess = () => resolve();
        req.onerror = (err) => reject(err);
      });
    } catch (err) {
      console.warn('[OfflineSync] Error deleting mutation:', err);
    }
  }

  let isSyncing = false;

  // Flush the queue sequentially
  async function flushQueue() {
    if (isSyncing) return;
    if (!navigator.onLine) {
      console.log('[OfflineSync] Still offline, postponing queue flush.');
      return;
    }

    const items = await getPendingMutations();
    if (items.length === 0) {
      updateQueueBadge();
      return;
    }

    isSyncing = true;
    showToast(`🔄 Reconnected! Syncing ${items.length} offline actions...`, 'info');

    let successCount = 0;
    for (const item of items) {
      try {
        let fetchBody = item.body;
        let headers = Object.assign({}, item.headers);

        const resp = await fetch(item.url, {
          method: item.method,
          headers: headers,
          body: typeof fetchBody === 'object' ? JSON.stringify(fetchBody) : fetchBody
        });

        if (resp.ok || resp.status === 400) {
          // If 200 OK or 400 validation discrepancy, remove from queue
          await removeMutation(item.id);
          successCount++;
        } else if (resp.status >= 500) {
          // Server error, pause and retry later
          console.warn('[OfflineSync] Server error during sync, pausing.');
          break;
        }
      } catch (networkErr) {
        console.warn('[OfflineSync] Network interrupted during sync. Will retry.', networkErr);
        break;
      }
    }

    isSyncing = false;
    updateQueueBadge();

    if (successCount > 0) {
      showToast(`🟢 ${successCount} offline duty actions successfully synced!`, 'success');
      // If trip detail page, reload or refresh status
      if (typeof window.fetchMilestoneStatus === 'function') {
        window.fetchMilestoneStatus();
      }
    }
  }

  // Update UI connectivity badges
  async function updateQueueBadge() {
    const items = await getPendingMutations();
    const count = items.length;
    const isOnline = navigator.onLine;

    const badge = document.getElementById('pwaConnectionBadge');
    const queuePill = document.getElementById('offlineQueuePill');

    if (badge) {
      if (!isOnline) {
        badge.innerHTML = '🟠 Offline Mode';
        badge.style.color = '#f59e0b';
      } else if (count > 0) {
        badge.innerHTML = `🟠 Syncing (${count})`;
        badge.style.color = '#f59e0b';
      } else {
        badge.innerHTML = '🟢 Online';
        badge.style.color = '#10b981';
      }
    }

    if (queuePill) {
      if (count > 0) {
        queuePill.style.display = 'inline-flex';
        queuePill.innerHTML = `<span>⏳ ${count} Queued</span> <button type="button" onclick="window.driverOfflineSync.flush()" style="background:none;border:none;color:inherit;cursor:pointer;padding:0 4px;font-weight:800;" title="Tap to sync now">🔄</button>`;
      } else {
        queuePill.style.display = 'none';
      }
    }
  }

  // Simple Notification Toast
  function showToast(msg, type) {
    let container = document.getElementById('pwaToastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'pwaToastContainer';
      container.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);z-index:99999;display:flex;flex-direction:column;gap:8px;max-width:90%;width:380px;pointer-events:none;';
      document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bg = type === 'success' ? '#059669' : type === 'info' ? '#0284c7' : '#d97706';
    toast.style.cssText = `background:${bg};color:#ffffff;padding:12px 16px;border-radius:10px;font-size:13px;font-weight:700;box-shadow:0 10px 30px rgba(0,0,0,0.3);text-align:center;pointer-events:auto;transition:opacity 0.3s;`;
    toast.textContent = msg;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  // Network Event Listeners
  window.addEventListener('online', () => {
    console.log('[OfflineSync] Network re-established.');
    updateQueueBadge();
    flushQueue();
  });

  window.addEventListener('offline', () => {
    console.log('[OfflineSync] Device went offline.');
    updateQueueBadge();
    showToast('🟠 Network offline. Actions will be safely saved locally.', 'warning');
  });

  // Expose API
  window.driverOfflineSync = {
    queue: queueMutation,
    flush: flushQueue,
    getPending: getPendingMutations,
    updateBadge: updateQueueBadge,
    showToast: showToast
  };

  // Auto-init on page load
  document.addEventListener('DOMContentLoaded', () => {
    updateQueueBadge();
    if (navigator.onLine) {
      flushQueue();
    }
  });

})(window);
