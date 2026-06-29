(function() {
  const ICONS = {
    success: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`,
    error: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`,
    info: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>`
  };

  function createContainer(position) {
    let container = document.getElementById('global-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'global-toast-container';
      document.body.appendChild(container);
    }
    // Update position if it changes (though usually one position is used per session)
    container.setAttribute('data-position', position);
    return container;
  }

  window.showToast = function(options) {
    const {
      message = '',
      type = 'success', // success, error, info
      position = 'bottom-right', // top-left, top-right, bottom-left, bottom-right
      duration = 4000
    } = options;

    const container = createContainer(position);

    // Create Toast Shell (Outer Bezel)
    const toast = document.createElement('div');
    toast.className = 'wry-toast';

    // Create Toast Core (Inner)
    const core = document.createElement('div');
    core.className = 'wry-toast__core';

    // Icon
    const iconWrapper = document.createElement('div');
    iconWrapper.className = `wry-toast__icon wry-toast__icon--${type}`;
    iconWrapper.innerHTML = ICONS[type] || ICONS.info;

    // Message
    const text = document.createElement('div');
    text.className = 'wry-toast__message';
    text.textContent = message;

    // Close Button
    const closeBtn = document.createElement('button');
    closeBtn.className = 'wry-toast__close';
    closeBtn.setAttribute('aria-label', 'Close notification');
    closeBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>`;

    core.appendChild(iconWrapper);
    core.appendChild(text);
    core.appendChild(closeBtn);
    toast.appendChild(core);

    // Append to container (if top, prepend so it stacks downwards, if bottom append so it stacks upwards)
    if (position.startsWith('top')) {
      container.prepend(toast);
    } else {
      container.appendChild(toast);
    }

    // Trigger Entry Animation (RequestAnimationFrame ensures DOM is painted before adding visible class)
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        toast.classList.add('wry-toast--visible');
      });
    });

    let timeoutId;

    const removeToast = () => {
      toast.classList.remove('wry-toast--visible');
      toast.classList.add('wry-toast--exit');
      
      // Wait for exit transition (500ms)
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 500);
    };

    closeBtn.addEventListener('click', () => {
      clearTimeout(timeoutId);
      removeToast();
    });

    if (duration > 0) {
      timeoutId = setTimeout(removeToast, duration);
    }
  };
})();
