(function () {
    const messagesEl = document.getElementById('widget-messages');
    if (!messagesEl) return;

    const conversationId = messagesEl.dataset.conversationId;
    const widgetKey = messagesEl.dataset.widgetKey;
    if (!conversationId || !widgetKey) return;

    const wsScheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = wsScheme + '//' + window.location.host + '/ws/chat/' + conversationId + '/?key=' + encodeURIComponent(widgetKey);
    const sendUrl = '/widget/conversations/' + conversationId + '/send/?key=' + encodeURIComponent(widgetKey);

    let socket = null;
    let sending = false;

    const form = document.getElementById('widget-form');
    const input = document.getElementById('widget-message-input');
    const sendBtn = document.getElementById('widget-send-btn');

    function appendMessage(msg) {
        if (!msg || !msg.content) return;
        if (msg.id && messagesEl.querySelector('[data-id="' + msg.id + '"]')) return;

        const div = document.createElement('div');
        div.className = 'widget-message widget-message-' + (msg.sender_type || 'visitor');
        if (msg.id) div.dataset.id = msg.id;

        const bubble = document.createElement('div');
        bubble.className = 'widget-bubble';
        bubble.textContent = msg.content;

        div.appendChild(bubble);
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function sendViaHttp(content) {
        return fetch(sendUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ content: content }),
        }).then(function (response) {
            if (!response.ok) {
                return response.text().then(function (text) {
                    throw new Error(text || 'Send failed');
                });
            }
            return response.json();
        }).then(function (data) {
            if (data.message) {
                appendMessage(data.message);
            }
        });
    }

    function handleSend() {
        if (!input || sending) return;
        const content = input.value.trim();
        if (!content) return;

        sending = true;
        input.value = '';
        if (sendBtn) sendBtn.disabled = true;

        sendViaHttp(content)
            .catch(function () {
                input.value = content;
            })
            .finally(function () {
                sending = false;
                if (sendBtn) sendBtn.disabled = false;
                input.focus();
            });
    }

    if (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            handleSend();
        });
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', function (e) {
            e.preventDefault();
            handleSend();
        });
    }

    if (input) {
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
            }
        });
    }

    const saveBtn = document.getElementById('save-contact-btn');
    const prechat = document.getElementById('widget-prechat');

    if (saveBtn) {
        saveBtn.addEventListener('click', function () {
            const name = document.getElementById('visitor-name').value.trim();
            const email = document.getElementById('visitor-email').value.trim();

            fetch('/widget/contact/?key=' + encodeURIComponent(widgetKey), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ name: name, email: email }),
            }).then(function () {
                if (prechat) prechat.style.display = 'none';
            });
        });
    }

    function connect() {
        try {
            socket = new WebSocket(wsUrl);
            socket.onmessage = function (e) {
                try {
                    appendMessage(JSON.parse(e.data));
                } catch (err) {
                    /* ignore malformed payloads */
                }
            };
            socket.onclose = function () {
                setTimeout(connect, 3000);
            };
        } catch (err) {
            setTimeout(connect, 3000);
        }
    }

    connect();
    if (input) input.focus();
    messagesEl.scrollTop = messagesEl.scrollHeight;
})();
