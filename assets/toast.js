(function () {
  const containerId = 'global-toast-container';

  function createContainer(position) {
    let container = document.getElementById(containerId);
    if (!container) {
      container = document.createElement('div');
      container.id = containerId;
      document.body.appendChild(container);
    }
    container.setAttribute('data-position', position || 'bottom-left');
    return container;
  }

  const icons = {
    success: `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 6L9 17l-5-5"/></svg>`,
    error: `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 6L6 18M6 6l12 12"/></svg>`,
    warning: `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="m21.73 18l-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3M12 9v4m0 4h.01"/></svg>`,
    info: `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M12 16v-4m0-4h.01"/></g></svg>`
  };

  const closeIcon = `<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 6L6 18M6 6l12 12"/></svg>`;


  window.showToast = function (options) {
    const {
      message = '',
      type = 'info', // success, error, warning, info
      position = 'bottom-left',
      duration = 4000
    } = options;

    const container = createContainer(position);

    const toast = document.createElement('div');
    toast.className = `wry-toast wry-toast--${type}`;

    toast.innerHTML = `
      <div class="wry-toast__core">
        <div class="wry-toast__icon-wrapper">
          ${icons[type] || icons.info}
        </div>
        <div class="wry-toast__divider"></div>
        <div class="wry-toast__message">${message}</div>
        <button class="wry-toast__close" aria-label="Close">
          ${closeIcon}
        </button>
      </div>
    `;

    container.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        toast.classList.add('wry-toast--visible');
      });
    });

    const closeToast = () => {
      toast.classList.remove('wry-toast--visible');
      toast.classList.add('wry-toast--exit');
      toast.addEventListener('transitionend', () => {
        if (toast.parentElement) {
          toast.remove();
        }
      });
    };

    const closeBtn = toast.querySelector('.wry-toast__close');
    closeBtn.addEventListener('click', closeToast);

    if (duration > 0) {
      setTimeout(closeToast, duration);
    }
  };
})();
