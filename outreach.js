const tabList = document.querySelector('.outreach-project-tabs');
const tabs = [...tabList.querySelectorAll('[role="tab"]')];
const projects = tabs.map(tab => document.getElementById(tab.getAttribute('aria-controls')));

function selectProject(selectedTab) {
  tabList.style.setProperty('--outreach-tab-index', tabs.indexOf(selectedTab));
  tabs.forEach((tab, index) => {
    const selected = tab === selectedTab;
    tab.setAttribute('aria-selected', String(selected));
    tab.tabIndex = selected ? 0 : -1;
    projects[index].hidden = !selected;
  });
}

projects.forEach((project, index) => {
  project.setAttribute('role', 'tabpanel');
  project.setAttribute('aria-labelledby', tabs[index].id);
  project.tabIndex = 0;
});
selectProject(tabs[0]);
tabList.hidden = false;

tabList.addEventListener('click', event => {
  const tab = event.target.closest('[role="tab"]');
  if (tab) selectProject(tab);
});

tabList.addEventListener('keydown', event => {
  const index = tabs.indexOf(event.target);
  if (index < 0) return;

  let nextIndex;
  switch (event.key) {
    case 'ArrowRight': nextIndex = (index + 1) % tabs.length; break;
    case 'ArrowLeft': nextIndex = (index + tabs.length - 1) % tabs.length; break;
    case 'Home': nextIndex = 0; break;
    case 'End': nextIndex = tabs.length - 1; break;
    default: return;
  }

  event.preventDefault();
  selectProject(tabs[nextIndex]);
  tabs[nextIndex].focus();
});

const hero = document.querySelector('.outreach-hero');
const trophyStage = document.querySelector('.outreach-trophy-stage');
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
let motionFrame = 0;
let heroProgress;
let trophyProgress;

function updateOutreachMotion() {
  motionFrame = 0;
  const viewHeight = window.innerHeight;
  const stage = trophyStage.getBoundingClientRect();
  const heroScroll = Math.min(1, Math.max(0, window.scrollY / hero.offsetHeight));
  const trophyTravel = Math.min(viewHeight * .54, stage.height);
  const trophyScroll = Math.min(1, Math.max(0, (viewHeight * .93 - stage.top) / trophyTravel));

  if (heroScroll !== heroProgress) {
    heroProgress = heroScroll;
    hero.style.setProperty('--outreach-scroll', heroScroll);
  }
  if (trophyScroll !== trophyProgress) {
    trophyProgress = trophyScroll;
    trophyStage.style.setProperty('--outreach-trophy-scroll', trophyScroll);
  }
}

function requestOutreachMotion() {
  if (!motionPreference.matches && !motionFrame) {
    motionFrame = requestAnimationFrame(updateOutreachMotion);
  }
}

window.addEventListener('scroll', requestOutreachMotion, { passive: true });
window.addEventListener('resize', requestOutreachMotion);
window.addEventListener('pageshow', requestOutreachMotion);
motionPreference.addEventListener('change', requestOutreachMotion);
requestOutreachMotion();
