(function () {
    const messagesEl = document.getElementById('chat-messages');
    if (!messagesEl) return;

    const conversationId = messagesEl.dataset.conversationId;
    const wsScheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = wsScheme + '//' + window.location.host + '/ws/chat/' + conversationId + '/';
    const messagesUrl = '/inbox/conversations/' + conversationId + '/messages/';
    const sendUrl = '/inbox/conversations/' + conversationId + '/send/';
    const feedUrl = '/inbox/conversations/feed/' + window.location.search;

    let socket = null;
    let wsConnected = false;
    let pollTimer = null;
    let feedTimer = null;
    let lastMessageId = 0;

    messagesEl.querySelectorAll('[data-id]').forEach(function (node) {
        const id = parseInt(node.dataset.id, 10);
        if (id > lastMessageId) lastMessageId = id;
    });

    function appendMessage(msg) {
        if (!msg || !msg.id) return;
        if (document.querySelector('[data-id="' + msg.id + '"]')) return;

        const div = document.createElement('div');
        div.className = 'message message-' + msg.sender_type;
        div.dataset.id = msg.id;

        const meta = document.createElement('div');
        meta.className = 'message-meta';
        const time = new Date(msg.created_at);
        meta.innerHTML = '<span class="message-sender">' + escapeHtml(msg.sender_name) + '</span> ' +
            '<span class="message-time">' + time.toLocaleString() + '</span>';

        const bubble = document.createElement('div');
        const isAudio = msg.message_type === 'audio' && msg.audio_url;
        bubble.className = 'message-bubble' + (isAudio ? ' message-bubble-audio' : '');

        if (isAudio) {
            const audio = document.createElement('audio');
            audio.className = 'message-audio';
            audio.controls = true;
            audio.preload = 'metadata';
            const source = document.createElement('source');
            source.src = msg.audio_url;
            if (msg.audio_mime_type) {
                source.type = msg.audio_mime_type;
            }
            audio.appendChild(source);
            bubble.appendChild(audio);
            if (msg.duration_seconds) {
                const dur = document.createElement('span');
                dur.className = 'message-audio-duration';
                dur.textContent = msg.duration_seconds + 's';
                bubble.appendChild(dur);
            }
        } else if (msg.content) {
            bubble.textContent = msg.content;
        } else {
            return;
        }

        div.appendChild(meta);
        div.appendChild(bubble);
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
        lastMessageId = Math.max(lastMessageId, msg.id);
        updateSidebarPreview(msg);
    }

    function updateSidebarPreview(msg) {
        const item = document.querySelector('.conversation-item[href*="conversation=' + conversationId + '"]');
        if (!item) return;
        const preview = item.querySelector('.conv-preview');
        if (preview) {
            preview.textContent = msg.message_type === 'audio'
                ? (msg.content || 'Voice message')
                : (msg.content || '');
        }
        item.classList.add('unread');
    }

    function escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }

    function getCsrfToken() {
        const cookie = document.cookie.split(';').find(function (c) {
            return c.trim().startsWith('csrftoken=');
        });
        return cookie ? cookie.split('=')[1] : '';
    }

    function pollMessages() {
        const url = messagesUrl + (lastMessageId ? ('?since=' + lastMessageId) : '');
        fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
            .then(function (response) {
                if (!response.ok) throw new Error('poll failed');
                return response.json();
            })
            .then(function (data) {
                (data.messages || []).forEach(appendMessage);
            })
            .catch(function () {
                /* keep polling */
            });
    }

    function pollFeed() {
        fetch(feedUrl, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
            .then(function (response) {
                if (!response.ok) throw new Error('feed failed');
                return response.json();
            })
            .then(function (data) {
                (data.conversations || []).forEach(function (conv) {
                    const item = document.querySelector('.conversation-item[href*="conversation=' + conv.id + '"]');
                    if (!item) return;
                    const preview = item.querySelector('.conv-preview');
                    if (preview && conv.preview) preview.textContent = conv.preview;
                    item.classList.toggle('unread', !!conv.is_unread);
                    const pill = item.querySelector('.status-pill');
                    if (pill) {
                        pill.className = 'status-pill status-' + conv.status;
                        pill.textContent = conv.status.charAt(0).toUpperCase() + conv.status.slice(1);
                    }
                });
            })
            .catch(function () {
                /* keep polling */
            });
    }

    function startPolling() {
        if (pollTimer) return;
        pollTimer = setInterval(pollMessages, 3000);
        feedTimer = setInterval(pollFeed, 5000);
        pollMessages();
        pollFeed();
    }

    function connect() {
        try {
            socket = new WebSocket(wsUrl);
            socket.onopen = function () {
                wsConnected = true;
            };
            socket.onmessage = function (e) {
                try {
                    appendMessage(JSON.parse(e.data));
                } catch (err) {
                    /* ignore malformed payloads */
                }
            };
            socket.onclose = function () {
                wsConnected = false;
                startPolling();
                setTimeout(connect, 3000);
            };
            socket.onerror = function () {
                wsConnected = false;
                startPolling();
            };
        } catch (err) {
            startPolling();
            setTimeout(connect, 3000);
        }
    }

    const form = document.getElementById('agent-chat-form');
    const input = document.getElementById('message-input');

    if (form && input) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const content = input.value.trim();
            if (!content) return;

            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ type: 'message', content: content }));
                input.value = '';
                return;
            }

            fetch(sendUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ content: content }),
            })
                .then(function (response) {
                    if (!response.ok) throw new Error('send failed');
                    return response.json();
                })
                .then(function (data) {
                    if (data.message) appendMessage(data.message);
                })
                .finally(function () {
                    input.value = '';
                });
        });
    }

    const statusSelect = document.getElementById('status-select');
    if (statusSelect) {
        statusSelect.addEventListener('change', function () {
            fetch('/inbox/conversations/' + conversationId + '/update/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ status: statusSelect.value }),
            });
        });
    }

    const assignSelect = document.getElementById('assign-select');
    if (assignSelect) {
        assignSelect.addEventListener('change', function () {
            fetch('/inbox/conversations/' + conversationId + '/update/', {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({
                    assigned_to: assignSelect.value || null,
                }),
            });
        });
    }

    connect();
    startPolling();
    messagesEl.scrollTop = messagesEl.scrollHeight;
})();
