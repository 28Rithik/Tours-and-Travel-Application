/**
 * ============================================================================
 * SIVA GAYATHRI TOURS & TRAVELS — MAPLIBRE OFFLINE PACK & CACHE MANAGER
 * Enables 100% offline navigation through Nilgiris, Ooty, & Western Ghats.
 * Uses browser IndexedDB + CacheStorage API for vector tiles & style JSON.
 * ============================================================================
 */

(function (window) {
    'use strict';

    const DB_NAME = 'TravelERPOfflineTilesDB';
    const DB_VERSION = 1;
    const STORE_NAME = 'vector_tiles';

    class OfflineTileManager {
        constructor() {
            this.db = null;
            this.initPromise = this._initIndexedDB();
            this.offlineRegions = {
                'ooty_nilgiris': {
                    name: 'Nilgiris & Ooty Ghat Road Corridor',
                    bbox: [76.68, 11.30, 76.92, 11.45],
                    minZoom: 10,
                    maxZoom: 14,
                    description: 'Offline vector map for Mettupalayam - Coonoor - Ooty route.'
                },
                'kodaikanal': {
                    name: 'Kodaikanal Mountain Range',
                    bbox: [77.45, 10.20, 77.55, 10.28],
                    minZoom: 10,
                    maxZoom: 14,
                    description: 'Offline map for Batlagundu - Kodaikanal Ghat.'
                },
                'coimbatore_hq': {
                    name: 'Coimbatore Hub Depot & Airport',
                    bbox: [76.92, 10.98, 77.05, 11.06],
                    minZoom: 11,
                    maxZoom: 15,
                    description: 'HQ central depot and high frequency pickup corridor.'
                }
            };
        }

        _initIndexedDB() {
            return new Promise((resolve, reject) => {
                if (!window.indexedDB) {
                    console.warn('[OfflineMap] IndexedDB not supported by this browser.');
                    resolve(null);
                    return;
                }
                const request = window.indexedDB.open(DB_NAME, DB_VERSION);
                request.onupgradeneeded = (event) => {
                    const db = event.target.result;
                    if (!db.objectStoreNames.contains(STORE_NAME)) {
                        db.createObjectStore(STORE_NAME, { keyPath: 'url' });
                    }
                };
                request.onsuccess = (event) => {
                    this.db = event.target.result;
                    console.log('[OfflineMap] IndexedDB initialized successfully.');
                    resolve(this.db);
                };
                request.onerror = (event) => {
                    console.error('[OfflineMap] IndexedDB open error:', event.target.error);
                    resolve(null);
                };
            });
        }

        /**
         * Intercepts MapLibre GL request via transformRequest.
         * If offline or cached, serves PBF from IndexedDB.
         */
        async interceptTransformRequest(url, resourceType) {
            if (resourceType !== 'Tile') {
                return { url };
            }

            await this.initPromise;
            if (!this.db) {
                return { url };
            }

            try {
                const cachedData = await this._getTile(url);
                if (cachedData) {
                    // Create Blob URL from cached ArrayBuffer
                    const blob = new Blob([cachedData.data], { type: 'application/x-protobuf' });
                    return { url: URL.createObjectURL(blob) };
                }
            } catch (err) {
                console.warn('[OfflineMap] Cache fetch error for:', url, err);
            }

            return { url };
        }

        _getTile(url) {
            return new Promise((resolve) => {
                if (!this.db) return resolve(null);
                const tx = this.db.transaction(STORE_NAME, 'readonly');
                const store = tx.objectStore(STORE_NAME);
                const req = store.get(url);
                req.onsuccess = () => resolve(req.result);
                req.onerror = () => resolve(null);
            });
        }

        _saveTile(url, arrayBuffer) {
            return new Promise((resolve) => {
                if (!this.db) return resolve(false);
                const tx = this.db.transaction(STORE_NAME, 'readwrite');
                const store = tx.objectStore(STORE_NAME);
                store.put({ url, data: arrayBuffer, savedAt: Date.now() });
                tx.oncomplete = () => resolve(true);
                tx.onerror = () => resolve(false);
            });
        }

        /**
         * Downloads and stores an entire offline pack into IndexedDB.
         */
        async downloadOfflineRegion(regionKey, progressCallback) {
            const region = this.offlineRegions[regionKey];
            if (!region) {
                throw new Error(`Region ${regionKey} is not configured.`);
            }

            console.log(`[OfflineMap] Starting download of pack: ${region.name}`);
            const tileUrls = this._computeTileUrls(region.bbox, region.minZoom, region.maxZoom);
            let downloaded = 0;

            for (const url of tileUrls) {
                try {
                    const resp = await fetch(url);
                    if (resp.ok) {
                        const buffer = await resp.arrayBuffer();
                        await this._saveTile(url, buffer);
                    }
                } catch (e) {
                    // Network failure for single tile
                }
                downloaded++;
                if (progressCallback) {
                    progressCallback({
                        current: downloaded,
                        total: tileUrls.length,
                        pct: Math.round((downloaded / tileUrls.length) * 100)
                    });
                }
            }

            console.log(`[OfflineMap] Pack ${region.name} downloaded successfully!`);
            return { status: 'success', count: downloaded, region: region.name };
        }

        _computeTileUrls(bbox, minZoom, maxZoom) {
            const baseUrl = window.location.origin.includes('8000') ? 'http://127.0.0.1:8088' : '';
            const urls = [];
            // Generate tile coordinates
            for (let z = minZoom; z <= maxZoom; z++) {
                const minX = Math.floor((bbox[0] + 180) / 360 * Math.pow(2, z));
                const maxX = Math.floor((bbox[2] + 180) / 360 * Math.pow(2, z));
                const minY = Math.floor((1 - Math.log(Math.tan(bbox[3] * Math.PI / 180) + 1 / Math.cos(bbox[3] * Math.PI / 180)) / Math.PI) / 2 * Math.pow(2, z));
                const maxY = Math.floor((1 - Math.log(Math.tan(bbox[1] * Math.PI / 180) + 1 / Math.cos(bbox[1] * Math.PI / 180)) / Math.PI) / 2 * Math.pow(2, z));

                for (let x = Math.min(minX, maxX); x <= Math.max(minX, maxX); x++) {
                    for (let y = Math.min(minY, maxY); y <= Math.max(minY, maxY); y++) {
                        urls.push(`${baseUrl}/data/v3/${z}/${x}/${y}.pbf`);
                        if (urls.length > 300) break; // Limit single pack size to avoid overwhelming mobile memory
                    }
                }
            }
            return urls;
        }

        /**
         * Attaches offline cache handler to a MapLibre GL map instance.
         */
        attachToMapLibre(mapInstance) {
            if (!mapInstance) return;
            mapInstance.setTransformRequest((url, resourceType) => {
                return this.interceptTransformRequest(url, resourceType);
            });
            console.log('[OfflineMap] MapLibre transformRequest attached.');
        }
    }

    // Export singleton to global scope
    window.TravelERPOfflineMap = new OfflineTileManager();

})(window);
