(function () {
  function initShowroomReveal() {
    var showroomPages = document.querySelectorAll('.showroom-page');

    showroomPages.forEach(function (showroomPage) {
      if (showroomPage.dataset.revealInit === 'true') {
        return;
      }

      var rooms = Array.prototype.slice.call(showroomPage.querySelectorAll('.showroom-room'));

      if (!rooms.length) {
        return;
      }

      showroomPage.dataset.revealInit = 'true';

      if (!('IntersectionObserver' in window)) {
        rooms.forEach(function (room) {
          room.classList.add('showroom-room--is-visible');
        });
        return;
      }

      rooms[0].classList.add('showroom-room--is-visible');
      showroomPage.classList.add('showroom-page--reveal-ready');

      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (!entry.isIntersecting) {
              return;
            }

            entry.target.classList.add('showroom-room--is-visible');
            observer.unobserve(entry.target);
          });
        },
        {
          rootMargin: '0px 0px -18% 0px',
          threshold: 0.32,
        }
      );

      rooms.slice(1).forEach(function (room) {
        observer.observe(room);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initShowroomReveal);
    return;
  }

  initShowroomReveal();
})();
