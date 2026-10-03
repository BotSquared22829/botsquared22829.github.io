// The opening is timed; scrolling advances the text inside a pinned stage.
// All copy is local and editable in about.html.
const introMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
if (!introMotion.matches) {
  const scrollKeys = ['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End', ' '];
  const preventIntroScroll = event => {
    if (event.type === 'keydown' && !scrollKeys.includes(event.key)) return;
    if (event.type === 'wheel' && event.ctrlKey) return;
    event.preventDefault();
  };
  document.documentElement.classList.add('intro-scroll-locked');
  window.addEventListener('wheel', preventIntroScroll, { passive: false });
  window.addEventListener('touchmove', preventIntroScroll, { passive: false });
  window.addEventListener('keydown', preventIntroScroll);

  function unlockIntroScroll() {
    document.documentElement.classList.remove('intro-scroll-locked');
    window.removeEventListener('wheel', preventIntroScroll);
    window.removeEventListener('touchmove', preventIntroScroll);
    window.removeEventListener('keydown', preventIntroScroll);
    introMotion.removeEventListener('change', onIntroMotionChange);
    window.removeEventListener('pagehide', unlockIntroScroll);
  }
  function onIntroMotionChange(event) {
    if (event.matches) unlockIntroScroll();
  }
  introMotion.addEventListener('change', onIntroMotionChange);
  window.addEventListener('pagehide', unlockIntroScroll);
  // The last intro word finishes at 8.45s + .65s delay + .2s fade.
  // Schedule cleanup before setting up the animation so failures cannot trap scrolling.
  window.setTimeout(unlockIntroScroll, 9300);

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

// Keep each photo and its description together as the awards stage pins.
// Short viewports and reduced motion use the same chapters in normal flow.
const awards = document.querySelector('.about-awards');
const awardsStage = awards.querySelector('.awards-stage');
const awardChapters = [...awards.querySelectorAll('.award-chapter')];
const awardsMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let awardsPinned = false;
let awardsFramePending = false;

function updateAwards() {
  const headerHeight = document.querySelector('.site-header').getBoundingClientRect().height;
  const travel = Math.max(1, awards.offsetHeight - awardsStage.offsetHeight);
  const progress = Math.max(0, Math.min(1, (headerHeight - awards.getBoundingClientRect().top) / travel));
  const active = Math.min(awardChapters.length - 1, Math.floor(progress * awardChapters.length));
  awardChapters.forEach((chapter, index) => {
    chapter.classList.toggle('is-active', awardsPinned && index === active);
    if (awardsPinned && index !== active) chapter.setAttribute('aria-hidden', 'true');
    else chapter.removeAttribute('aria-hidden');
  });
}

function layoutAwards() {
  const styles = getComputedStyle(awardsStage);
  const neededHeight = awards.querySelector('h2').offsetHeight
    + Math.max(...awardChapters.map(chapter => chapter.offsetHeight))
    + parseFloat(styles.rowGap) + parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom);
  const availableHeight = window.innerHeight - document.querySelector('.site-header').offsetHeight;
  awardsPinned = !awardsMotion.matches && neededHeight <= availableHeight;
  awards.classList.toggle('awards-scroll-ready', awardsPinned);
  updateAwards();
}

window.addEventListener('scroll', () => {
  if (awardsFramePending || !awardsPinned) return;
  awardsFramePending = true;
  requestAnimationFrame(() => {
    awardsFramePending = false;
    updateAwards();
  });
}, { passive: true });
window.addEventListener('resize', layoutAwards, { passive: true });
awardsMotion.addEventListener('change', layoutAwards);
document.fonts.ready.then(layoutAwards);
layoutAwards();
