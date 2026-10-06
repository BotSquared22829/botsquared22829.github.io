const title = document.querySelector('[data-decode-title]');
const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
const content = document.querySelector('.decode-content');
const hero = content?.querySelector('.decode-hero');
const intro = content?.querySelector('.decode-intro');
const story = content?.querySelector('.decode-story');
const cad = content?.querySelector('.decode-story--cad');
const timeline = content?.querySelector('.decode-story--timeline');
const indicator = content?.querySelector('.decode-scroll-indicator');
const subtitle = content?.querySelector('.decode-subtitle');
const navigationType = performance.getEntriesByType('navigation')[0]?.type;
const lateInitialization = !document.documentElement.classList.contains('detail-pending');
const preserveLinearView = lateInitialization && window.scrollY > 0;
const initialTarget = navigationType !== 'reload' && location.hash
  ? [...document.querySelectorAll('[id]')].find(element => `#${encodeURIComponent(element.id)}` === location.hash && content?.contains(element))
  : null;
const savedPosition = navigationType === 'back_forward' ? history.state?.decodeScrollY : undefined;
let restorePosition = Number.isFinite(savedPosition) ? savedPosition : lateInitialization && !initialTarget ? window.scrollY : undefined;
let openingFinished = !title || motion.matches || Boolean(initialTarget) || Number.isFinite(restorePosition);
let unlockTimer;

history.scrollRestoration = 'manual';

function resetToTop() {
  if (location.hash) history.replaceState(history.state, '', location.pathname + location.search);
  window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
}

function preventOpeningScroll(event) {
  if (event.type === 'keydown' && !['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End', ' '].includes(event.key)) return;
  if (event.type === 'wheel' && event.ctrlKey) return;
  event.preventDefault();
}

function unlockOpening() {
  openingFinished = true;
  clearTimeout(unlockTimer);
  document.documentElement.classList.remove('decode-scroll-locked');
  window.removeEventListener('wheel', preventOpeningScroll);
  window.removeEventListener('touchmove', preventOpeningScroll);
  window.removeEventListener('keydown', preventOpeningScroll);
  subtitle?.removeEventListener('transitionend', onSubtitleFinished);
  indicator?.removeAttribute('tabindex');
  content?.dispatchEvent(new Event('decode:ready'));
  content?.classList.remove('is-initializing');
}

function onSubtitleFinished(event) {
  if (event.target === subtitle && event.propertyName === 'opacity') unlockOpening();
}

if (!initialTarget && !Number.isFinite(restorePosition)) resetToTop();
if (!openingFinished) {
  document.documentElement.classList.add('decode-scroll-locked');
  indicator?.setAttribute('tabindex', '-1');
  window.addEventListener('wheel', preventOpeningScroll, { passive: false });
  window.addEventListener('touchmove', preventOpeningScroll, { passive: false });
  window.addEventListener('keydown', preventOpeningScroll);
  subtitle?.addEventListener('transitionend', onSubtitleFinished);
  // Fail open if a hidden tab or interrupted transition skips transitionend.
  unlockTimer = window.setTimeout(unlockOpening, 4000);
}
window.addEventListener('pagehide', () => {
  restorePosition = window.scrollY;
  history.replaceState({ ...history.state, decodeScrollY: restorePosition }, '');
  unlockOpening();
});
motion.addEventListener('change', event => {
  if (event.matches) unlockOpening();
});
content?.addEventListener('focusin', event => {
  // Activating Skip to content should also skip the temporary opening gate.
  if (!openingFinished && event.target === content) unlockOpening();
});

if (title && !openingFinished) {
  const content = title.closest('.decode-content');
  content.classList.add('is-scrambling');
  const letters = [...title.querySelectorAll('.decode-letter')];
  const word = letters.map(letter => letter.textContent).join('');
  const glyphs = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%&*+=?<>/\\{}[]_-';
  const spawnStep = 180;
  const delay = (letters.length - 1) * spawnStep + 320;
  const step = 260;
  const start = performance.now();
  let frame;
  let lastTick = -1;

  function finish() {
    cancelAnimationFrame(frame);
    letters.forEach((letter, index) => {
      letter.hidden = false;
      letter.textContent = word[index];
    });
    content.classList.remove('is-scrambling');
    if (motion.matches) unlockOpening();
    else {
      clearTimeout(unlockTimer);
      unlockTimer = window.setTimeout(unlockOpening, 800);
    }
    motion.removeEventListener('change', onMotionChange);
  }

  function onMotionChange() {
    if (motion.matches) finish();
  }

  function animate(now) {
    const elapsed = now - start;
    const spawned = Math.min(letters.length, 1 + Math.floor(elapsed / spawnStep));
    const resolved = Math.max(0, Math.floor((elapsed - delay) / step));
    if (resolved >= letters.length) {
      finish();
      return;
    }
    letters.forEach((letter, index) => { letter.hidden = index >= spawned; });
    const tick = Math.floor(elapsed / 65);
    if (tick !== lastTick) {
      letters.forEach((letter, index) => {
        let glyphIndex = Math.floor(Math.random() * glyphs.length);
        if (glyphs[glyphIndex] === word[index]) glyphIndex = (glyphIndex + 1) % glyphs.length;
        letter.textContent = index < resolved ? word[index] : glyphs[glyphIndex];
      });
      lastTick = tick;
    }
    frame = requestAnimationFrame(animate);
  }

  motion.addEventListener('change', onMotionChange);
  animate(start);
}

if (hero && intro && story && cad && timeline && indicator) {
  const timelineList = timeline.querySelector('.decode-timeline');
  const timelineItems = [...timelineList.querySelectorAll('.decode-timeline-item')];
  const eventPanels = [...timeline.querySelectorAll('.decode-event-panel')];
  let scrollFrame = 0;
  let focusStory = false;
  let storyVisible = false;
  let cadVisible = false;
  let timelineVisible = false;
  let markerPositions = [];
  let timelineLength = 1;
  let metricsDirty = true;
  let currentPanel = -1;
  let scrollEnabled = false;
  let timelinePinned = false;

  function geometry() {
    const header = document.querySelector('.site-header').getBoundingClientRect().height;
    return {
      start: content.getBoundingClientRect().top + window.scrollY - header,
      distance: Math.max(1, hero.offsetHeight),
    };
  }

  function updateFade() {
    scrollFrame = 0;
    if (!openingFinished) {
      resetToTop();
      return;
    }
    if (!scrollEnabled) return;
    const { start, distance } = geometry();
    // Read marker layout before changing chapter styles, and only when the
    // viewport changes. Timeline rows do not move during the scroll animation.
    if (metricsDirty) {
      markerPositions = timelineItems.map(item => item.offsetTop);
      timelineLength = Math.max(1, markerPositions.at(-1) - markerPositions[0]);
      metricsDirty = false;
    }
    const progress = (window.scrollY - start) / distance;
    const wasStoryVisible = storyVisible;
    // Crossing a threshold starts a complete timed transition. A separate
    // return threshold avoids flickering when scrolling near the trigger.
    if (progress >= .18) storyVisible = true;
    else if (progress <= .08) storyVisible = false;
    if (progress >= 1.18) cadVisible = true;
    else if (progress <= 1.08) cadVisible = false;
    if (!timelinePinned) timelineVisible = false;
    else if (progress >= 2.18) timelineVisible = true;
    else if (progress <= 2.08) timelineVisible = false;
    content.classList.toggle('is-story-visible', storyVisible);
    content.classList.toggle('is-cad-visible', cadVisible);
    content.classList.toggle('is-timeline-visible', timelineVisible);
    // Hold on Kickoff for another .35 viewport of scrolling after the reveal.
    const timelineProgress = Math.min(1, Math.max(0, (progress - 2.53) / 2.2));
    const reached = markerPositions.map(position => timelineProgress + .0001 >= (position - markerPositions[0]) / timelineLength);
    let currentEvent = 0;
    reached.forEach((isReached, index) => { if (isReached) currentEvent = index; });
    if (timelinePinned) {
      timelineList.style.setProperty('--timeline-progress', timelineProgress);
      timelineList.style.setProperty('--timeline-length', `${timelineLength}px`);
    }
    timelineItems.forEach((item, index) => {
      item.classList.toggle('is-reached', timelineVisible && reached[index]);
      item.classList.toggle('is-current', timelineVisible && index === currentEvent);
      if (timelineVisible && index === currentEvent) item.setAttribute('aria-current', 'step');
      else item.removeAttribute('aria-current');
    });
    const visiblePanel = timelineVisible ? currentEvent : -1;
    if (timelinePinned && currentPanel !== visiblePanel) {
      eventPanels.forEach((panel, index) => {
        const hidden = index !== visiblePanel;
        if (hidden && panel.contains(document.activeElement)) content.focus({ preventScroll: true });
        panel.classList.toggle('is-current', index === currentEvent);
        panel.setAttribute('aria-hidden', String(hidden));
        panel.inert = hidden;
      });
      currentPanel = visiblePanel;
    }
    intro.setAttribute('aria-hidden', String(storyVisible));
    intro.inert = storyVisible;
    if (((!storyVisible || cadVisible) && story.contains(document.activeElement)) || ((!cadVisible || timelineVisible) && cad.contains(document.activeElement)) || (timelinePinned && !timelineVisible && timeline.contains(document.activeElement))) content.focus({ preventScroll: true });
    story.setAttribute('aria-hidden', String(!storyVisible || cadVisible));
    cad.setAttribute('aria-hidden', String(!cadVisible || timelineVisible));
    if (timelinePinned) timeline.setAttribute('aria-hidden', String(!timelineVisible));
    story.inert = !storyVisible || cadVisible;
    cad.inert = !cadVisible || timelineVisible;
    timeline.inert = timelinePinned && !timelineVisible;
    indicator.tabIndex = storyVisible || !openingFinished ? -1 : 0;
    // Keep keyboard focus pending while the smooth scroll approaches the
    // reveal threshold; cancel only if the reader moves past or back out of it.
    if ((wasStoryVisible && !storyVisible) || cadVisible) focusStory = false;
  }

  function queueFade() {
    if (!scrollFrame) scrollFrame = requestAnimationFrame(updateFade);
  }

  function configureScroll() {
    // A tall timeline must not disable the earlier chapters. Measure each
    // layout independently, keeping oversized content in normal document flow.
    const canAnimate = !motion.matches && !preserveLinearView;
    hero.insertBefore(timeline, indicator);
    content.classList.remove('has-linear-timeline');
    content.classList.toggle('has-decode-scroll', canAnimate);
    let contentFits = false;
    timelinePinned = false;
    if (canAnimate) {
      const styles = getComputedStyle(hero);
      const availableHeight = hero.clientHeight - parseFloat(styles.paddingTop) - parseFloat(styles.paddingBottom);
      const introHeight = intro.getBoundingClientRect().height + indicator.offsetHeight + 12;
      contentFits = Math.max(introHeight, story.getBoundingClientRect().height, cad.getBoundingClientRect().height) <= availableHeight + 1;
      timelinePinned = contentFits && timeline.getBoundingClientRect().height <= availableHeight + 1;
      if (contentFits && !timelinePinned) {
        hero.parentElement.after(timeline);
        content.classList.add('has-linear-timeline');
      }
    }
    scrollEnabled = canAnimate && contentFits;
    content.classList.toggle('has-decode-scroll', scrollEnabled);
    metricsDirty = true;
    currentPanel = -2;
    if (!timelinePinned) {
      timeline.removeAttribute('aria-hidden');
      timeline.inert = false;
      timelineList.style.removeProperty('--timeline-progress');
      timelineList.style.removeProperty('--timeline-length');
      eventPanels.forEach(panel => {
        panel.removeAttribute('aria-hidden');
        panel.inert = false;
      });
    }
    if (!scrollEnabled) {
      if (!openingFinished) unlockOpening();
      intro.removeAttribute('aria-hidden');
      story.removeAttribute('aria-hidden');
      cad.removeAttribute('aria-hidden');
      timeline.removeAttribute('aria-hidden');
      timelineList.style.removeProperty('--timeline-progress');
      timelineList.style.removeProperty('--timeline-length');
      [intro, story, cad, timeline].forEach(section => { section.inert = false; });
      eventPanels.forEach(panel => {
        panel.removeAttribute('aria-hidden');
        panel.inert = false;
      });
      timelineItems.forEach(item => {
        item.removeAttribute('aria-current');
        item.classList.remove('is-current', 'is-reached');
      });
      indicator.removeAttribute('tabindex');
      content.classList.remove('is-story-visible', 'is-cad-visible', 'is-timeline-visible');
      storyVisible = false;
      cadVisible = false;
      timelineVisible = false;
      focusStory = false;
    } else if (!openingFinished) {
      intro.setAttribute('aria-hidden', 'false');
      story.setAttribute('aria-hidden', 'true');
      cad.setAttribute('aria-hidden', 'true');
      if (timelinePinned) timeline.setAttribute('aria-hidden', 'true');
      [story, cad].forEach(section => { section.inert = true; });
      timeline.inert = timelinePinned;
      if (timelinePinned) eventPanels.forEach(panel => {
        panel.setAttribute('aria-hidden', 'true');
        panel.inert = true;
      });
      indicator.tabIndex = -1;
    } else updateFade();
  }

  function revealStory(behavior) {
    const { start, distance } = geometry();
    window.scrollTo({ top: start + distance * .24, behavior });
  }

  indicator.addEventListener('click', event => {
    if (!openingFinished) {
      event.preventDefault();
      return;
    }
    if (!scrollEnabled) return;
    event.preventDefault();
    history.replaceState(history.state, '', '#decode-story');
    focusStory = true;
    revealStory('smooth');
  });
  story.addEventListener('transitionend', event => {
    if (event.target === story && event.propertyName === 'opacity' && storyVisible && !cadVisible && focusStory) {
      focusStory = false;
      story.focus({ preventScroll: true });
    }
  });
  window.addEventListener('scroll', queueFade, { passive: true });
  window.addEventListener('resize', () => {
    metricsDirty = true;
    configureScroll();
  });
  window.addEventListener('pageshow', event => {
    const position = event.persisted || Number.isFinite(restorePosition) ? restorePosition : undefined;
    const restoreView = () => {
      if (Number.isFinite(position)) window.scrollTo({ top: position, behavior: 'instant' });
      else if (initialTarget) {
        const chapterProgress = new Map([[story, .24], [cad, 1.24], [timeline, 2.24]]).get(initialTarget.closest('.decode-story'));
        if (scrollEnabled && chapterProgress !== undefined && (timelinePinned || !timeline.contains(initialTarget))) {
          const { start, distance } = geometry();
          window.scrollTo({ top: start + distance * chapterProgress, behavior: 'instant' });
        } else initialTarget.scrollIntoView({ behavior: 'instant', block: 'start' });
      } else resetToTop();
      updateFade();
    };
    restoreView();
    if (initialTarget || Number.isFinite(position)) requestAnimationFrame(restoreView);
  });
  content.addEventListener('decode:ready', queueFade);
  motion.addEventListener('change', configureScroll);
  configureScroll();
}

// Commit the hidden chapter state without transitions before exposing the intro.
// This prevents a visible paragraph from fading out during the first paint.
if (content) {
  if (story) getComputedStyle(story).opacity;
  content.classList.remove('is-initializing');
}

const resultsSection = document.querySelector('.decode-performance');
if (resultsSection) {
  const eventButtons = [...resultsSection.querySelectorAll('[data-result-event]')];
  const resultPanels = [...resultsSection.querySelectorAll('[data-result]')];
  const chartPoints = [...resultsSection.querySelectorAll('[data-score-point]')];

  function selectResult(eventKey) {
    eventButtons.forEach(button => {
      button.setAttribute('aria-pressed', String(button.dataset.resultEvent === eventKey));
    });
    resultPanels.forEach(panel => {
      const selected = panel.dataset.result === eventKey;
      panel.hidden = !selected;
      panel.classList.toggle('is-current', selected);
    });
    chartPoints.forEach(point => {
      point.classList.toggle('is-selected', point.dataset.scorePoint === eventKey);
    });
  }

  eventButtons.forEach(button => {
    button.addEventListener('click', () => selectResult(button.dataset.resultEvent));
  });
  selectResult('province');
  const eventPicker = resultsSection.querySelector('.decode-event-picker');
  if (eventPicker) eventPicker.hidden = false;

  if (!motion.matches && 'IntersectionObserver' in window) {
    resultsSection.classList.add('will-reveal');
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        resultsSection.classList.add('is-in-view');
        observer.disconnect();
      }
    }, { threshold: .3 });
    observer.observe(resultsSection.querySelector('.decode-score-chart'));
    motion.addEventListener('change', event => {
      if (event.matches) {
        resultsSection.classList.add('is-in-view');
        observer.disconnect();
      }
    });
  }
}
