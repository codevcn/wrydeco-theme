document.addEventListener('DOMContentLoaded', () => {
  const gallery = document.querySelector('[data-product-gallery]');
  if (!gallery) return;

  const slider = gallery.querySelector('[data-gallery-slider]');
  const dots = gallery.querySelectorAll('.product-gallery__dot');
  
  if (!slider || dots.length === 0) return;

  // Sync scroll to dots
  slider.addEventListener('scroll', () => {
    const scrollLeft = slider.scrollLeft;
    const itemWidth = slider.clientWidth;
    const activeIndex = Math.round(scrollLeft / itemWidth);
    
    updateActiveDot(activeIndex);
  });

  // Click on dots to scroll
  dots.forEach(dot => {
    dot.addEventListener('click', (e) => {
      const index = parseInt(e.target.dataset.index);
      scrollToIndex(index);
    });
  });

  function updateActiveDot(index) {
    dots.forEach((dot, i) => {
      if (i === index) {
        dot.classList.add('is-active');
      } else {
        dot.classList.remove('is-active');
      }
    });
  }

  function scrollToIndex(index) {
    const itemWidth = slider.clientWidth;
    slider.scrollTo({
      left: index * itemWidth,
      behavior: 'smooth'
    });
  }

  // Listen to variant changes to scroll to featured media
  document.addEventListener('product:variant-change', () => {
    // We check if the new HTML rendered a different featured media.
    // In our product-info.js, we didn't replace the gallery DOM entirely, 
    // but the section API fetches new HTML. If we want to sync the gallery, 
    // it's better to find the featured media ID from the new variant.
    // For simplicity, if we get the variant ID, we'd need its featured media ID.
    // Since we don't fetch the whole product JSON deeply here, 
    // let's rely on the user clicking a swatch, we can just fetch the variant data again, 
    // or we could have replaced the whole gallery DOM in product-info.js.
  });
});
