const root = document.documentElement;
const opensAtHero = () => !location.hash || location.hash === '#' || location.hash === '#main';
history.scrollRestoration = opensAtHero() ? 'manual' : 'auto';
if (opensAtHero()) {
  // Reloading the home page starts the story instead of restoring a later video frame.
  window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
}
root.classList.add('js');
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
const shortScreen = window.matchMedia('(max-height: 650px), (max-width: 380px) and (max-height: 740px)');
const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#navigation');
menuButton.hidden = false;

function closeMenu() {
  navigation.classList.remove('is-open');
  menuButton.setAttribute('aria-expanded', 'false');
  menuButton.querySelector('span').textContent = '+';
}
menuButton.addEventListener('click', () => {
  const open = menuButton.getAttribute('aria-expanded') !== 'true';
  navigation.classList.toggle('is-open', open);
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.querySelector('span').textContent = open ? '−' : '+';
});
navigation.addEventListener('click', (event) => {
  if (event.target.closest('a')) closeMenu();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && menuButton.getAttribute('aria-expanded') === 'true') {
    closeMenu();
    menuButton.focus();
  }
});

const reveals = [...document.querySelectorAll('[data-reveal]')];
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('is-visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.08, rootMargin: '0px 0px -4% 0px' });
reveals.forEach((element) => revealObserver.observe(element));
// Focus and direct links should never land on content waiting for a reveal.
function revealTarget(element) {
  element?.closest('[data-reveal]')?.classList.add('is-visible');
  element?.querySelectorAll('[data-reveal]').forEach(item => item.classList.add('is-visible'));
}
function revealHash() {
  if (location.hash.length > 1) {
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    revealTarget(target);
  }
}
document.addEventListener('focusin', event => revealTarget(event.target));
window.addEventListener('hashchange', revealHash);
revealHash();

const hero = document.querySelector('.hero');
const heroStage = document.querySelector('.hero-stage');
const heroContent = document.querySelector('.hero-content');
const heroVideo = document.querySelector('#hero-video');
const heroCutout = document.querySelector('.hero-robot-cutout');
const cutoutContext = heroCutout.getContext('2d', { willReadFrequently: true });
let cutoutTime = -1;
function drawHeroCutout() {
  if (motionPreference.matches || !cutoutContext || heroVideo.readyState < 2 || cutoutTime === heroVideo.currentTime) return;
  try {
    cutoutContext.drawImage(heroVideo, 0, 0, heroCutout.width, heroCutout.height);
    const frame = cutoutContext.getImageData(0, 0, heroCutout.width, heroCutout.height);
    // The render uses pure black. Remove that backdrop so the robot can occlude text.
    for (let i = 0; i < frame.data.length; i += 4) {
      frame.data[i + 3] = Math.min(255, Math.max(frame.data[i], frame.data[i + 1], frame.data[i + 2]) * 32);
    }
    cutoutContext.putImageData(frame, 0, 0);
    cutoutTime = heroVideo.currentTime;
    heroCutout.parentElement.classList.add('cutout-ready');
  } catch {
    // Keep the original video visible if the browser cannot read its pixels.
    heroCutout.parentElement.classList.remove('cutout-ready');
  }
}
heroVideo.addEventListener('loadeddata', drawHeroCutout);
heroVideo.addEventListener('seeked', drawHeroCutout);
const robot = document.querySelector('.robot-section');
const robotStage = document.querySelector('.robot-stage');
const panels = [...document.querySelectorAll('[data-chapter]')];
const frames = [...document.querySelectorAll('[data-frame]')];
const steps = [...document.querySelectorAll('[data-step]')];
const wordStory = document.querySelector('.word-story');
// Keep a single readable heading for assistive technology while animating its letters.
wordStory.setAttribute('aria-label', wordStory.textContent.trim());
[...wordStory.querySelectorAll('.accent-word')].forEach(word => {
  const letters = [...word.textContent].map(character => {
    const letter = document.createElement('span');
    letter.className = 'story-letter';
    letter.textContent = character;
    return letter;
  });
  word.replaceChildren(...letters);
  word.setAttribute('aria-hidden', 'true');
});
const storyLetters = [...wordStory.querySelectorAll('.accent-word .story-letter')];
const gallery = document.querySelector('.team-gallery');
const navLinks = [...navigation.querySelectorAll('a')];
const sections = navLinks.map(link => document.querySelector(link.getAttribute('href')));
const clamp = (value, min = 0, max = 1) => Math.min(max, Math.max(min, value));
let frameRequest = 0;
let lastTime = 0;
let heroProgress = 0;
let robotProgress = 0;
let chapter = -1;
let animated = false;
let heroAnimated = false;
let geometry = {};
let videoProgress = 0;
// The first part brings the scene into view; the rest is reserved for playback.
const heroEntryScreens = 0.6;
// Frame 68 is the right-hand stop. Give the initial travel extra scroll distance.
const videoTravelEnd = 67 / 24;
const videoTravelWeight = 1.7;
// The robot holds at the right edge through frame 80, then starts its turn.
const videoSpinStart = 80 / 24;

function seekHeroVideo() {
  if (motionPreference.matches || !Number.isFinite(heroVideo.duration) || heroVideo.readyState < 2 || heroVideo.seeking) return;
  // Keep only the latest scroll position while the decoder completes a seek.
  const lastFrame = Math.max(0, heroVideo.duration - 1 / 24);
  const travelEnd = Math.min(videoTravelEnd, lastFrame);
  const weightedTime = videoProgress * (lastFrame + travelEnd * (videoTravelWeight - 1));
  const targetTime = weightedTime <= travelEnd * videoTravelWeight
    ? weightedTime / videoTravelWeight
    : travelEnd + weightedTime - travelEnd * videoTravelWeight;
  if (Math.abs(heroVideo.currentTime - targetTime) > 1 / 48) heroVideo.currentTime = targetTime;
}
heroVideo.addEventListener('loadedmetadata', requestRender);
heroVideo.addEventListener('loadeddata', seekHeroVideo);
heroVideo.addEventListener('seeked', seekHeroVideo);
heroVideo.addEventListener('seeked', requestRender);

function selectChapter(index) {
  if (index === chapter) return;
  chapter = index;
  panels.forEach((panel, i) => panel.classList.toggle('is-current', i === index));
  frames.forEach((frame, i) => {
    frame.classList.toggle('is-current', i === index);
    if (animated) frame.setAttribute('aria-hidden', String(i !== index));
    else frame.removeAttribute('aria-hidden');
  });
  steps.forEach((step, i) => step.setAttribute('aria-pressed', String(i === index)));
}

function measure() {
  const y = window.scrollY;
  geometry = {
    header: parseFloat(getComputedStyle(root).getPropertyValue('--header')),
    heroTop: hero.getBoundingClientRect().top + y,
    heroRange: Math.max(1, hero.offsetHeight - heroStage.offsetHeight),
    heroStageHeight: heroStage.offsetHeight,
    heroEntryRange: heroStage.offsetHeight * heroEntryScreens,
    robotTop: robot.getBoundingClientRect().top + y,
    robotRange: Math.max(1, robot.offsetHeight - robotStage.offsetHeight),
    wordTop: wordStory.getBoundingClientRect().top + y,
    galleryTop: gallery.getBoundingClientRect().top + y,
    galleryHeight: gallery.offsetHeight,
    sections: sections.map(section => section.getBoundingClientRect().top + y),
    pageRange: Math.max(1, document.documentElement.scrollHeight - window.innerHeight),
  };
}

function requestRender() {
  if (!frameRequest) frameRequest = requestAnimationFrame(render);
}
function render(time) {
  frameRequest = 0;
  const y = window.scrollY;
  const vh = window.innerHeight;
  const delta = lastTime ? Math.min(time - lastTime, 64) : 16;
  lastTime = time;
  const smoothing = 1 - Math.exp(-delta / 75);
  const targetHero = clamp((y + geometry.header - geometry.heroTop) / geometry.heroRange);
  const targetRobot = clamp((y + geometry.header - geometry.robotTop) / geometry.robotRange);
  heroProgress += (targetHero - heroProgress) * smoothing;
  robotProgress += (targetRobot - robotProgress) * smoothing;
  root.style.setProperty('--read-progress', String(clamp(y / geometry.pageRange)));

  if (!motionPreference.matches) {
    videoProgress = clamp((heroProgress * geometry.heroRange - geometry.heroEntryRange) / (geometry.heroRange - geometry.heroEntryRange));
    seekHeroVideo();
  }

  if (heroAnimated) {
    const entrance = clamp(heroProgress * geometry.heroRange / geometry.heroEntryRange);
    hero.style.setProperty('--title-y', `${-entrance * 100}px`);
    hero.style.setProperty('--title-scale', String(1 - entrance * 0.06));
    hero.style.setProperty('--title-opacity', String(clamp(1 - entrance * 1.6)));
    hero.style.setProperty('--photo-y', `${(1 - entrance) * geometry.heroStageHeight * 0.48}px`);
    hero.style.setProperty('--hint-opacity', String(clamp(1 - entrance * 2)));
    const nameReveal = clamp((heroVideo.currentTime - 0.15) / (videoTravelEnd - 0.15));
    const spinReveal = clamp((heroVideo.currentTime - videoSpinStart) / 0.75);
    const spinEase = spinReveal * spinReveal * (3 - 2 * spinReveal);
    hero.style.setProperty('--name-mask', `${(1 - nameReveal) * 100}%`);
    hero.style.setProperty('--name-opacity', String(clamp(nameReveal * 4)));
    hero.style.setProperty('--name-rise', `${-spinEase * 24}px`);
    hero.style.setProperty('--number-opacity', String(spinEase));
    heroContent.inert = entrance > 0.63;
  }
  if (animated) {
    const nextChapter = Math.min(2, Math.floor(robotProgress * 3));
    selectChapter(nextChapter);
    robot.style.setProperty('--robot-progress', String(robotProgress));
    const localProgress = clamp((robotProgress - nextChapter / 3) * 3);
    robot.style.setProperty('--robot-zoom', String(1 + localProgress * 0.035));
    const wordProgress = clamp((y + vh * 0.86 - geometry.wordTop) / (vh * 0.72));
    const leadingLetter = wordProgress > 0 && wordProgress < 1
      ? Math.ceil(wordProgress * storyLetters.length) - 1
      : -1;
    storyLetters.forEach((letter, index) => {
      letter.classList.toggle('is-lit', wordProgress > index / storyLetters.length);
      letter.classList.toggle('is-leading', index === leadingLetter);
    });
    const galleryProgress = clamp((y + vh - geometry.galleryTop) / (vh + geometry.galleryHeight));
    gallery.style.setProperty('--team-parallax', `${(galleryProgress - 0.5) * 24}px`);
  }
  let currentSection = -1;
  geometry.sections.forEach((top, i) => { if (y + vh * 0.4 >= top) currentSection = i; });
  navLinks.forEach((link, i) => {
    link.classList.toggle('is-active', i === currentSection);
    if (i === currentSection) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  });
  if ((heroAnimated && Math.abs(targetHero - heroProgress) > 0.0003) || (animated && Math.abs(targetRobot - robotProgress) > 0.0003)) requestRender();
}

function configureMotion() {
  heroAnimated = !motionPreference.matches;
  animated = !motionPreference.matches && !shortScreen.matches;
  heroVideo.controls = motionPreference.matches;
  if (!motionPreference.matches) {
    heroVideo.pause();
    if (heroVideo.preload !== 'auto') {
      heroVideo.preload = 'auto';
      heroVideo.load();
    }
  } else {
    // Leave a still frame and native playback controls when scroll motion is disabled.
    heroVideo.pause();
  }
  root.classList.toggle('motion-ready', !motionPreference.matches);
  root.classList.toggle('hero-motion', heroAnimated);
  heroContent.inert = false;
  if (!animated) frames.forEach(frame => frame.removeAttribute('aria-hidden'));
  if (!animated) storyLetters.forEach(letter => {
    letter.classList.add('is-lit');
    letter.classList.remove('is-leading');
  });
  // A preference change must expose every section immediately.
  if (motionPreference.matches) reveals.forEach(element => element.classList.add('is-visible'));
  chapter = -1;
  measure();
  heroProgress = clamp((scrollY + geometry.header - geometry.heroTop) / geometry.heroRange);
  robotProgress = clamp((scrollY + geometry.header - geometry.robotTop) / geometry.robotRange);
  lastTime = 0;
  requestRender();
}
steps.forEach((button, index) => {
  button.addEventListener('click', () => {
    if (!animated) return;
    // Jump to the middle of a chapter, leaving room on either side of the transition.
    const progress = (index + 0.45) / 3;
    window.scrollTo({ top: geometry.robotTop - geometry.header + geometry.robotRange * progress, behavior: 'smooth' });
  });
});
window.addEventListener('scroll', requestRender, { passive: true });
window.addEventListener('resize', configureMotion, { passive: true });
window.addEventListener('load', () => { measure(); requestRender(); });
window.addEventListener('pageshow', event => {
  if (event.persisted) return;
  if (opensAtHero()) {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
    videoProgress = 0;
    seekHeroVideo();
  } else {
    // Sticky scene heights are finalized now, so section links land in the right place.
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    target?.scrollIntoView({ block: 'start', behavior: 'instant' });
  }
  configureMotion();
});
motionPreference.addEventListener('change', configureMotion);
shortScreen.addEventListener('change', configureMotion);
document.fonts.ready.then(() => { measure(); requestRender(); });
configureMotion();
