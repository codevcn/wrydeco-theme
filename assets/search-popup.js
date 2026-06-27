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
    this.viewAllContainer = this.querySelector('.search-popup__view-all');
    this.viewAllBtn = this.querySelector('.search-popup__view-all-btn');
    
    this.loadingSpinner = this.querySelector('.search-popup__loading');
    this.emptyState = this.querySelector('.search-popup__empty');
    this.initialState = this.querySelector('.search-popup__initial');
    
    this.storageKey = 'wrydeco_recently_searched';
    this.maxRecent = 8;
    this.debounceTimer = null;
    
    this.bindEvents();
    this.renderRecentSearches();
  }

  bindEvents() {
    this.closeButton?.addEventListener('click', () => {
      if (this.input.value.length > 0) {
        this.input.value = '';
        this.onInput();
        this.input.focus();
      } else {
        this.close();
      }
    });
    
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
    
    this.addEventListener('click', this.handleProductClick.bind(this));
  }
  
  isOpen() {
    return this.hasAttribute('open');
  }

  open() {
    this.setAttribute('open', '');
    document.body.style.overflow = 'hidden';
    this.renderRecentSearches();
    setTimeout(() => {
      this.input?.focus();
    }, 100);
  }

  close() {
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
    
    if (!products || products.length === 0) {
      this.showEmptyState();
      return;
    }
    
    this.predictiveList.innerHTML = products.map((product, index) => this.createProductCardHtml(product, index, query)).join('');
    this.predictiveList.style.display = 'grid';
    
    if (this.viewAllContainer && this.viewAllBtn) {
      this.viewAllBtn.href = `/search?q=${encodeURIComponent(query)}&type=product`;
      this.viewAllContainer.style.display = 'block';
    }
  }
  
  renderRecentSearches() {
    const recent = this.getRecentSearches();
    
    if (this.input.value.trim().length >= 2) {
      return; 
    }
    
    this.hideAllSections();
    
    if (recent.length === 0 && this.input.value.trim().length === 0) {
      if (this.initialState) this.initialState.style.display = 'flex';
      return;
    }
    
    if (recent.length > 0) {
      this.recentList.innerHTML = recent.map((product, index) => this.createProductCardHtml(product, index)).join('');
      this.recentContainer.style.display = 'block';
    } else {
      if (this.initialState) this.initialState.style.display = 'flex';
    }
  }
  
  showRecentSearches() {
    this.renderRecentSearches();
  }
  
  showLoading() {
    this.hideAllSections();
    this.loadingSpinner.style.display = 'flex';
  }
  
  showEmptyState() {
    this.hideAllSections();
    this.emptyState.style.display = 'block';
  }
  
  hideAllSections() {
    if (this.recentContainer) this.recentContainer.style.display = 'none';
    if (this.predictiveList) this.predictiveList.style.display = 'none';
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
      
    return `
      <a href="${product.url}" class="search-product-card" data-title="${product.title.replace(/"/g, '&quot;')}" data-url="${product.url}" data-image="${imageUrl}" style="animation-delay: ${index * 0.05}s">
        <div class="search-product-card__image">
          ${imageHtml}
        </div>
        <div class="search-product-card__info">
          <span class="search-product-card__title">${displayTitle}</span>
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
