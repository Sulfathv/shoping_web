document.querySelectorAll('[data-gallery]').forEach((gallery) => {
  const slides = Array.from(gallery.querySelectorAll('.detail-slide'));
  const counter = gallery.parentElement.querySelector('[data-gallery-index]');
  const update = () => {
    const index = Math.round(gallery.scrollLeft / gallery.clientWidth);
    if (counter) counter.textContent = String(index + 1);
  };
  gallery.addEventListener('scroll', () => window.requestAnimationFrame(update), { passive: true });
  gallery.parentElement.querySelector('.gallery-prev')?.addEventListener('click', () => {
    const index = Math.round(gallery.scrollLeft / gallery.clientWidth);
    gallery.scrollTo({ left: Math.max(0, index - 1) * gallery.clientWidth, behavior: 'smooth' });
  });
  gallery.parentElement.querySelector('.gallery-next')?.addEventListener('click', () => {
    const index = Math.round(gallery.scrollLeft / gallery.clientWidth);
    gallery.scrollTo({ left: Math.min(slides.length - 1, index + 1) * gallery.clientWidth, behavior: 'smooth' });
  });
});
