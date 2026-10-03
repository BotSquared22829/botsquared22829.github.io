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
  spotlight.disabled = true;
  expand.addEventListener('click', () => {
    if (expandedIsland === island && !closing) closeIsland();
    else openIsland(island);
  });
});
roster.hidden = true;

document.addEventListener('keydown', event => {
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
