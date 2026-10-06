const content = document.querySelector('.cdc-content');
const hero = content.querySelector('.cdc-hero');
const firetruck = content.querySelector('.cdc-firetruck');
const indicator = content.querySelector('.cdc-scroll-indicator');
const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
const navigationType = performance.getEntriesByType('navigation')[0]?.type;
const lateInitialization = !document.documentElement.classList.contains('detail-pending');
const preserveLinearView = lateInitialization && window.scrollY > 0;
const initialTarget = navigationType !== 'reload' && location.hash
  ? [...content.querySelectorAll('[id]')].find(element => `#${encodeURIComponent(element.id)}` === location.hash)
  : null;
const savedPosition = navigationType === 'back_forward' ? history.state?.cdcScrollY : undefined;
let restorePosition = Number.isFinite(savedPosition) ? savedPosition : lateInitialization && !initialTarget ? window.scrollY : undefined;
let revealed = false;
let scrollFrame = 0;
let focusTitle = false;
let scrollEnabled = false;

history.scrollRestoration = 'manual';

function resetToTop() {
  if (location.hash) history.replaceState(history.state, '', location.pathname + location.search);
  window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
}

function geometry() {
  const header = document.querySelector('.site-header').getBoundingClientRect().height;
  return {
    start: content.getBoundingClientRect().top + window.scrollY - header,
    threshold: Math.min(180, Math.max(90, hero.offsetHeight * .16)),
  };
}

function updateTitle() {
  scrollFrame = 0;
  if (!scrollEnabled) return;
  const { start, threshold } = geometry();
  const distance = window.scrollY - start;
  const wasRevealed = revealed;
  if (distance >= threshold) revealed = true;
  else if (distance <= threshold * .45) revealed = false;
  content.classList.toggle('is-firetruck-visible', revealed);
  firetruck.setAttribute('aria-hidden', String(!revealed));
  indicator.tabIndex = revealed ? -1 : 0;
  if (!revealed && document.activeElement === firetruck) content.focus({ preventScroll: true });
  if (wasRevealed && !revealed) focusTitle = false;
}

function queueTitle() {
  if (!scrollFrame) scrollFrame = requestAnimationFrame(updateTitle);
}

function configureMotion() {
  const canAnimate = !motion.matches && !preserveLinearView;
  content.classList.toggle('has-cdc-scroll', canAnimate);
  let contentFits = false;
  if (canAnimate) {
    const styles = getComputedStyle(hero);
    const opening = content.querySelector('.cdc-opening');
    const subtitle = content.querySelector('.cdc-subtitle');
    const requiredHeight = opening.offsetHeight + firetruck.firstElementChild.scrollHeight
      + subtitle.offsetHeight + parseFloat(getComputedStyle(subtitle).marginTop)
      + parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom)
      + parseFloat(styles.rowGap) + indicator.offsetHeight;
    contentFits = requiredHeight <= hero.clientHeight + 1;
  }
  scrollEnabled = canAnimate && contentFits;
  content.classList.toggle('has-cdc-scroll', scrollEnabled);
  if (!scrollEnabled) {
    firetruck.removeAttribute('aria-hidden');
    indicator.removeAttribute('tabindex');
    content.classList.remove('is-firetruck-visible');
    revealed = false;
    focusTitle = false;
  } else updateTitle();
}

indicator.addEventListener('click', event => {
  if (!scrollEnabled) return;
  event.preventDefault();
  focusTitle = true;
  const { start, threshold } = geometry();
  window.scrollTo({ top: start + threshold + 24, behavior: 'smooth' });
});
firetruck.addEventListener('transitionend', event => {
  if (event.target === firetruck && event.propertyName === 'opacity' && revealed && focusTitle) {
    focusTitle = false;
    firetruck.focus({ preventScroll: true });
  }
});
window.addEventListener('scroll', queueTitle, { passive: true });
window.addEventListener('resize', configureMotion);
window.addEventListener('pagehide', () => {
  restorePosition = window.scrollY;
  history.replaceState({ ...history.state, cdcScrollY: restorePosition }, '');
});
window.addEventListener('pageshow', event => {
  const position = event.persisted || Number.isFinite(restorePosition) ? restorePosition : undefined;
  const restoreView = () => {
    if (Number.isFinite(position)) window.scrollTo({ top: position, behavior: 'instant' });
    else if (initialTarget) {
      if (scrollEnabled && firetruck.contains(initialTarget)) {
        const { start, threshold } = geometry();
        window.scrollTo({ top: start + threshold + 24, behavior: 'instant' });
      } else initialTarget.scrollIntoView({ behavior: 'instant', block: 'start' });
    } else resetToTop();
    updateTitle();
  };
  restoreView();
  if (initialTarget || Number.isFinite(position)) requestAnimationFrame(restoreView);
});
motion.addEventListener('change', configureMotion);
if (!initialTarget && !Number.isFinite(restorePosition)) resetToTop();
configureMotion();
getComputedStyle(firetruck).opacity;
content.classList.remove('is-initializing');
