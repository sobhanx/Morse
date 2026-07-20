(function () {
    const messagesEl = document.getElementById('widget-messages');
    if (!messagesEl) return;

    const conversationId = messagesEl.dataset.conversationId;
    const widgetKey = messagesEl.dataset.widgetKey;
    if (!conversationId || !widgetKey) return;

    // Prefer stored identity (parent may have set global key), then server id.
    const GLOBAL_STORAGE_KEY = 'morse_visitor_id';
    const VISITOR_STORAGE_KEY = 'morse_visitor_id:' + widgetKey;
    const VISITOR_COOKIE_NAME = 'morse_vid_' + widgetKey.replace(/[^a-zA-Z0-9_-]/g, '');
    const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

    function generateVisitorId() {
        if (window.crypto && typeof window.crypto.randomUUID === 'function') {
            return window.crypto.randomUUID();
        }
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
            const r = (Math.random() * 16) | 0;
            const v = c === 'x' ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }

    function readCookieVisitorId() {
        const parts = (document.cookie || '').split(';');
        for (let i = 0; i < parts.length; i++) {
            const part = parts[i].trim();
            if (part.indexOf(VISITOR_COOKIE_NAME + '=') === 0) {
                return decodeURIComponent(part.slice(VISITOR_COOKIE_NAME.length + 1));
            }
        }
        return null;
    }

    function writeCookieVisitorId(id) {
        try {
            document.cookie =
                VISITOR_COOKIE_NAME +
                '=' +
                encodeURIComponent(id) +
                '; path=/; max-age=' +
                60 * 60 * 24 * 365 +
                '; SameSite=Lax';
        } catch (err) {
            /* ignore */
        }
    }

    function readStoredVisitorId() {
        try {
            const keyed = window.localStorage.getItem(VISITOR_STORAGE_KEY);
            if (keyed && UUID_RE.test(keyed)) return keyed;
            const globalId = window.localStorage.getItem(GLOBAL_STORAGE_KEY);
            if (globalId && UUID_RE.test(globalId)) return globalId;
        } catch (err) {
            /* ignore */
        }
        const fromCookie = readCookieVisitorId();
        return fromCookie && UUID_RE.test(fromCookie) ? fromCookie : null;
    }

    function writeStoredVisitorId(id) {
        if (!id || !UUID_RE.test(id)) return;
        try {
            window.localStorage.setItem(VISITOR_STORAGE_KEY, id);
            window.localStorage.setItem(GLOBAL_STORAGE_KEY, id);
        } catch (err) {
            /* ignore quota / private mode */
        }
        writeCookieVisitorId(id);
    }

    // Prefer server-resolved id (from URL visitor_id), then stored, then generate once.
    let visitorId =
        (messagesEl.dataset.visitorId && UUID_RE.test(messagesEl.dataset.visitorId)
            ? messagesEl.dataset.visitorId
            : null) ||
        readStoredVisitorId() ||
        generateVisitorId();
    writeStoredVisitorId(visitorId);

    function withVisitorQuery(url) {
        const joiner = url.indexOf('?') === -1 ? '?' : '&';
        return (
            url +
            joiner +
            'visitor_id=' +
            encodeURIComponent(visitorId) +
            '&key=' +
            encodeURIComponent(widgetKey)
        );
    }

    function visitorHeaders(extra) {
        const headers = Object.assign({}, extra || {});
        headers['X-Visitor-Id'] = visitorId;
        return headers;
    }

    const wsScheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl =
        wsScheme +
        '//' +
        window.location.host +
        '/ws/chat/' +
        conversationId +
        '/?key=' +
        encodeURIComponent(widgetKey) +
        '&visitor_id=' +
        encodeURIComponent(visitorId);
    const sendUrl = withVisitorQuery('/widget/conversations/' + conversationId + '/send/');
    const voiceUrl = withVisitorQuery('/widget/conversations/' + conversationId + '/voice/');
    const contactUrl = withVisitorQuery('/widget/contact/');

    let socket = null;
    let sending = false;

    const form = document.getElementById('widget-form');
    const input = document.getElementById('widget-message-input');
    const sendBtn = document.getElementById('widget-send-btn');
    const micBtn = document.getElementById('widget-mic-btn');
    const recordingEl = document.getElementById('widget-recording');
    const timerEl = document.getElementById('widget-recording-timer');
    const cancelRecBtn = document.getElementById('widget-cancel-recording');
    const stopRecBtn = document.getElementById('widget-stop-recording');

    const maxVoiceSeconds = Math.min(
        parseInt((form && form.dataset.maxVoiceSeconds) || '60', 10) || 60,
        60
    );
    const msgMicDenied = (form && form.dataset.msgMicDenied) || 'Microphone access is required.';
    const msgMicUnsupported = (form && form.dataset.msgMicUnsupported) || 'Voice recording is not supported.';
    const msgVoiceFailed = (form && form.dataset.msgVoiceFailed) || 'Could not send voice message.';

    let mediaRecorder = null;
    let mediaStream = null;
    let audioChunks = [];
    let recordingStartedAt = 0;
    let recordingTimer = null;
    let discardRecording = false;

    function formatDuration(seconds) {
        const s = Math.max(0, Math.floor(seconds));
        const m = Math.floor(s / 60);
        const rem = s % 60;
        return m + ':' + String(rem).padStart(2, '0');
    }

    function audioSrc(url) {
        if (!url) return url;
        return withVisitorQuery(url);
    }

    function appendMessage(msg) {
        if (!msg) return;
        const isAudio = msg.message_type === 'audio' && msg.audio_url;
        if (!isAudio && !msg.content) return;
        if (msg.id && messagesEl.querySelector('[data-id="' + msg.id + '"]')) return;

        const div = document.createElement('div');
        div.className = 'widget-message widget-message-' + (msg.sender_type || 'visitor');
        if (msg.id) div.dataset.id = msg.id;

        const bubble = document.createElement('div');
        bubble.className = 'widget-bubble' + (isAudio ? ' widget-bubble-audio' : '');

        if (isAudio) {
            const audio = document.createElement('audio');
            audio.className = 'widget-audio';
            audio.controls = true;
            audio.preload = 'metadata';
            const source = document.createElement('source');
            source.src = audioSrc(msg.audio_url);
            if (msg.audio_mime_type) {
                source.type = msg.audio_mime_type;
            }
            audio.appendChild(source);
            bubble.appendChild(audio);
            if (msg.duration_seconds) {
                const dur = document.createElement('span');
                dur.className = 'widget-audio-duration';
                dur.textContent = msg.duration_seconds + 's';
                bubble.appendChild(dur);
            }
        } else {
            bubble.textContent = msg.content;
        }

        div.appendChild(bubble);
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function sendViaHttp(content) {
        return fetch(sendUrl, {
            method: 'POST',
            headers: visitorHeaders({ 'Content-Type': 'application/json' }),
            credentials: 'include',
            body: JSON.stringify({ content: content, visitor_id: visitorId }),
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
        if (!input || sending || (mediaRecorder && mediaRecorder.state === 'recording')) return;
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

    function pickMimeType() {
        if (!window.MediaRecorder) return '';
        const ua = navigator.userAgent || '';
        const isApple = /iPad|iPhone|iPod|Macintosh/.test(ua) &&
            !/Chrome|CriOS|FxiOS|Edg/.test(ua);
        const candidates = isApple
            ? ['audio/mp4', 'audio/aac', 'audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus']
            : ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4', 'audio/aac'];
        for (let i = 0; i < candidates.length; i++) {
            if (MediaRecorder.isTypeSupported(candidates[i])) {
                return candidates[i];
            }
        }
        return '';
    }

    function mimeToExt(mimeType) {
        if (!mimeType) return 'webm';
        if (mimeType.indexOf('ogg') !== -1) return 'ogg';
        if (mimeType.indexOf('mp4') !== -1 || mimeType.indexOf('aac') !== -1) return 'm4a';
        if (mimeType.indexOf('mpeg') !== -1) return 'mp3';
        if (mimeType.indexOf('wav') !== -1) return 'wav';
        return 'webm';
    }

    function setRecordingUi(active) {
        if (recordingEl) recordingEl.hidden = !active;
        if (input) input.hidden = active;
        if (sendBtn) sendBtn.hidden = active;
        if (micBtn) {
            micBtn.hidden = active;
            micBtn.disabled = active;
        }
    }

    function stopTracks() {
        if (mediaStream) {
            mediaStream.getTracks().forEach(function (t) {
                t.stop();
            });
            mediaStream = null;
        }
    }

    function clearRecordingTimer() {
        if (recordingTimer) {
            clearInterval(recordingTimer);
            recordingTimer = null;
        }
    }

    function updateTimer() {
        if (!timerEl || !recordingStartedAt) return;
        const elapsed = Math.floor((Date.now() - recordingStartedAt) / 1000);
        timerEl.textContent = formatDuration(Math.min(elapsed, maxVoiceSeconds));
        if (elapsed >= maxVoiceSeconds && mediaRecorder && mediaRecorder.state === 'recording') {
            discardRecording = false;
            mediaRecorder.stop();
        }
    }

    function resetRecorderState() {
        clearRecordingTimer();
        stopTracks();
        mediaRecorder = null;
        audioChunks = [];
        recordingStartedAt = 0;
        setRecordingUi(false);
        if (timerEl) timerEl.textContent = '0:00';
    }

    function sendVoiceBlob(blob, durationSeconds) {
        const formData = new FormData();
        formData.append('audio', blob, 'voice.' + mimeToExt(blob.type));
        formData.append('duration_seconds', String(durationSeconds));
        formData.append('visitor_id', visitorId);

        sending = true;
        if (stopRecBtn) stopRecBtn.disabled = true;

        return fetch(voiceUrl, {
            method: 'POST',
            credentials: 'include',
            headers: visitorHeaders(),
            body: formData,
        }).then(function (response) {
            if (!response.ok) {
                return response.json().then(function (data) {
                    throw new Error((data && data.error) || 'Upload failed');
                }).catch(function (err) {
                    if (err.message && err.message !== 'Upload failed') throw err;
                    throw new Error('Upload failed');
                });
            }
            return response.json();
        }).then(function (data) {
            if (data.message) {
                appendMessage(data.message);
            }
        }).finally(function () {
            sending = false;
            if (stopRecBtn) stopRecBtn.disabled = false;
        });
    }

    function startRecording() {
        if (sending || mediaRecorder) return;
        if (!window.isSecureContext) {
            window.alert(msgMicUnsupported);
            return;
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
            window.alert(msgMicUnsupported);
            return;
        }

        navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
            mediaStream = stream;
            audioChunks = [];
            discardRecording = false;

            const mimeType = pickMimeType();
            try {
                mediaRecorder = mimeType
                    ? new MediaRecorder(stream, { mimeType: mimeType })
                    : new MediaRecorder(stream);
            } catch (err) {
                stopTracks();
                window.alert(msgMicUnsupported);
                return;
            }

            mediaRecorder.ondataavailable = function (e) {
                if (e.data && e.data.size > 0) {
                    audioChunks.push(e.data);
                }
            };

            mediaRecorder.onstop = function () {
                clearRecordingTimer();
                const durationSeconds = Math.max(
                    1,
                    Math.min(
                        maxVoiceSeconds,
                        Math.round((Date.now() - recordingStartedAt) / 1000) || 1
                    )
                );
                const shouldDiscard = discardRecording;
                const chunks = audioChunks.slice();
                const type = (mediaRecorder && mediaRecorder.mimeType) || (chunks[0] && chunks[0].type) || 'audio/webm';
                resetRecorderState();

                if (shouldDiscard || !chunks.length) {
                    return;
                }

                const blob = new Blob(chunks, { type: type });
                sendVoiceBlob(blob, durationSeconds).catch(function () {
                    window.alert(msgVoiceFailed);
                });
            };

            recordingStartedAt = Date.now();
            setRecordingUi(true);
            updateTimer();
            recordingTimer = setInterval(updateTimer, 250);
            mediaRecorder.start(250);
        }).catch(function (err) {
            const name = (err && err.name) || '';
            if (name === 'NotAllowedError' || name === 'PermissionDeniedError' || name === 'SecurityError') {
                window.alert(msgMicDenied);
                return;
            }
            if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
                window.alert(msgMicUnsupported);
                return;
            }
            window.alert(msgMicDenied);
        });
    }

    function cancelRecording() {
        if (!mediaRecorder || mediaRecorder.state === 'inactive') {
            resetRecorderState();
            return;
        }
        discardRecording = true;
        mediaRecorder.stop();
    }

    function finishRecording() {
        if (!mediaRecorder || mediaRecorder.state !== 'recording') return;
        discardRecording = false;
        mediaRecorder.stop();
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

    if (micBtn) {
        micBtn.addEventListener('click', function (e) {
            e.preventDefault();
            startRecording();
        });
    }

    if (cancelRecBtn) {
        cancelRecBtn.addEventListener('click', function (e) {
            e.preventDefault();
            cancelRecording();
        });
    }

    if (stopRecBtn) {
        stopRecBtn.addEventListener('click', function (e) {
            e.preventDefault();
            finishRecording();
        });
    }

    const saveBtn = document.getElementById('save-contact-btn');
    const prechat = document.getElementById('widget-prechat');

    if (saveBtn) {
        saveBtn.addEventListener('click', function () {
            const name = document.getElementById('visitor-name').value.trim();
            const email = document.getElementById('visitor-email').value.trim();

            fetch(contactUrl, {
                method: 'POST',
                headers: visitorHeaders({ 'Content-Type': 'application/json' }),
                credentials: 'include',
                body: JSON.stringify({ name: name, email: email, visitor_id: visitorId }),
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
