class SearchPopup extends HTMLElement {
  constructor() {
    super();
    this.overlay = this.querySelector('.search-popup__overlay');
    this.closeButton = this.querySelector('.search-popup__close');
    this.input = this.querySelector('.search-popup__input');
    this.resultsContainer = this.querySelector('.search-popup__results');
    this.recentContainer = this.querySelector('.search-popup__recent');
    this.recentList = this.querySelector('.search-popup__recent-list');
    this.predictiveList = this.querySelector('.search-popup__predictive-list');
    this.topResultsContainer = this.querySelector('.search-popup__top-results');
    this.viewAllContainer = this.querySelector('.search-popup__view-all');
    this.viewAllBtn = this.querySelector('.search-popup__view-all-btn');
    
    this.loadingSpinner = this.querySelector('.search-popup__loading');
    this.emptyState = this.querySelector('.search-popup__empty');
    this.initialState = this.querySelector('.search-popup__initial');
    
    this.storageKey = 'wrydeco_recently_searched';
    this.maxRecent = 8;
    this.debounceTimer = null;
    this.focusTimer = null;
    this.currentMode = '';
    this.defaultResultsHtml = this.predictiveList?.innerHTML || '';
    this.defaultRecentSearches = Array.from(this.predictiveList?.querySelectorAll('.search-product-card') || []).map(card => ({
      title: card.dataset.title,
      url: card.dataset.url,
      image: card.dataset.image
    }));
    
    this.bindEvents();
    this.renderRecentSearches();
  }

  bindEvents() {
    this.closeButton?.addEventListener('click', () => this.close());
    
    this.overlay?.addEventListener('click', (e) => {
      if (e.target === this.overlay) {
        this.close();
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen()) {
        this.close();
      }
    });

    this.input?.addEventListener('input', this.onInput.bind(this));

    this.recentList?.addEventListener('click', (event) => {
      const removeButton = event.target.closest('[data-remove-recent]');
      if (removeButton) {
        event.stopPropagation();
        this.removeRecentSearch(Number(removeButton.dataset.removeRecent));
        return;
      }

      const chip = event.target.closest('[data-recent-query]');
      if (chip) {
        this.input.value = chip.dataset.recentQuery;
        this.onInput();
      }
    });
    
    this.addEventListener('click', this.handleProductClick.bind(this));
  }
  
  isOpen() {
    return this.hasAttribute('open');
  }

  open() {
    if (this.isOpen()) return;

    this.setAttribute('open', '');
    document.body.style.overflow = 'hidden';
    clearTimeout(this.focusTimer);
    this.focusTimer = setTimeout(() => {
      this.input?.focus();
    }, 220);
  }

  close() {
    clearTimeout(this.focusTimer);
    this.removeAttribute('open');
    document.body.style.overflow = '';
  }
  
  onInput() {
    clearTimeout(this.debounceTimer);
    const query = this.input.value.trim();
    
    if (query.length < 2) {
      this.showRecentSearches();
      return;
    }
    
    this.showLoading();
    
    this.debounceTimer = setTimeout(() => {
      this.performSearch(query);
    }, 300);
  }
  
  async performSearch(query) {
    try {
      const response = await fetch(`/search/suggest.json?q=${encodeURIComponent(query)}&resources[type]=product&resources[limit]=10&resources[options][unavailable_products]=last`);
      if (!response.ok) throw new Error('Search failed');
      
      const data = await response.json();
      const products = data.resources.results.products;
      
      this.renderPredictiveResults(products, query);
    } catch (error) {
      console.error('Predictive Search Error:', error);
      this.showEmptyState();
    }
  }
  
  renderPredictiveResults(products, query) {
    this.hideAllSections();
    this.currentMode = 'results';
    
    if (!products || products.length === 0) {
      this.showEmptyState();
      return;
    }
    
    this.predictiveList.innerHTML = products.map((product, index) => this.createProductCardHtml(product, index, query)).join('');
    this.predictiveList.style.display = 'grid';
    if (this.topResultsContainer) this.topResultsContainer.style.display = 'block';
    
    if (this.viewAllContainer && this.viewAllBtn) {
      this.viewAllBtn.href = `/search?q=${encodeURIComponent(query)}&type=product`;
      this.viewAllContainer.style.display = 'block';
    }
  }
  
  renderRecentSearches() {
    const recent = this.getRecentSearches();
    const visibleRecent = recent.length > 0 ? recent : this.defaultRecentSearches;
    
    if (this.input.value.trim().length >= 2) {
      return; 
    }

    if (this.currentMode === 'recent') return;
    
    this.hideAllSections();
    this.currentMode = 'recent';
    
    if (visibleRecent.length > 0) {
      this.recentList.innerHTML = visibleRecent.slice(0, 4).map((product, index) => this.createRecentChipHtml(product, index)).join('');
      this.recentContainer.style.display = 'block';
    }

    this.predictiveList.innerHTML = recent.length > 0
      ? recent.slice(0, 4).map((product, index) => this.createProductCardHtml(product, index)).join('')
      : this.defaultResultsHtml;
    this.predictiveList.style.display = 'grid';
    if (this.topResultsContainer) this.topResultsContainer.style.display = 'block';
    if (this.viewAllContainer) this.viewAllContainer.style.display = 'block';
  }
  
  showRecentSearches() {
    this.renderRecentSearches();
  }
  
  showLoading() {
    this.hideAllSections();
    this.currentMode = 'loading';
    this.loadingSpinner.style.display = 'flex';
  }
  
  showEmptyState() {
    this.hideAllSections();
    this.currentMode = 'empty';
    this.emptyState.style.display = 'flex';
  }
  
  hideAllSections() {
    if (this.recentContainer) this.recentContainer.style.display = 'none';
    if (this.predictiveList) this.predictiveList.style.display = 'none';
    if (this.topResultsContainer) this.topResultsContainer.style.display = 'none';
    if (this.loadingSpinner) this.loadingSpinner.style.display = 'none';
    if (this.emptyState) this.emptyState.style.display = 'none';
    if (this.viewAllContainer) this.viewAllContainer.style.display = 'none';
    if (this.initialState) this.initialState.style.display = 'none';
  }
  
  getRecentSearches() {
    try {
      const data = localStorage.getItem(this.storageKey);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.error('Failed to parse recent searches', e);
      return [];
    }
  }

  removeRecentSearch(index) {
    const recent = this.getRecentSearches();
    recent.splice(index, 1);
    localStorage.setItem(this.storageKey, JSON.stringify(recent));
    this.currentMode = '';
    this.renderRecentSearches();
  }

  createRecentChipHtml(product, index) {
    const title = this.escapeHtml(product.title || 'Recent search');
    const imageUrl = product.image || product.featured_image || '';
    const image = imageUrl ? `<img src="${this.escapeHtml(imageUrl)}" alt="" width="32" height="32">` : '';
    return `<button type="button" class="search-popup__recent-chip" data-recent-query="${title}">${image}<span>${title}</span><i data-remove-recent="${index}" aria-label="Remove ${title}">&times;</i></button>`;
  }

  escapeHtml(value) {
    return String(value || '').replace(/[&<>"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[character]);
  }
  
  saveToRecentSearches(product) {
    let recent = this.getRecentSearches();
    
    // Remove if already exists
    recent = recent.filter(p => p.url !== product.url);
    
    // Add to top
    recent.unshift(product);
    
    // Limit to maxRecent
    recent = recent.slice(0, this.maxRecent);
    
    try {
      localStorage.setItem(this.storageKey, JSON.stringify(recent));
    } catch (e) {
      console.error('Failed to save recent searches', e);
    }
  }
  
  handleProductClick(e) {
    const card = e.target.closest('.search-product-card');
    if (!card) return;
    
    const product = {
      title: card.dataset.title,
      url: card.dataset.url,
      image: card.dataset.image
    };
    
    this.saveToRecentSearches(product);
  }
  
  createProductCardHtml(product, index = 0, query = '') {
    const imageUrl = product.image || product.featured_image || ''; 
    const imageHtml = imageUrl 
      ? `<img src="${imageUrl}" alt="${product.title.replace(/"/g, '&quot;')}" width="150" height="150" loading="lazy">`
      : `<div class="search-product-card__placeholder">No Image</div>`;
      
    let displayTitle = product.title;
    if (query) {
      const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
      displayTitle = displayTitle.replace(regex, '<mark>$1</mark>');
    }
      
    const productType = this.escapeHtml(product.type || product.product_type || 'Handcrafted furniture');
    const rawPrice = String(product.price || '');
    const formattedPrice = rawPrice && /^\d/.test(rawPrice) ? `$${rawPrice}` : rawPrice;
    const price = formattedPrice ? `<span class="search-product-card__price">${this.escapeHtml(formattedPrice)}</span>` : '';

    return `
      <a href="${product.url}" class="search-product-card" data-title="${product.title.replace(/"/g, '&quot;')}" data-url="${product.url}" data-image="${imageUrl}" style="animation-delay: ${index * 0.05}s">
        <div class="search-product-card__image">
          ${imageHtml}
        </div>
        <div class="search-product-card__info">
          <span class="search-product-card__type">${productType}</span>
          <span class="search-product-card__title">${displayTitle}</span>
          ${price}
        </div>
      </a>
    `;
  }
}

if (!customElements.get('search-popup')) {
  customElements.define('search-popup', SearchPopup);
}

window.openSearchPopup = function(e) {
  if (e) e.preventDefault();
  const popup = document.querySelector('search-popup');
  if (popup) {
    popup.open();
  }
};
