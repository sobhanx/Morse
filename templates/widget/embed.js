{% load i18n %}
(function() {
    const script = document.currentScript;
    const host = script
        ? new URL(script.src).origin
        : window.location.protocol + '//' + window.location.host;
    const widgetKey = "{{ widget_key|escapejs }}";
    const widgetUrl = host + '/widget/chat/?key=' + encodeURIComponent(widgetKey) + '&v=3';
    const brandLabel = "{{ brand_name|escapejs }}";
    const openLabel = "{% trans 'Chat with Morse' %}";
    const closeLabel = "{% trans 'Close chat' %}";
    const chatTitle = "{% trans 'Morse chat' %}";

    const stack = document.createElement('div');
    stack.id = 'morse-widget-launcher-stack';
    stack.className = 'widget-launcher-stack';

    const label = document.createElement('span');
    label.className = 'widget-launcher-label';
    label.textContent = brandLabel;

    const launcher = document.createElement('button');
    launcher.type = 'button';
    launcher.id = 'morse-widget-launcher';
    launcher.className = 'widget-launcher';
    launcher.setAttribute('aria-label', openLabel);
    launcher.innerHTML =
        '<span class="launcher-pulse" aria-hidden="true"></span>' +
        '<span class="launcher-monogram" aria-hidden="true">M</span>';

    stack.appendChild(label);
    stack.appendChild(launcher);

    const frame = document.createElement('div');
    frame.id = 'morse-widget-frame';
    frame.className = 'widget-frame hidden';
    frame.innerHTML =
        '<button type="button" class="widget-close" aria-label="' + closeLabel + '">×</button>' +
        '<iframe src="' + widgetUrl + '" title="' + chatTitle + '"></iframe>';

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = host + '/static/css/widget.css';
    document.head.appendChild(link);

    document.body.appendChild(stack);
    document.body.appendChild(frame);

    launcher.addEventListener('click', () => frame.classList.remove('hidden'));
    frame.querySelector('.widget-close').addEventListener('click', () => frame.classList.add('hidden'));
})();
