{% load i18n %}
{% trans "Support" as launcher_label_raw %}
{% trans "Chat with Morse" as open_label_raw %}
{% trans "Close chat" as close_label_raw %}
{% trans "Morse chat" as chat_title_raw %}
(function() {
    // morse-visitor-persist-v11 — /widget/embed.js visitor identity (parent localStorage)
    // Labels use percent-encoding so Persian stays correct even if charset is misdetected.
    var script = document.currentScript;
    var host = script
        ? new URL(script.src).origin
        : window.location.protocol + '//' + window.location.host;
    var widgetKey = "{{ widget_key|escapejs }}";
    var launcherLabel = decodeURIComponent("{{ launcher_label_raw|urlencode }}");
    var openLabel = decodeURIComponent("{{ open_label_raw|urlencode }}");
    var closeLabel = decodeURIComponent("{{ close_label_raw|urlencode }}");
    var chatTitle = decodeURIComponent("{{ chat_title_raw|urlencode }}");

    function generateUuid() {
        if (window.crypto && typeof window.crypto.randomUUID === 'function') {
            return window.crypto.randomUUID();
        }
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
            var r = (Math.random() * 16) | 0;
            var v = c === 'x' ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }

    // 1) Read localStorage key "morse_visitor_id"
    var visitorId = null;
    try {
        visitorId = localStorage.getItem('morse_visitor_id');
    } catch (err) {
        console.warn('[Morse embed] localStorage.getItem failed', err);
        visitorId = null;
    }

    // 2) If missing, generate UUID
    // 3) Save it to parent localStorage
    if (!visitorId) {
        visitorId = generateUuid();
        try {
            localStorage.setItem('morse_visitor_id', visitorId);
        } catch (err) {
            console.error('[Morse embed] failed to save morse_visitor_id', err);
        }
    }

    // 4) Add visitor_id=<id> to iframe URL
    var widgetUrl =
        host +
        '/widget/chat/?key=' +
        encodeURIComponent(widgetKey) +
        '&visitor_id=' +
        encodeURIComponent(visitorId) +
        '&v=11';

    var stack = document.createElement('div');
    stack.id = 'morse-widget-launcher-stack';
    stack.className = 'widget-launcher-stack';

    var label = document.createElement('span');
    label.className = 'widget-launcher-label';
    label.textContent = launcherLabel;

    var launcher = document.createElement('button');
    launcher.type = 'button';
    launcher.id = 'morse-widget-launcher';
    launcher.className = 'widget-launcher';
    launcher.setAttribute('aria-label', openLabel);
    launcher.innerHTML =
        '<span class="launcher-pulse" aria-hidden="true"></span>' +
        '<span class="launcher-monogram" aria-hidden="true">M</span>';

    stack.appendChild(label);
    stack.appendChild(launcher);

    var frame = document.createElement('div');
    frame.id = 'morse-widget-frame';
    frame.className = 'widget-frame hidden';
    frame.innerHTML =
        '<button type="button" class="widget-close" aria-label="' + closeLabel + '">×</button>' +
        '<iframe src="' + widgetUrl + '" title="' + chatTitle + '" allow="microphone *"></iframe>';

    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = host + '/static/css/widget.css?v=genie1';
    document.head.appendChild(link);

    document.body.appendChild(stack);
    document.body.appendChild(frame);

    launcher.addEventListener('click', function () {
        frame.classList.remove('hidden');
    });
    frame.querySelector('.widget-close').addEventListener('click', function () {
        frame.classList.add('hidden');
    });
})();
