const SaleEvent = {
  init() {
    const notice = document.querySelector('[data-sale-notice]');
    if (!notice) return;

    const isTargetCollection = notice.dataset.inCollection === 'true';
    if (!isTargetCollection) return; // Only applies to specific collection

    const startTime = new Date(notice.dataset.startTime).getTime();
    const endTime = new Date(notice.dataset.endTime).getTime();
    const now = Date.now();

    // Check time condition
    if (now >= startTime && now <= endTime) {
      notice.classList.add('is-visible');
    } else {
      notice.classList.remove('is-visible');
    }
    
    // Note: minimum subtotal logic is typically handled at checkout, 
    // but the UI notice is visible to encourage adding to cart.
  }
};

document.addEventListener('DOMContentLoaded', SaleEvent.init);
window.SaleEvent = SaleEvent;
