// LogTrack PWA Service Worker - Android Optimized
const CACHE_NAME = 'logtrack-v2.0.0';
const ASSETS_TO_CACHE = [
    '/',
    '/login',
    '/dashboard',
    '/operation',
    '/sla',
    '/sla-goals',
    '/cadastros',
    '/relatorios',
    '/occurrence-report',
    '/static/pwa.js',
    '/static/icon-192.png',
    '/static/icon-512.png',
    '/static/vendor/bootstrap/css/bootstrap.min.css',
    '/static/vendor/fontawesome/css/all.min.css',
    '/static/vendor/bootstrap/js/bootstrap.bundle.min.js',
];

// Install - Cache tudo
self.addEventListener('install', (event) => {
    console.log('[SW] Instalando Service Worker v2...');
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[SW] Cache aberto, adicionando assets...');
            return cache.addAll(ASSETS_TO_CACHE).catch((error) => {
                console.log('[SW] Alguns assets falharam (esperado):', error);
                // Continua mesmo que alguns falhem
            });
        })
    );
    self.skipWaiting();
});

// Activate - Limpar caches antigos
self.addEventListener('activate', (event) => {
    console.log('[SW] Ativando Service Worker v2...');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('[SW] Deletando cache antigo:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch - Network First com Cache Fallback (MELHOR PARA ANDROID)
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Ignorar requisições não-GET
    if (request.method !== 'GET') {
        return;
    }

    // Para requisições HTML (páginas)
    if (request.headers.get('accept')?.includes('text/html')) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    if (response.status === 200) {
                        const cache = caches.open(CACHE_NAME);
                        cache.then((c) => c.put(request, response.clone()));
                    }
                    return response;
                })
                .catch(() => {
                    return caches.match(request).then((cached) => {
                        return cached || createOfflineResponse();
                    });
                })
        );
        return;
    }

    // Para assets (CSS, JS, imagens) - Cache First
    if (request.url.includes('/static/') || request.url.includes('cdn.jsdelivr') || request.url.includes('cdnjs')) {
        event.respondWith(
            caches.match(request).then((cached) => {
                return cached || fetch(request).then((response) => {
                    if (response.status === 200) {
                        const cache = caches.open(CACHE_NAME);
                        cache.then((c) => c.put(request, response.clone()));
                    }
                    return response;
                }).catch(() => {
                    console.log('[SW] Asset não encontrado:', request.url);
                    return new Response('', { status: 404 });
                });
            })
        );
        return;
    }

    // Para requisições API - Network Only
    if (request.url.includes('/api/')) {
        event.respondWith(fetch(request));
        return;
    }

    // Padrão: Network First
    event.respondWith(
        fetch(request).then((response) => {
            if (response.status === 200) {
                const cache = caches.open(CACHE_NAME);
                cache.then((c) => c.put(request, response.clone()));
            }
            return response;
        }).catch(() => {
            return caches.match(request);
        })
    );
});

// Resposta offline customizada
function createOfflineResponse() {
    return new Response(
        `<!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Offline - LogTrack</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #0066CC 0%, #1aa84a 100%);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    color: white;
                    padding: 20px;
                }
                .container {
                    text-align: center;
                    background: rgba(0, 0, 0, 0.15);
                    padding: 40px;
                    border-radius: 12px;
                    backdrop-filter: blur(10px);
                    max-width: 400px;
                }
                .icon {
                    font-size: 64px;
                    margin-bottom: 20px;
                }
                h1 {
                    font-size: 28px;
                    margin-bottom: 15px;
                    font-weight: 600;
                }
                p {
                    font-size: 16px;
                    margin-bottom: 20px;
                    opacity: 0.9;
                    line-height: 1.5;
                }
                .status {
                    display: inline-block;
                    padding: 10px 20px;
                    background: rgba(255, 255, 255, 0.2);
                    border-radius: 20px;
                    margin-bottom: 30px;
                    font-size: 14px;
                    font-weight: 600;
                }
                button {
                    background: white;
                    color: #0066CC;
                    border: none;
                    padding: 12px 30px;
                    border-radius: 20px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                    margin-bottom: 20px;
                }
                button:active {
                    transform: scale(0.95);
                }
                .info {
                    font-size: 12px;
                    opacity: 0.8;
                    margin-top: 30px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">📡</div>
                <h1>Você está offline</h1>
                <p>Sem conexão com a internet no momento.</p>
                <p>Você pode acessar páginas em cache ou aguardar a conexão voltar.</p>
                <div class="status">🔴 Status: Sem conexão</div>
                <br>
                <button onclick="location.reload()">Tentar Novamente</button>
                <p class="info">Seu progresso será sincronizado quando reconectar.</p>
            </div>
            <script>
                // Verificar conexão periodicamente
                window.addEventListener('online', () => {
                    console.log('✅ Conexão restaurada!');
                    setTimeout(() => location.reload(), 1000);
                });
            </script>
        </body>
        </html>`,
        {
            status: 503,
            statusText: 'Service Unavailable',
            headers: new Headers({
                'Content-Type': 'text/html; charset=utf-8',
            }),
        }
    );
}

// Sincronização em background
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-operations') {
        event.waitUntil(syncOperations());
    }
});

async function syncOperations() {
    try {
        console.log('[SW] Sincronizando operações...');
        // Implementar lógica de sincronização aqui
    } catch (error) {
        console.error('[SW] Erro ao sincronizar:', error);
    }
}

// Notificações Push
self.addEventListener('push', (event) => {
    const data = event.data?.json() ?? {};
    const title = data.title || 'LogTrack';
    const options = {
        body: data.body || 'Nova notificação',
        icon: '/static/icon-192.png',
        badge: '/static/icon-192.png',
        tag: 'logtrack-notification',
        requireInteraction: true,
        actions: [
            { action: 'open', title: 'Abrir' },
            { action: 'close', title: 'Fechar' },
        ],
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

// Click em notificação
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    event.waitUntil(
        clients.matchAll({ type: 'window' }).then((clientList) => {
            for (let client of clientList) {
                if (client.url === '/' && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow('/dashboard');
            }
        })
    );
});

console.log('[SW] Service Worker v2 carregado e pronto! ✅');
