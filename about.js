// The opening is timed; scrolling advances the text inside a pinned stage.
// All copy is local and editable in about.html.
const introMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const introShortScreen = window.matchMedia('(max-height: 500px)');
// Skip the opening pause while the thinking animation is commented out.
const introDelay = document.querySelector('.thinking-sequence') ? 5.7 : 0;
const robotStory = document.querySelector('.robot-story');
const robotSteps = [...document.querySelectorAll('[data-robot-step]')];
const robotPhases = ['sketch', 'build', 'compete'];
const robotVideo = document.querySelector('.robot-story-video');
// Frames 1–72 hold the outer plates clear, seat wheels/deck/launcher,
// then close the side assemblies around the wheels, with a
// completed-robot pause. Frames 73–120 turn it as the full-scale BIOBUZZ
// field fades into the close camera view.
const robotAssemblyEnd = 71 / 24;
const robotLastFrame = 119 / 24;
// Materialize the same exploded pose before any parts begin to assemble.
const robotRevealStart = 0.76;
const robotBuildStart = 1.16;
let robotRequestedTime = introMotion.matches || introShortScreen.matches ? robotLastFrame : 0;

function seekRobotFrame() {
  if (robotVideo.readyState < 2 || robotVideo.seeking || !Number.isFinite(robotVideo.duration)) return;
  const time = Math.min(robotRequestedTime, Math.max(0, robotVideo.duration - 1 / 24));
  if (Math.abs(robotVideo.currentTime - time) > 1 / 48) robotVideo.currentTime = time;
}

robotVideo.addEventListener('loadeddata', () => {
  robotStory.classList.add('has-cad-video');
  seekRobotFrame();
});
robotVideo.addEventListener('seeked', seekRobotFrame);
robotVideo.addEventListener('error', () => {
  robotStory.classList.remove('has-cad-video');
});

function setRobotProgress(progress, animated = true) {
  const index = Math.min(robotPhases.length - 1, Math.floor(progress));
  robotStory.dataset.phase = robotPhases[index];
  const reveal = Math.max(0, Math.min(1, (progress - robotRevealStart) / (robotBuildStart - robotRevealStart)));
  const blend = animated ? reveal * reveal * (3 - 2 * reveal) : 1;
  robotStory.style.setProperty('--robot-sketch-opacity', 1 - blend);
  robotStory.style.setProperty('--robot-color-visible', blend > 0 ? 1 : 0);
  // A matching still covers the decoder during the dissolve, including when
  // reversing quickly from a later video frame back into the sketch.
  robotStory.classList.toggle('is-build-intro', animated && progress <= robotBuildStart);
  // Match each video segment to the scroll distance within its story paragraph.
  // Retain only this latest target while the decoder finishes an earlier seek.
  const build = Math.max(0, Math.min(1, (progress - robotBuildStart) / (2 - robotBuildStart)));
  const compete = Math.max(0, Math.min(1, progress - 2));
  robotRequestedTime = animated
    ? build * robotAssemblyEnd + compete * (robotLastFrame - robotAssemblyEnd)
    : robotLastFrame;
  seekRobotFrame();
  robotSteps.forEach((step, stepIndex) => {
    step.classList.toggle('is-complete', animated && stepIndex < index);
    if (animated && stepIndex === index) step.setAttribute('aria-current', 'step');
    else step.removeAttribute('aria-current');
  });
}

if (!introMotion.matches && !introShortScreen.matches) {
  setRobotProgress(0);
  const scrollKeys = ['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Home', 'End', ' '];
  const preventIntroScroll = event => {
    if (event.type === 'keydown' && !scrollKeys.includes(event.key)) return;
    if (event.type === 'wheel' && event.ctrlKey) return;
    event.preventDefault();
  };
  // A direct section link should be usable while the offscreen intro finishes.
  if (!location.hash || location.hash === '#' || location.hash === '#main') {
    document.documentElement.classList.add('intro-scroll-locked');
    window.addEventListener('wheel', preventIntroScroll, { passive: false });
    window.addEventListener('touchmove', preventIntroScroll, { passive: false });
    window.addEventListener('keydown', preventIntroScroll);
  }

  function unlockIntroScroll() {
    document.documentElement.classList.remove('intro-scroll-locked');
    window.removeEventListener('wheel', preventIntroScroll);
    window.removeEventListener('touchmove', preventIntroScroll);
    window.removeEventListener('keydown', preventIntroScroll);
    document.removeEventListener('focusin', onIntroFocus);
    window.removeEventListener('pagehide', unlockIntroScroll);
  }
  function onIntroFocus(event) {
    if (event.target.id === 'main') unlockIntroScroll();
  }
  function onIntroMotionChange(event) {
    if (!event.matches) {
      if (!introMotion.matches && !introShortScreen.matches) {
        if (!hasScrolled) setRobotProgress(0);
        updateScrollStory();
      }
      return;
    }
    unlockIntroScroll();
    introComplete = true;
    setRobotProgress(2, false);
    // Returning to full motion must not restart the introductory text delays.
    groups.forEach(({ tokens }) => tokens.forEach(token => {
      token.style.animation = 'none';
      token.style.opacity = '1';
      token.style.filter = 'none';
      token.style.transform = 'none';
    }));
  }
  introMotion.addEventListener('change', onIntroMotionChange);
  introShortScreen.addEventListener('change', onIntroMotionChange);
  document.addEventListener('focusin', onIntroFocus);
  window.addEventListener('pagehide', unlockIntroScroll);
  // The last intro word finishes 1.6s after the opening pause.
  // Schedule cleanup before setting up the animation so failures cannot trap scrolling.
  window.setTimeout(unlockIntroScroll, (introDelay + 1.6) * 1000);

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
        token.style.setProperty('--stream-delay', `${introDelay + (isParagraph ? 0.75 : 0) + (x * 0.35 + y * 0.65) * 0.65}s`);
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
    if (introMotion.matches || introShortScreen.matches || !hasScrolled || !introComplete) return;
    document.body.classList.add('story-has-scrolled');
    const stage = document.querySelector('.thinking-stage');
    const headerHeight = document.querySelector('.site-header').getBoundingClientRect().height;
    const distance = Math.max(0, headerHeight - stage.getBoundingClientRect().top);
    const progress = Math.min(paragraphs.length - 0.001, distance / (window.innerHeight * 0.9));
    const active = Math.floor(progress);
    setRobotProgress(progress);
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
  }, introDelay * 1000);
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
