(function () {
    const messagesEl = document.getElementById('chat-messages');
    if (!messagesEl) return;

    const conversationId = messagesEl.dataset.conversationId;
    const wsScheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = wsScheme + '//' + window.location.host + '/ws/chat/' + conversationId + '/';

    let socket = null;

    function connect() {
        socket = new WebSocket(wsUrl);
        socket.onmessage = function (e) {
            const data = JSON.parse(e.data);
            appendMessage(data);
        };
        socket.onclose = function () {
            setTimeout(connect, 3000);
        };
    }

    function appendMessage(msg) {
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
        bubble.className = 'message-bubble';
        bubble.textContent = msg.content;

        div.appendChild(meta);
        div.appendChild(bubble);
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    }

    function getCsrfToken() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    const form = document.getElementById('agent-chat-form');
    const input = document.getElementById('message-input');

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        const content = input.value.trim();
        if (!content) return;

        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: 'message', content: content }));
        } else {
            fetch('/inbox/conversations/' + conversationId + '/send/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({ content: content }),
            });
        }
        input.value = '';
    });

    const statusSelect = document.getElementById('status-select');
    if (statusSelect) {
        statusSelect.addEventListener('change', function () {
            fetch('/inbox/conversations/' + conversationId + '/update/', {
                method: 'POST',
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
    messagesEl.scrollTop = messagesEl.scrollHeight;
})();
