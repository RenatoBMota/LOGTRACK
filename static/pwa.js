// PWA - Funcionalidades essenciais SEM Service Worker
(function() {
    'use strict';

    // ===== DESABILITAR SERVICE WORKERS EXISTENTES =====
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistrations().then(registrations => {
            for (let registration of registrations) {
                registration.unregister().then(() => {
                    console.log('✅ Service Worker desregistrado');
                });
            }
        }).catch(error => {
            console.log('Erro ao desregistrar Service Worker:', error);
        });
    }

    // ===== DETECTAR MODO OFFLINE/ONLINE =====
    window.addEventListener('online', () => {
        console.log('✅ Conexão restaurada');
        document.body.classList.remove('offline-mode');
    });

    window.addEventListener('offline', () => {
        console.log('❌ Perdeu conexão');
        document.body.classList.add('offline-mode');
    });

    // ===== SALVAR DADOS OFFLINE =====
    window.logtrackDB = {
        saveOffline: function(key, data) {
            try {
                localStorage.setItem(`logtrack_offline_${key}`, JSON.stringify(data));
                console.log(`💾 Dados salvos offline: ${key}`);
            } catch (error) {
                console.error('Erro ao salvar offline:', error);
            }
        },

        getOffline: function(key) {
            try {
                const data = localStorage.getItem(`logtrack_offline_${key}`);
                return data ? JSON.parse(data) : null;
            } catch (error) {
                console.error('Erro ao ler offline:', error);
                return null;
            }
        },

        deleteOffline: function(key) {
            try {
                localStorage.removeItem(`logtrack_offline_${key}`);
            } catch (error) {
                console.error('Erro ao deletar offline:', error);
            }
        },

        clearAll: function() {
            try {
                Object.keys(localStorage).forEach((key) => {
                    if (key.startsWith('logtrack_offline_')) {
                        localStorage.removeItem(key);
                    }
                });
            } catch (error) {
                console.error('Erro ao limpar offline:', error);
            }
        }
    };

    // ===== SHARE API =====
    if (navigator.share) {
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('share-btn')) {
                const title = e.target.dataset.title || 'LogTrack';
                const text = e.target.dataset.text || 'Confira LogTrack!';
                const url = e.target.dataset.url || window.location.href;

                navigator.share({
                    title,
                    text,
                    url,
                }).catch((error) => console.log('Erro ao compartilhar:', error));
            }
        });
    }

    console.log('✅ PWA inicializado (Service Worker desabilitado)!');
})();

// ===== ADICIONAR ESTILOS PARA OFFLINE MODE =====
const style = document.createElement('style');
style.textContent = `
    body.offline-mode {
        filter: grayscale(30%);
    }

    body.offline-mode::before {
        content: '📡 Modo Offline - Alguns dados podem estar desatualizados';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: #ff9800;
        color: white;
        padding: 8px;
        text-align: center;
        font-size: 12px;
        z-index: 10000;
        font-weight: bold;
    }
`;
document.head.appendChild(style);
