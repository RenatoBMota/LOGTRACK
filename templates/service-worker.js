// LogTrack PWA Service Worker
const CACHE_NAME = 'logtrack-v1.0.0';
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
    '/usuarios',
    '/configuracoes',
    '/static/css/style.css',
    '/static/js/app.js',
];

// Instalar Service Worker e cache
self.addEventListener('install', (event) => {
    console.log('Service Worker instalado');
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('Cache aberto');
            return cache.addAll(ASSETS_TO_CACHE).catch((error) => {
                console.log('Erro ao fazer cache:', error);
            });
        })
    );
    self.skipWaiting();
});

// Ativar Service Worker e limpar caches antigos
self.addEventListener('activate', (event) => {
    console.log('Service Worker ativado');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deletando cache antigo:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Estratégia de Network First (tenta rede primeiro, depois cache)
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Ignorar requisições não-GET
    if (request.method !== 'GET') {
        return;
    }

    // Ignorar requisições API (POST, PUT, DELETE, PATCH)
    if (url.pathname.includes('/api/') || request.method !== 'GET') {
        event.respondWith(fetch(request));
        return;
    }

    // Estratégia: Network First
    event.respondWith(
        fetch(request)
            .then((response) => {
                // Cache apenas responses bem-sucedidas
                if (response.status === 200) {
                    const responseToCache = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(request, responseToCache);
                    });
                }
                return response;
            })
            .catch(() => {
                // Se falhar, tenta cache
                return caches.match(request).then((cachedResponse) => {
                    return cachedResponse || createOfflineResponse();
                });
            })
    );
});

// Resposta offline customizada
function createOfflineResponse() {
    return new Response(
        `
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>LogTrack - Offline</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                    background: linear-gradient(135deg, #0066CC, #1aa84a);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    color: white;
                    padding: 20px;
                }
                .offline-container {
                    text-align: center;
                    background: rgba(0,0,0,0.2);
                    padding: 40px;
                    border-radius: 12px;
                    backdrop-filter: blur(10px);
                }
                h1 { font-size: 48px; margin-bottom: 20px; }
                p { font-size: 18px; margin-bottom: 30px; opacity: 0.9; }
                .status { 
                    display: inline-block;
                    padding: 10px 20px;
                    background: rgba(255,255,255,0.2);
                    border-radius: 6px;
                    margin-bottom: 30px;
                }
                button {
                    background: white;
                    color: #0066CC;
                    border: none;
                    padding: 12px 30px;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                    cursor: pointer;
                    transition: transform 0.2s;
                }
                button:hover { transform: scale(1.05); }
                .icon { font-size: 64px; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <div class="offline-container">
                <div class="icon">📡</div>
                <h1>Você está offline</h1>
                <p>Parece que você perdeu a conexão com a internet.</p>
                <p>Você pode acessar páginas em cache ou aguardar a conexão voltar.</p>
                <div class="status">Status: Sem conexão</div>
                <br>
                <button onclick="location.reload()">Tentar novamente</button>
                <p style="margin-top: 30px; font-size: 14px; opacity: 0.7;">
                    Seu progresso será salvo automaticamente quando reconectar.
                </p>
            </div>
            <script>
                // Verifica conexão periodicamente
                window.addEventListener('online', () => {
                    console.log('Conexão restaurada!');
                    location.reload();
                });
            </script>
        </body>
        </html>
        `,
        {
            status: 503,
            statusText: 'Service Unavailable',
            headers: new Headers({
                'Content-Type': 'text/html; charset=utf-8',
            }),
        }
    );
}

// Sincronização em background (salva dados offline para sincronizar depois)
self.addEventListener('sync', (event) => {
    if (event.tag === 'sync-operations') {
        event.waitUntil(syncOperations());
    }
});

async function syncOperations() {
    try {
        // Aqui você pode sincronizar dados salvos offline
        console.log('Sincronizando operações...');
        // Implementar lógica de sincronização
    } catch (error) {
        console.error('Erro ao sincronizar:', error);
    }
}

// Notificações Push
self.addEventListener('push', (event) => {
    const data = event.data?.json() ?? {};
    const title = data.title || 'LogTrack - Notificação';
    const options = {
        body: data.body || 'Você tem uma nova notificação',
        icon: '/static/icon-192.png',
        badge: '/static/badge-72.png',
        tag: 'logtrack-notification',
        requireInteraction: true,
        actions: [
            { action: 'open', title: 'Abrir' },
            { action: 'close', title: 'Fechar' },
        ],
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

// Clique em notificação
self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    if (event.action === 'open' || !event.action) {
        event.waitUntil(
            clients.matchAll({ type: 'window' }).then((clientList) => {
                // Se já tem uma aba aberta, foca nela
                for (let client of clientList) {
                    if (client.url === '/' && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Caso contrário, abre uma nova
                if (clients.openWindow) {
                    return clients.openWindow('/');
                }
            })
        );
    }
});

console.log('Service Worker carregado e pronto para trabalhar!');
