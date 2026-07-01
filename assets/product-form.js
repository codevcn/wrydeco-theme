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

  const btn = form.querySelector('button[name="add"]');
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
        'Accept': 'application/json'
      },
      body: formData
    };

    fetch(window.Shopify.routes.root + 'cart/add.js', config)
      .then((response) => response.text())
      .then((text) => {
        const cleanJson = text.replace(/<!--[\s\S]*?-->/g, '').trim();
        return JSON.parse(cleanJson);
      })
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
          // If no toast, don't redirect immediately so they can see the animation
        }

        // Fly to cart animation
        const mainImage = document.querySelector('.product-gallery__main-item.is-active img.product-gallery__main-media');
        const cartIcon = document.querySelector('.header__icon--cart') || document.querySelector('.header__icon--cart svg');
        
        if (mainImage && cartIcon) {
          const clone = mainImage.cloneNode();
          const imgRect = mainImage.getBoundingClientRect();
          const cartRect = cartIcon.getBoundingClientRect();
          
          clone.style.position = 'fixed';
          clone.style.top = imgRect.top + 'px';
          clone.style.left = imgRect.left + 'px';
          clone.style.width = imgRect.width + 'px';
          clone.style.height = imgRect.height + 'px';
          clone.style.zIndex = '9999';
          clone.style.transition = 'all 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94)';
          clone.style.borderRadius = '8px';
          clone.style.objectFit = 'cover';
          clone.style.pointerEvents = 'none';
          document.body.appendChild(clone);
          
          // Force reflow
          clone.offsetHeight;
          
          clone.style.top = (cartRect.top + cartRect.height / 2 - 15) + 'px';
          clone.style.left = (cartRect.left + cartRect.width / 2 - 15) + 'px';
          clone.style.width = '30px';
          clone.style.height = '30px';
          clone.style.opacity = '0.1';
          clone.style.borderRadius = '50%';
          
          clone.addEventListener('transitionend', () => {
            clone.remove();
            
            // Trigger cart shake
            if (cartIcon.animate) {
              cartIcon.animate([
                { transform: 'translateX(0)' },
                { transform: 'translateX(-4px) rotate(-4deg)' },
                { transform: 'translateX(4px) rotate(4deg)' },
                { transform: 'translateX(-4px) rotate(-4deg)' },
                { transform: 'translateX(4px) rotate(4deg)' },
                { transform: 'translateX(-2px) rotate(-2deg)' },
                { transform: 'translateX(2px) rotate(2deg)' },
                { transform: 'translateX(0)' }
              ], {
                duration: 500,
                easing: 'ease-in-out'
              });
            }
          }, { once: true });
        }

        // Update header cart count
        fetch(window.Shopify.routes.root + 'cart.js')
          .then(res => res.text())
          .then(text => {
            const cleanJson = text.replace(/<!--[\s\S]*?-->/g, '').trim();
            return JSON.parse(cleanJson);
          })
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
