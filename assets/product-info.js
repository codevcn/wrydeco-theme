document.addEventListener('DOMContentLoaded', () => {
  const container = document.querySelector('section[data-product-id]');
  if (!container) return;

  const stateEl = container.querySelector('[data-product-state]');
  if (!stateEl) return;
  
  let state = JSON.parse(stateEl.textContent);
  
  const variantRadios = container.querySelectorAll('.variant-swatch input[type="radio"]');
  variantRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      onVariantChange();
    });
  });

  function onVariantChange() {
    const selectedOptions = Array.from(container.querySelectorAll('.variant-swatch input[type="radio"]:checked')).map(el => el.value);
    
    // We need to fetch the variants to find the matching one.
    // However, without a pre-loaded variant array in JS, we can just use the Section Rendering API 
    // to query Shopify with the selected options or URL params. 
    // Wait, the standard OS 2.0 way is to build the URL with ?variant=ID, but we only have option values here.
    // We should have included the variants JSON in the HTML. Since we didn't, let's just fetch the product.json
    
    fetch(`${state.url}.js`)
      .then(response => response.json())
      .then(product => {
        const matchedVariant = product.variants.find(variant => {
          return selectedOptions.every((val, index) => variant.options[index] === val);
        });

        if (matchedVariant) {
          state.selectedVariantId = matchedVariant.id;
          updateURL(matchedVariant.id);
          renderProductInfo(matchedVariant.id);
        }
      });
  }

  function updateURL(variantId) {
    if (!variantId) return;
    window.history.replaceState({ }, '', `${state.url}?variant=${variantId}`);
  }

  function renderProductInfo(variantId) {
    const sectionId = container.id.replace('MainProduct-', '');
    const url = `${state.url}?variant=${variantId}&section_id=${sectionId}`;

    fetch(url)
      .then(response => response.text())
      .then(responseText => {
        const html = new DOMParser().parseFromString(responseText, 'text/html');
        const newContainer = html.getElementById(`MainProduct-${sectionId}`);
        if (!newContainer) return;

        // Update elements
        const updateElements = [
          '[data-annualized-cost]',
          '[data-sku]',
          '[data-price-container]',
          '[data-sale-notice]',
          '[data-add-to-cart-text]',
          '[data-inventory-status]'
        ];

        updateElements.forEach(selector => {
          const current = container.querySelector(selector);
          const next = newContainer.querySelector(selector);
          if (current && next) {
            current.innerHTML = next.innerHTML;
            // Also copy classes and dataset
            current.className = next.className;
            Object.assign(current.dataset, next.dataset);
          }
        });

        // Update variant option labels
        container.querySelectorAll('.variant-option__selected-value').forEach((label, idx) => {
          const nextLabel = newContainer.querySelectorAll('.variant-option__selected-value')[idx];
          if (nextLabel) label.innerHTML = nextLabel.innerHTML;
        });

        // Update hidden variant ID input
        const variantInput = container.querySelector('[data-variant-id]');
        if (variantInput) variantInput.value = variantId;

        // Update add to cart button state
        const addToCartBtn = container.querySelector('.btn--add-to-cart');
        const nextAddToCartBtn = newContainer.querySelector('.btn--add-to-cart');
        if (addToCartBtn && nextAddToCartBtn) {
          addToCartBtn.disabled = nextAddToCartBtn.disabled;
        }

        // Trigger custom event for gallery to sync
        document.dispatchEvent(new CustomEvent('product:variant-change', {
          detail: { variantId }
        }));
        
        // Re-run sale event logic on the newly injected notice
        if (window.SaleEvent && typeof window.SaleEvent.init === 'function') {
          window.SaleEvent.init();
        }
      });
  }
});
