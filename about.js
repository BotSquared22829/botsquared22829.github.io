// The opening is timed; scrolling advances the text inside a pinned stage.
// All copy is local and editable in about.html.
if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const groups = [];
  document.querySelectorAll('[data-stream]').forEach(element => {
    const tokens = [];
    const text = element.textContent.trim();
    const readable = document.createElement('span');
    readable.className = 'stream-readable';
    readable.textContent = text;
    const visual = document.createElement('span');
    visual.setAttribute('aria-hidden', 'true');
    const words = text.split(/\s+/);
    words.forEach((word, index) => {
      const token = document.createElement('span');
      token.className = 'stream-word';
      token.textContent = word;
      tokens.push(token);
      visual.append(token);
      if (index < words.length - 1) visual.append(document.createTextNode(' '));
    });
    element.replaceChildren(readable, visual);
    groups.push({ element, tokens, isParagraph: element.matches('p') });
  });
  document.querySelector('.streamed-copy').classList.add('scroll-reveal-ready');
  document.body.classList.add('story-scroll-ready');

  function layOutReveal() {
    groups.forEach(group => {
      const { tokens, isParagraph } = group;
      const positions = tokens.map(token => token.getBoundingClientRect());
      const left = Math.min(...positions.map(position => position.left));
      const top = Math.min(...positions.map(position => position.top));
      const width = Math.max(1, Math.max(...positions.map(position => position.left)) - left);
      const height = Math.max(1, Math.max(...positions.map(position => position.top)) - top);
      tokens.forEach((token, index) => {
        const x = (positions[index].left - left) / width;
        const y = (positions[index].top - top) / height;
        // The opening diagonal wave adapts to the actual text wrapping.
        token.style.setProperty('--stream-delay', `${(isParagraph ? 8.45 : 7.7) + (x * 0.35 + y * 0.65) * 0.65}s`);
      });
    });
  }

  const paragraphs = groups.filter(group => group.isParagraph);
  paragraphs[0].element.classList.add('is-revealed');
  paragraphs.slice(1).forEach(({ element }) => element.classList.add('paragraph-fade'));
  let previousScroll = window.scrollY;
  let scrollIntent = false;
  let hasScrolled = false;
  let introComplete = false;
  let framePending = false;

  function updateScrollStory() {
    if (!hasScrolled || !introComplete) return;
    const stage = document.querySelector('.thinking-stage');
    const headerHeight = document.querySelector('.site-header').getBoundingClientRect().height;
    const distance = Math.max(0, headerHeight - stage.getBoundingClientRect().top);
    const progress = Math.min(paragraphs.length - 0.001, distance / (window.innerHeight * 0.9));
    const active = Math.floor(progress);
    const fadeProgress = Math.min(1, (progress - active) / 0.62);
    paragraphs.forEach(({ element }, index) => {
      element.classList.toggle('is-revealed', index === active);
      if (index > 0) {
        element.style.setProperty('--paragraph-progress', index === active ? fadeProgress : 0);
      }
    });
  }

  // Browser-restored scroll positions should not start the story on load.
  window.addEventListener('wheel', () => { scrollIntent = true; }, { passive: true });
  window.addEventListener('touchmove', () => { scrollIntent = true; }, { passive: true });
  window.addEventListener('pointerdown', () => { scrollIntent = true; }, { passive: true });
  window.addEventListener('keydown', event => {
    if (['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End', ' '].includes(event.key)) scrollIntent = true;
  });
  window.addEventListener('scroll', () => {
    if (scrollIntent && Math.abs(window.scrollY - previousScroll) > 2) hasScrolled = true;
    previousScroll = window.scrollY;
    if (framePending) return;
    framePending = true;
    requestAnimationFrame(() => {
      framePending = false;
      updateScrollStory();
    });
  }, { passive: true });

  window.setTimeout(() => {
    introComplete = true;
    updateScrollStory();
  }, 7700);
  layOutReveal();
  document.fonts.ready.then(layOutReveal);
  window.addEventListener('resize', () => {
    layOutReveal();
    updateScrollStory();
  }, { passive: true });
}
