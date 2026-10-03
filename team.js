const overview = document.querySelector('.team-overview');
const photo = document.querySelector('.team-group-photo');
const islands = [...document.querySelectorAll('.department-island')];
const members = [...document.querySelectorAll('[data-member-department]')];
const roster = document.querySelector('.member-grid');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const surface = document.createElement('div');
surface.className = 'department-surface';
surface.setAttribute('role', 'region');
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
  if (reducedMotion.matches || from.clipPath === to.clipPath) {
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
  surface.removeAttribute('aria-labelledby');
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
  surface.setAttribute('aria-labelledby', island.querySelector('h2').id);
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
  expand.addEventListener('click', () => {
    if (expandedIsland === island && !closing) closeIsland();
    else openIsland(island);
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
reducedMotion.addEventListener('change', () => {
  if (reducedMotion.matches) settleSurface();
});
