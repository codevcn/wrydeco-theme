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

  const btn = form.querySelector('.custom-add-to-cart-btn');
  const errorWrapper = form.querySelector('[data-error-message-wrapper]');
  const errorMessage = form.querySelector('[data-error-message]');
  
  let originalBtnHtml = '';

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    
    errorWrapper.hidden = true;
    
    if (btn) {
      originalBtnHtml = btn.innerHTML;
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
        if (window.showToast) {
          window.showToast({
            message: 'Item added to your cart.',
            type: 'success',
            position: 'bottom-right'
          });
        } else {
          window.location.href = window.Shopify.routes.root + 'cart';
        }

        // Update header cart count
        fetch(window.Shopify.routes.root + 'cart.js')
          .then(res => res.json())
          .then(cart => {
            const cartIcon = document.querySelector('.header__icon--cart');
            if (cartIcon) {
              let bubble = cartIcon.querySelector('.cart-count-bubble');
              if (cart.item_count > 0) {
                if (!bubble) {
                  bubble = document.createElement('div');
                  bubble.className = 'cart-count-bubble';
                  bubble.innerHTML = '<span></span>';
                  cartIcon.appendChild(bubble);
                }
                bubble.querySelector('span').textContent = cart.item_count;
              } else if (bubble) {
                bubble.remove();
              }
            }
          });
      })
      .catch((error) => {
        errorWrapper.hidden = false;
        errorMessage.textContent = error.message;
      })
      .finally(() => {
        if (btn) {
          btn.removeAttribute('aria-disabled');
          btn.classList.remove('loading');
          // Restore original button text
          btn.innerHTML = originalBtnHtml;
        }
      });
  });
});
