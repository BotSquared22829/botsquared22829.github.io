const overview = document.querySelector('.team-overview');
const photo = document.querySelector('.team-group-photo');
const islands = [...document.querySelectorAll('.department-island')];
const members = [...document.querySelectorAll('[data-member-department]')];
const roster = document.querySelector('.member-grid');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
let motionReduced = reducedMotion.matches;
const surface = document.createElement('div');
surface.className = 'department-surface';
surface.hidden = true;
overview.prepend(surface);
const contents = new Map();
let expandedIsland = null;
let animation = null;
let closing = false;

// Photo regions, numbered left to right, in the source image's 1210 × 908 coordinates.
// Department membership is supplied by data-spotlight-people on each island.
const spotlightRegions = {
  1: '247,320 293,309 327,328 334,373 324,417 306,466 274,518 258,644 278,742 300,782 288,852 245,894 214,831 197,713 170,606 173,508 196,443 238,414',
  2: '343,379 384,365 409,382 429,433 436,480 468,500 477,596 470,677 408,678 400,731 369,755 337,788 304,839 289,787 273,708 265,594 280,517 318,477 325,419',
  3: '472,300 510,287 540,307 546,352 539,397 554,425 575,439 550,478 523,505 505,569 506,682 478,684 478,584 467,499 440,482 427,447 458,418 471,398',
  4: '564,374 596,357 623,369 641,400 646,439 635,477 666,499 684,546 681,610 654,686 521,686 506,625 506,556 521,507 558,478 550,434 550,399',
  5: '653,309 690,291 720,303 736,333 734,377 723,408 750,425 771,467 765,555 758,637 774,683 754,759 668,758 667,697 651,684 681,609 686,549 666,496 641,480 649,443 634,424 657,409 646,364',
  6: '810,286 849,269 881,285 903,316 899,358 885,393 928,391 943,409 939,477 929,565 939,643 935,698 949,771 863,765 820,753 776,759 766,690 754,636 762,552 766,466 757,435 788,410 822,395 804,361 797,319',
  7: '983,316 1026,301 1065,310 1080,342 1070,389 1060,415 1095,431 1121,450 1133,519 1143,634 1134,676 1121,697 1117,779 1093,873 1058,849 1027,798 991,788 945,779 940,709 931,636 935,551 938,476 954,440 994,423 981,386 975,345'
};
const svgNamespace = 'http://www.w3.org/2000/svg';
const spotlightOverlay = document.createElementNS(svgNamespace, 'svg');
spotlightOverlay.setAttribute('viewBox', '0 0 1210 908');
spotlightOverlay.setAttribute('aria-hidden', 'true');
spotlightOverlay.classList.add('team-spotlight-overlay');
spotlightOverlay.innerHTML = '<defs><filter id="team-spotlight-soften" x="-20%" y="-20%" width="140%" height="140%"><feMorphology operator="dilate" radius="14"/><feGaussianBlur stdDeviation="24"/></filter><mask id="team-spotlight-mask" maskUnits="userSpaceOnUse" x="0" y="0" width="1210" height="908" style="mask-type: luminance"><rect width="1210" height="908" fill="white"/><g fill="black" filter="url(#team-spotlight-soften)"></g></mask></defs><rect width="1210" height="908" fill="black" fill-opacity=".76" mask="url(#team-spotlight-mask)"/>';
photo.append(spotlightOverlay);
const spotlightCutouts = spotlightOverlay.querySelector('g');
let spotlightIsland = null;

function clearSpotlight() {
  photo.classList.remove('is-spotlit');
  spotlightIsland?.querySelector('.department-spotlight').setAttribute('aria-pressed', 'false');
  spotlightIsland = null;
}

function toggleSpotlight(island) {
  if (spotlightIsland === island) {
    clearSpotlight();
    return;
  }
  clearSpotlight();
  // Settle any opening/closing panel before revealing the original photo.
  cancelAnimation();
  restoreOverview();
  const cutouts = (island.dataset.spotlightPeople || '').split(/\s+/)
    .filter(person => spotlightRegions[person])
    .map(person => {
      const polygon = document.createElementNS(svgNamespace, 'polygon');
      polygon.setAttribute('points', spotlightRegions[person]);
      return polygon;
    });
  if (!cutouts.length) return;
  spotlightCutouts.replaceChildren(...cutouts);
  spotlightIsland = island;
  island.querySelector('.department-spotlight').setAttribute('aria-pressed', 'true');
  photo.classList.add('is-spotlit');
}

function slotFrame(island) {
  const bounds = overview.getBoundingClientRect();
  const slot = island.parentElement.getBoundingClientRect();
  return {
    clipPath: `inset(${slot.top - bounds.top}px ${bounds.right - slot.right}px ${bounds.bottom - slot.bottom}px ${slot.left - bounds.left}px round 22px)`
  };
}

function fullFrame() {
  return {
    clipPath: `inset(0px 0px 0px 0px round ${getComputedStyle(photo).borderTopLeftRadius})`
  };
}

function surfaceFrame() {
  return { clipPath: getComputedStyle(surface).clipPath };
}

function cancelAnimation() {
  if (!animation) return;
  animation.onfinish = null;
  animation.cancel();
  animation = null;
}

function settleSurface() {
  cancelAnimation();
  if (closing) restoreOverview();
  else if (expandedIsland) {
    Object.assign(surface.style, fullFrame());
    overview.classList.add('is-open');
  }
}

function animateSurface(from, to) {
  cancelAnimation();
  // The background and contents share one clip, without scaling portraits or text.
  // Persist the destination before animating so completion cannot flash a stale frame.
  Object.assign(surface.style, to);
  if (motionReduced || from.clipPath === to.clipPath) {
    settleSurface();
    return;
  }
  animation = surface.animate([from, to], {
    duration: 550, easing: 'cubic-bezier(.22,1,.36,1)', fill: 'both'
  });
  animation.onfinish = settleSurface;
}

function resetIsland(island) {
  island.classList.remove('is-expanded');
  contents.get(island).hidden = true;
  const button = island.querySelector('.department-expand');
  button.setAttribute('aria-expanded', 'false');
  button.setAttribute('aria-label', `More about ${island.querySelector('h2').textContent}`);
}

function restoreOverview() {
  if (expandedIsland) resetIsland(expandedIsland);
  overview.classList.remove('has-expanded', 'is-open');
  surface.hidden = true;
  expandedIsland = null;
  closing = false;
}

function closeIsland() {
  if (!expandedIsland || closing) return;
  const from = surfaceFrame();
  const island = expandedIsland;
  closing = true;
  overview.classList.remove('is-open');
  contents.get(island).hidden = true;
  animateSurface(from, slotFrame(island));
}

function openIsland(island) {
  clearSpotlight();
  // Continue from the rendered frame on reversal or a department switch.
  const from = expandedIsland ? surfaceFrame() : slotFrame(island);
  if (expandedIsland) resetIsland(expandedIsland);
  closing = false;
  expandedIsland = island;
  island.classList.add('is-expanded');
  contents.get(island).hidden = false;
  const button = island.querySelector('.department-expand');
  button.setAttribute('aria-expanded', 'true');
  button.setAttribute('aria-label', `Close ${island.querySelector('h2').textContent}`);
  overview.classList.add('has-expanded');
  surface.hidden = false;
  animateSurface(from, fullFrame());
}

islands.forEach(island => {
  const slot = document.createElement('div');
  slot.className = 'department-slot';
  island.before(slot);
  slot.append(island);
  const title = island.querySelector('h2');
  title.id = `${island.dataset.department}-title`;
  island.setAttribute('aria-labelledby', title.id);
  const content = island.querySelector('.department-content');
  // The shared animation surface precedes the controls in DOM order. Give
  // keyboard users a direct way into its scrollable content when it opens.
  content.tabIndex = 0;
  content.setAttribute('role', 'region');
  content.setAttribute('aria-labelledby', title.id);
  const memberGrid = document.createElement('div');
  memberGrid.className = 'department-members';
  members.filter(member => member.dataset.memberDepartment === island.dataset.department).forEach(member => {
    const oldHeading = member.querySelector('h2');
    const heading = document.createElement('h3');
    heading.textContent = oldHeading.textContent;
    oldHeading.replaceWith(heading);
    memberGrid.append(member);
  });
  content.append(memberGrid);
  content.hidden = true;
  contents.set(island, content);
  surface.append(content);
  const expand = island.querySelector('.department-expand');
  expand.hidden = false;
  const spotlight = island.querySelector('.department-spotlight');
  spotlight.hidden = false;
  spotlight.disabled = !(island.dataset.spotlightPeople || '').split(/\s+/).some(person => spotlightRegions[person]);
  spotlight.setAttribute('aria-pressed', 'false');
  spotlight.addEventListener('click', () => toggleSpotlight(island));
  expand.addEventListener('click', event => {
    if (expandedIsland === island && !closing) closeIsland();
    else {
      openIsland(island);
      if (event.detail === 0) {
        content.focus({ preventScroll: true });
        content.scrollIntoView({ block: 'center', behavior: 'instant' });
      }
    }
  });
});
roster.hidden = true;

document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && spotlightIsland) {
    spotlightIsland.querySelector('.department-spotlight').focus({ preventScroll: true });
    clearSpotlight();
  }
  if (event.key === 'Escape' && expandedIsland) {
    expandedIsland.querySelector('.department-expand').focus({ preventScroll: true });
    closeIsland();
  }
});
function updateLayout() {
  overview.style.setProperty('--department-content-height', `${photo.getBoundingClientRect().height}px`);
  settleSurface();
}
// Container and image changes can resize the panel without a window resize.
new ResizeObserver(updateLayout).observe(overview);
window.addEventListener('resize', updateLayout);
updateLayout();

// Scroll rotates two adjacent faces of an invisible rectangular block.
// The first and last portions hold each message still before the page continues.
const unity = document.querySelector('.team-unity');
const unityStage = unity.querySelector('.team-unity-stage');
let unityFramePending = false;
let unityConnectionProgress = 0;

function updateUnity() {
  unityFramePending = false;
  if (motionReduced) return;
  const headerHeight = document.querySelector('.site-header').getBoundingClientRect().height;
  const travel = Math.max(1, unity.offsetHeight - unityStage.offsetHeight);
  const progress = Math.max(0, Math.min(1, (headerHeight - unity.getBoundingClientRect().top) / travel));
  const turn = Math.max(0, Math.min(1, (progress - 0.15) / 0.6));
  const eased = turn * turn * (3 - 2 * turn);
  unityConnectionProgress = Math.max(0, Math.min(1, (eased - 0.55) / 0.45));
  unity.style.setProperty('--unity-angle', `${eased * 90}deg`);
  unity.style.setProperty('--unity-divided-opacity', 1 - eased);
  unity.style.setProperty('--unity-united-opacity', eased);
  unity.style.setProperty('--hint-opacity', Math.max(0, 1 - progress * 12));
}

function layoutUnity() {
  unity.classList.toggle('unity-scroll-ready', !motionReduced);
  updateUnity();
}

window.addEventListener('scroll', () => {
  if (unityFramePending || motionReduced) return;
  unityFramePending = true;
  requestAnimationFrame(updateUnity);
}, { passive: true });
window.addEventListener('resize', layoutUnity, { passive: true });
layoutUnity();

// Separate particles become a network as the second face comes into view.
const unityNetwork = unity.querySelector('.team-unity-network');
let networkWidth = 0;
let networkHeight = 0;
let networkDots = [];
let networkLinks = [];
let networkFrame = null;
let networkVisible = false;
let networkTime = 0;
let networkPreviousTime = null;
let networkConnection = null;
const networkPointer = { x: 0, y: 0, targetX: 0, targetY: 0, strength: 0, active: false };

unityStage.addEventListener('pointermove', event => {
  if (event.pointerType === 'touch' || motionReduced) return;
  const bounds = unityStage.getBoundingClientRect();
  networkPointer.targetX = event.clientX - bounds.left;
  networkPointer.targetY = event.clientY - bounds.top;
  if (!networkPointer.active) {
    networkPointer.x = networkPointer.targetX;
    networkPointer.y = networkPointer.targetY;
  }
  networkPointer.active = true;
}, { passive: true });
unityStage.addEventListener('pointerleave', () => { networkPointer.active = false; });
unityStage.addEventListener('pointercancel', () => { networkPointer.active = false; });

function layoutNetwork() {
  networkPointer.active = false;
  networkPointer.strength = 0;
  networkConnection = null;
  const bounds = unityStage.getBoundingClientRect();
  networkWidth = bounds.width;
  networkHeight = bounds.height;
  unityNetwork.setAttribute('viewBox', `0 0 ${networkWidth} ${networkHeight}`);
  const columns = networkWidth < 600 ? 5 : 8;
  const rows = 6;
  // Deterministic offsets keep the composition stable through resize.
  const random = seed => { const value = Math.sin(seed * 127.1 + 311.7) * 43758.5453; return value - Math.floor(value); };
  networkDots = Array.from({ length: columns * rows }, (_, index) => {
    const dot = document.createElementNS(svgNamespace, 'circle');
    dot.setAttribute('r', 1.5 + random(index + 80) * 1.4);
    dot.setAttribute('opacity', '.65');
    return {
      element: dot,
      x: ((index % columns) + 0.2 + random(index + 1) * 0.6) / columns * networkWidth,
      y: (Math.floor(index / columns) + 0.2 + random(index + 30) * 0.6) / rows * networkHeight,
      phase: random(index + 100) * Math.PI * 2
    };
  });
  const pairs = new Set();
  networkLinks = [];
  networkDots.forEach((dot, index) => {
    networkDots.map((other, target) => ({ target, distance: Math.hypot(dot.x - other.x, dot.y - other.y) }))
      .filter(other => other.target !== index)
      .sort((a, b) => a.distance - b.distance).slice(0, 3)
      .forEach(({ target }) => {
        const key = [Math.min(index, target), Math.max(index, target)].join('-');
        if (pairs.has(key)) return;
        pairs.add(key);
        const line = document.createElementNS(svgNamespace, 'line');
        line.setAttribute('stroke', '#ff5964');
        line.setAttribute('stroke-width', '.8');
        line.setAttribute('pathLength', '1');
        line.setAttribute('stroke-dasharray', '1');
        networkLinks.push({ element: line, from: index, to: target });
      });
  });
  unityNetwork.replaceChildren(...networkLinks.map(link => link.element), ...networkDots.map(dot => dot.element));
  drawNetwork();
}

function drawNetwork() {
  const connected = motionReduced ? 1 : unityConnectionProgress;
  const connectionChanged = connected !== networkConnection;
  if (connectionChanged) {
    // Every dot shares this color; inherit it instead of rewriting each dot.
    unityNetwork.setAttribute('fill', `rgb(${190 + connected * 65}, ${190 - connected * 90}, ${202 - connected * 87})`);
  }
  const drift = motionReduced ? 0 : networkTime / 1000;
  const restless = 1 - connected;
  const amplitude = Math.min(85, networkWidth * 0.16);
  const cursorStrength = motionReduced ? 0 : networkPointer.strength;
  const cursorRadius = Math.min(300, networkWidth * 0.7);
  const positions = networkDots.map(dot => {
    // Blend separate paths so scrolling changes energy without jumping phase.
    const wildX = (Math.sin(drift * 0.7 + dot.phase) + Math.sin(drift * 0.31 + dot.phase * 2) * 0.35) * amplitude;
    const wildY = (Math.cos(drift * 0.58 + dot.phase) + Math.sin(drift * 0.43 + dot.phase * 1.7) * 0.35) * amplitude;
    let x = dot.x + wildX * restless + Math.sin(drift * 0.24 + dot.phase) * 14 * connected;
    let y = dot.y + wildY * restless + Math.cos(drift * 0.18 + dot.phase) * 17 * connected;
    const dx = networkPointer.x - x;
    const dy = networkPointer.y - y;
    const influence = Math.max(0, 1 - Math.hypot(dx, dy) / cursorRadius);
    const pull = influence * influence * cursorStrength * (0.55 - connected * 0.3);
    x += dx * pull + (networkPointer.x / networkWidth - 0.5) * 22 * cursorStrength;
    y += dy * pull + (networkPointer.y / networkHeight - 0.5) * 22 * cursorStrength;
    x = Math.max(5, Math.min(networkWidth - 5, x));
    y = Math.max(5, Math.min(networkHeight - 5, y));
    dot.element.setAttribute('cx', x);
    dot.element.setAttribute('cy', y);
    return { x, y };
  });
  networkLinks.forEach((link, index) => {
    const from = positions[link.from];
    const to = positions[link.to];
    link.element.setAttribute('x1', from.x);
    link.element.setAttribute('y1', from.y);
    link.element.setAttribute('x2', to.x);
    link.element.setAttribute('y2', to.y);
    if (connectionChanged) {
      const reveal = Math.max(0, Math.min(1, (connected - (index % 7) * 0.025) / 0.85));
      link.element.setAttribute('opacity', reveal * 0.32);
      link.element.setAttribute('stroke-dashoffset', 1 - reveal);
    }
  });
  networkConnection = connected;
}

function animateNetwork(time) {
  const elapsed = networkPreviousTime === null ? 16 : Math.min(50, time - networkPreviousTime);
  networkTime += elapsed;
  networkPreviousTime = time;
  const follow = 1 - Math.exp(-elapsed / 140);
  networkPointer.x += (networkPointer.targetX - networkPointer.x) * follow;
  networkPointer.y += (networkPointer.targetY - networkPointer.y) * follow;
  networkPointer.strength += ((networkPointer.active ? 1 : 0) - networkPointer.strength) * follow;
  drawNetwork();
  networkFrame = requestAnimationFrame(animateNetwork);
}

function syncNetworkMotion() {
  if (networkFrame !== null) cancelAnimationFrame(networkFrame);
  networkFrame = null;
  networkPreviousTime = null;
  if (!networkVisible || document.hidden || motionReduced) {
    networkPointer.active = false;
    networkPointer.strength = 0;
  }
  if (networkVisible && !document.hidden && !motionReduced) networkFrame = requestAnimationFrame(animateNetwork);
  else drawNetwork();
}

new ResizeObserver(layoutNetwork).observe(unityStage);
new IntersectionObserver(([entry]) => {
  networkVisible = entry.isIntersecting;
  syncNetworkMotion();
}).observe(unityStage);
document.addEventListener('visibilitychange', syncNetworkMotion);
reducedMotion.addEventListener('change', event => {
  motionReduced = event.matches;
  if (motionReduced) settleSurface();
  layoutUnity();
  syncNetworkMotion();
});
layoutNetwork();
