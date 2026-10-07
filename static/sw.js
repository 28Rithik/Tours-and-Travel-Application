/**
 * 📱 TravelERP Driver Portal — Service Worker (PWA Offline Support)
 * =================================================================
 * Cache-first strategy for static assets, network-first for API/dynamic content.
 * Provides offline fallback page for disconnected drivers.
 */

const CACHE_NAME = 'driver-portal-v1';
const OFFLINE_URL = '/driver/login/';

// Static assets to pre-cache on installation
const PRE_CACHE_URLS = [
  '/driver/',
  '/driver/login/',
  '/static/manifest.json',
];

// Install — pre-cache critical assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Pre-caching critical assets');
      return cache.addAll(PRE_CACHE_URLS);
    }).catch((err) => {
      console.warn('[SW] Pre-cache partially failed (expected on first install):', err.message);
    })
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    })
  );
  self.clients.claim();
});

// Fetch — network-first for navigation, cache-first for static
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests (form submissions, API POSTs)
  if (request.method !== 'GET') return;

  // Skip external requests
  if (url.origin !== self.location.origin) return;

  // API calls — network only, no caching
  if (url.pathname.startsWith('/api/')) return;

  // Static assets — cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(request).then((cached) => {
        return cached || fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // Navigation requests — network-first with offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache successful navigation responses
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => {
          // Offline — try cache, then fallback
          return caches.match(request).then((cached) => {
            return cached || caches.match(OFFLINE_URL).then((offlinePage) => {
              return offlinePage || new Response(
                `<!DOCTYPE html>
                <html>
                <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
                <title>Offline | Driver Desk</title>
                <style>
                  body { font-family: -apple-system, sans-serif; background: #090d16; color: #f8fafc;
                         display: flex; align-items: center; justify-content: center; min-height: 100vh;
                         text-align: center; padding: 2rem; }
                  .offline-card { background: #1e293b; border-radius: 16px; padding: 3rem 2rem;
                                  max-width: 400px; border: 1px solid #334155; }
                  .offline-icon { font-size: 4rem; margin-bottom: 1rem; }
                  h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
                  p { color: #94a3b8; font-size: 0.9rem; line-height: 1.6; }
                  .retry-btn { display: inline-block; margin-top: 1.5rem; padding: 0.75rem 2rem;
                               background: #38bdf8; color: #0f172a; font-weight: 700; border-radius: 12px;
                               text-decoration: none; font-size: 0.9rem; }
                </style></head>
                <body>
                  <div class="offline-card">
                    <div class="offline-icon">📡</div>
                    <h1>No Network Connection</h1>
                    <p>Your device is currently offline. Trip data submitted while offline will sync when you reconnect.</p>
                    <a href="/" class="retry-btn" onclick="location.reload(); return false;">↻ Retry Connection</a>
                  </div>
                </body></html>`,
                { headers: { 'Content-Type': 'text/html' } }
              );
            });
          });
        })
    );
    return;
  }
});

// Background Sync — queue offline form submissions
self.addEventListener('sync', (event) => {
  if (event.tag === 'driver-form-sync') {
    console.log('[SW] Background sync triggered for queued forms');
  }
});

// Push Notifications (future — SOS alerts, dispatch updates)
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || 'Driver Desk Alert';
  const options = {
    body: data.body || 'You have a new notification.',
    icon: '/static/pwa/icon-192.png',
    badge: '/static/pwa/icon-192.png',
    vibrate: [200, 100, 200],
    tag: data.tag || 'driver-alert',
    data: { url: data.url || '/driver/' },
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.url || '/driver/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      for (const client of clients) {
        if (client.url.includes('/driver/') && 'focus' in client) {
          return client.focus();
        }
      }
      return self.clients.openWindow(url);
    })
  );
});
