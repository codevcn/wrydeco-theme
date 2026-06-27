document.addEventListener('DOMContentLoaded', () => {
  // Quantity Selector logic
  const qtyWrappers = document.querySelectorAll('[data-quantity-selector]');
  qtyWrappers.forEach(wrapper => {
    const input = wrapper.querySelector('input');
    const btns = wrapper.querySelectorAll('button');
    
    btns.forEach(btn => {
      btn.addEventListener('click', () => {
        let val = parseInt(input.value) || 1;
        if (btn.dataset.action === 'increase') {
          val++;
        } else if (btn.dataset.action === 'decrease') {
          val = Math.max(1, val - 1);
        }
        input.value = val;
      });
    });
  });

  // AJAX Add to cart logic
  const form = document.querySelector('form[data-type="add-to-cart-form"]');
  if (!form) return;

  const btn = form.querySelector('.btn--add-to-cart');
  const errorWrapper = form.querySelector('[data-error-message-wrapper]');
  const errorMessage = form.querySelector('[data-error-message]');

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    
    errorWrapper.hidden = true;
    
    if (btn) {
      btn.setAttribute('aria-disabled', true);
      btn.classList.add('loading');
      btn.innerHTML = '<span class="spinner"></span> Loading...'; // Simple spinner text for demo
    }

    const formData = new FormData(form);
    const config = {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/javascript'
      },
      body: formData
    };

    fetch(window.Shopify.routes.root + 'cart/add.js', config)
      .then((response) => response.json())
      .then((response) => {
        if (response.status) {
          throw new Error(response.description);
        }
        // Success
        window.location.href = window.Shopify.routes.root + 'cart';
      })
      .catch((error) => {
        errorWrapper.hidden = false;
        errorMessage.textContent = error.message;
      })
      .finally(() => {
        if (btn) {
          btn.removeAttribute('aria-disabled');
          btn.classList.remove('loading');
          // Reset button text
          const btnText = btn.querySelector('[data-add-to-cart-text]');
          btn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg> <span data-add-to-cart-text>Add to cart</span>`;
        }
      });
  });
});
