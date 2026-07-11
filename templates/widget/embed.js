(function() {
    const script = document.currentScript;
    const host = script
        ? new URL(script.src).origin
        : window.location.protocol + '//' + window.location.host;
    const widgetKey = "{{ widget_key|escapejs }}";
    const widgetUrl = host + '/widget/chat/?key=' + encodeURIComponent(widgetKey) + '&v=2';

    const launcher = document.createElement('div');
    launcher.id = 'morse-widget-launcher';
    launcher.className = 'widget-launcher';
    launcher.innerHTML = '<span class="launcher-icon">💬</span>';
    launcher.setAttribute('aria-label', 'Open chat');

    const frame = document.createElement('div');
    frame.id = 'morse-widget-frame';
    frame.className = 'widget-frame hidden';
    frame.innerHTML = '<button class="widget-close" aria-label="Close chat">×</button><iframe src="' + widgetUrl + '" title="Morse chat"></iframe>';

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = host + '/static/css/widget.css';
    document.head.appendChild(link);

    document.body.appendChild(launcher);
    document.body.appendChild(frame);

    launcher.addEventListener('click', () => frame.classList.remove('hidden'));
    frame.querySelector('.widget-close').addEventListener('click', () => frame.classList.add('hidden'));
})();
