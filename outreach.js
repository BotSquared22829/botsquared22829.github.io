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

const trophyStage = document.querySelector('.outreach-trophy-stage');
const motionPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
let motionFrame = 0;
let trophyProgress;

function updateOutreachMotion() {
  motionFrame = 0;
  const viewHeight = window.innerHeight;
  const stage = trophyStage.getBoundingClientRect();
  const trophyTravel = Math.min(viewHeight * .54, stage.height);
  const trophyScroll = Math.min(1, Math.max(0, (viewHeight * .93 - stage.top) / trophyTravel));

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

const journey = document.querySelector('.outreach-journey');
const stage = journey.querySelector('.journey-stage');
const header = document.querySelector('.site-header');
const chapters = [...journey.querySelectorAll('[data-stops]')];
const stops = chapters.flatMap(chapter =>
  chapter.dataset.stops.trim().split(/\s+/).map(camera => ({ camera, chapter }))
);
// In the phone layout the copy sits below the video. A chapter fragment
// should bring the whole stage into view when it selects a camera stop.
const chapterIds = chapters.map(chapter => chapter.id);
const anchors = chapters.map(() => {
  const anchor = document.createElement('span');
  anchor.className = 'journey-anchor';
  anchor.setAttribute('aria-hidden', 'true');
  journey.prepend(anchor);
  return anchor;
});
const chapterNav = journey.querySelector('.journey-nav');
const video = journey.querySelector('video');
const routes = journey.querySelector('.journey-routes');
const lines = routes.querySelector('svg');
const pins = routes.querySelector('.journey-pins');
const venueList = journey.querySelector('.journey-venues');
const venues = [...venueList.querySelectorAll('[data-venue]')];
const home = venueList.dataset.origin.split(',').map(Number);
const narrowView = matchMedia('(max-width: 760px), (max-aspect-ratio: 1/1)');
const shortView = matchMedia('(max-height: 490px), (max-width: 760px) and (max-height: 610px)');
const clamp = value => Math.max(0, Math.min(1, value));
const media = {
  wide: { video: 'assets/outreach-map/wide.mp4?v=3', poster: 'assets/outreach-map/school.webp' },
  portrait: { video: 'assets/outreach-map/portrait.mp4?v=3', poster: 'assets/outreach-map/school-portrait.webp' }
};

let framing;
let unavailable = false;
let pendingLoad = 0;
let currentCamera;
let stopIndex = 0;
let decodedFrame = 0;
let pendingFrame = null;
let moving = false;
let reverse = false;
let playbackFrame = 0;
let presentationCallback = 0;

const chapterLinks = chapters.map((chapter, index) => {
  const link = document.createElement('a');
  link.href = '#' + chapter.id;
  link.textContent = chapter.dataset.nav;
  link.addEventListener('click', event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    history.pushState(null, '', link.hash);
    goToChapter(index);
  });
  chapterNav.append(link);
  return link;
});

function atJourney() {
  return framing && Math.abs(stage.getBoundingClientRect().top - header.getBoundingClientRect().bottom) < 3;
}

function goToChapter(index) {
  const stop = stops.findIndex(item => item.chapter === chapters[index]);
  showStop(stop, false);
  window.scrollTo({ top: window.scrollY + journey.getBoundingClientRect().top - header.offsetHeight, behavior: 'instant' });
}

function followChapterHash() {
  const index = chapterIds.findIndex(id => '#' + id === location.hash);
  if (framing && index >= 0) goToChapter(index);
}

function makePin(name, isHome) {
  const pin = document.createElement(isHome ? 'span' : 'button');
  pin.className = 'journey-pin' + (isHome ? ' origin' : '');
  const label = document.createElement('span');
  label.textContent = name;
  pin.append(label);
  if (!isHome) pin.type = 'button';
  pins.append(pin);
  return pin;
}

function placePin(pin, point) {
  pin.style.left = point[0]*100 + '%';
  pin.style.top = point[1]*100 + '%';
}

// Match the Blender camera to latitude, longitude and height above the Earth.
function project(lon, lat, altitude = 0) {
  const radians = Math.PI / 180;
  const phi = lat*radians;
  const lambda = lon*radians;
  const r = 6371 + altitude;
  const xyz = [r*Math.cos(phi)*Math.cos(lambda), r*Math.cos(phi)*Math.sin(lambda), r*Math.sin(phi), 1];
  const clip = currentCamera.clip.map(row => row.reduce((sum, value, i) => sum + value*xyz[i], 0));
  return [(1+clip[0]/clip[3])/2, (1-clip[1]/clip[3])/2];
}

const homePin = makePin('Killarney Secondary', true);
const venueRoutes = venues.map((venue, index) => {
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.style.setProperty('--route-delay', index * 120 + 'ms');
  path.setAttribute('pathLength', '1');
  lines.append(path);
  const pin = makePin(venue.dataset.venue, false);
  pin.setAttribute('aria-controls', venue.id);
  pin.setAttribute('aria-label', 'Show events at ' + venue.querySelector('h3').textContent);
  pin.addEventListener('click', () => selectVenue(index));
  return { pin, path };
});

function positionRoutes() {
  const [width, height] = framing === 'wide' ? [1440, 900] : [768, 896];
  lines.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
  venues.forEach((venue, index) => {
    const lon = Number(venue.dataset.lon);
    const lat = Number(venue.dataset.lat);
    const km = 111.2*Math.hypot((lon-home[0])*Math.cos(home[1]*Math.PI/180), lat-home[1]);
    const steps = [];
    for (let j = 0; j <= 32; j++) {
      const t = j/32;
      const altitude = Math.sin(Math.PI*t)*km*.24;
      const [x, y] = project(home[0]+(lon-home[0])*t, home[1]+(lat-home[1])*t, altitude);
      steps.push((j ? 'L' : 'M') + (x*width).toFixed(2) + ' ' + (y*height).toFixed(2));
    }
    venueRoutes[index].path.setAttribute('d', steps.join(' '));
    placePin(venueRoutes[index].pin, project(lon, lat));
  });
}

function selectVenue(index) {
  venues.forEach((venue, i) => {
    venue.hidden = i !== index;
    venueRoutes[i].pin.setAttribute('aria-pressed', String(i === index));
  });
}

function updateRoutes() {
  const { overhead, metro } = currentCamera.stops;
  const atVenues = stops[stopIndex].camera === 'metro' && decodedFrame === metro;
  const opacity = clamp((decodedFrame / overhead - .67) / .18);
  routes.hidden = video.readyState < 2 || opacity === 0 || decodedFrame > metro;
  homePin.style.opacity = opacity;
  if (!routes.hidden) placePin(homePin, currentCamera.origin[decodedFrame]);
  routes.classList.toggle('at-venues', atVenues);
  venueRoutes.forEach(({ pin }) => { pin.hidden = !atVenues; });
}

// The second half of the MP4 plays the same camera path backwards. Switching
// halves at the current pose lets the decoder play normally in either direction.
function cameraFrameAt(mediaTime) {
  const { last, fps } = currentCamera;
  const frame = Math.floor(mediaTime * fps + .0001);
  return Math.max(0, Math.min(frame, 2 * last - frame));
}

function presentPose(mediaTime) {
  const frame = cameraFrameAt(mediaTime);
  if (frame === decodedFrame) return;
  decodedFrame = frame;
  updateRoutes();
}

function onVideoFrame(now, metadata) {
  if (!framing) return;
  if (!video.seeking) presentPose(video.paused ? video.currentTime : metadata.mediaTime);
  presentationCallback = video.requestVideoFrameCallback(onVideoFrame);
}

function mediaFrameAt(frame) {
  return reverse ? 2 * currentCamera.last - frame : frame;
}

function requestPlayback() {
  if (framing && !playbackFrame) playbackFrame = requestAnimationFrame(updatePlayback);
}

function updatePlayback() {
  playbackFrame = 0;
  if (!framing || document.hidden || video.seeking || video.readyState < 2) return;
  const { fps, stops: frames } = currentCamera;
  const destination = frames[stops[stopIndex].camera];
  if (pendingFrame !== null) {
    const frame = mediaFrameAt(pendingFrame);
    pendingFrame = null;
    if (Math.floor(video.currentTime * fps) !== frame) {
      video.currentTime = (frame + .1) / fps;
      return;
    }
  }

  if (!moving) {
    presentPose(video.currentTime);
    return;
  }
  const endFrame = mediaFrameAt(destination);
  if (video.currentTime * fps >= endFrame) {
    video.pause();
    if (Math.floor(video.currentTime * fps) !== endFrame) {
      video.currentTime = (endFrame + .1) / fps;
      return;
    }
    moving = false;
    presentPose(video.currentTime);
    return;
  }
  if (!video.requestVideoFrameCallback) presentPose(video.currentTime);
  if (video.paused) video.play().catch(error => {
    if (error.name !== 'AbortError' && framing) useStaticJourney();
  });
  requestPlayback();
}

function showStop(index, animate) {
  stopIndex = index;
  const { camera, chapter } = stops[index];
  const destination = currentCamera.stops[camera];
  video.pause();
  moving = destination !== decodedFrame;
  reverse = animate && destination < decodedFrame;
  pendingFrame = animate ? decodedFrame : destination;
  chapters.forEach((article, i) => {
    const active = article === chapter;
    article.classList.toggle('is-current', active);
    article.inert = !active;
    if (active) chapterLinks[i].setAttribute('aria-current', 'step');
    else chapterLinks[i].removeAttribute('aria-current');
  });
  updateRoutes();
  requestPlayback();
}

function canStep(direction) {
  const next = stopIndex + direction;
  return next >= 0 && next < stops.length;
}

const wheelThreshold = 32; // CSS pixels of deliberate movement per stop
let lastWheelAt = -Infinity;
let lastWheelDelta = 0;
let wheelDistance = 0;
let spentDirection = 0;
let quietestDelta = Infinity;

window.addEventListener('wheel', event => {
  const mode = event.deltaMode;
  const delta = event.deltaY;
  const magnitude = Math.abs(delta);
  if (!event.cancelable || event.ctrlKey || Math.abs(event.deltaX) > magnitude || !delta) return;

  const direction = Math.sign(delta);
  const gap = event.timeStamp - lastWheelAt;
  // A new push can arrive while the previous flick is still coasting.
  // Detect it from rising deltas or a sustained change of direction.
  const freshPush = magnitude >= Math.max(5, quietestDelta * 1.75);
  const reversed = direction !== spentDirection && direction === Math.sign(lastWheelDelta);
  const wheelClick = mode !== 0 || (gap >= 45 && magnitude >= wheelThreshold && delta === lastWheelDelta);
  if (gap >= 110 || wheelClick || (spentDirection && (freshPush || reversed))) {
    spentDirection = 0;
    quietestDelta = Infinity;
    wheelDistance = 0;
  }
  lastWheelAt = event.timeStamp;
  lastWheelDelta = delta;

  const onStage = atJourney();
  if (!onStage || moving || spentDirection) {
    if (onStage) event.preventDefault();
    if (!spentDirection) spentDirection = direction;
    quietestDelta = Math.min(quietestDelta, magnitude);
    wheelDistance = 0;
    return;
  }
  if (!canStep(direction)) return;
  event.preventDefault();
  if (Math.sign(wheelDistance) !== direction) wheelDistance = 0;
  wheelDistance += delta;
  if (mode !== 0 || Math.abs(wheelDistance) >= wheelThreshold) {
    spentDirection = direction;
    quietestDelta = magnitude;
    showStop(stopIndex + direction, true);
  }
}, { passive: false });

let swipe = null;
stage.addEventListener('touchstart', event => {
  const touch = event.touches[0];
  swipe = atJourney() && event.touches.length === 1 ?
    { x: touch.clientX, y: touch.clientY, spent: moving } : null;
}, { passive: true });

stage.addEventListener('touchmove', event => {
  if (!swipe || event.touches.length !== 1 || !event.cancelable) return;
  const touch = event.touches[0];
  const dy = swipe.y - touch.clientY;
  if (Math.abs(touch.clientX - swipe.x) > Math.abs(dy) || !dy) return;
  const direction = Math.sign(dy);
  if (!swipe.spent && !moving && !canStep(direction)) {
    swipe = null;
    return;
  }
  event.preventDefault();
  if (moving) swipe.spent = true;
  if (!swipe.spent && Math.abs(dy) >= 55) {
    swipe.spent = true;
    showStop(stopIndex + direction, true);
  }
}, { passive: false });

for (const type of ['touchend', 'touchcancel']) {
  stage.addEventListener(type, () => { swipe = null; }, { passive: true });
}

window.addEventListener('keydown', event => {
  if (!atJourney() || event.defaultPrevented || event.ctrlKey || event.altKey || event.metaKey ||
      event.target.closest('input, textarea, select, [contenteditable="true"]')) return;
  const keys = { ArrowDown: 1, PageDown: 1, ArrowUp: -1, PageUp: -1 };
  const direction = event.key === ' ' && !event.target.closest('button') ? (event.shiftKey ? -1 : 1) : keys[event.key];
  if (!direction || (!moving && !event.repeat && !canStep(direction))) return;
  event.preventDefault();
  if (!moving && !event.repeat) showStop(stopIndex + direction, true);
});

function setMode() {
  const supported = !unavailable && typeof outreachMapCameras !== 'undefined' && video.canPlayType('video/mp4');
  chapterNav.hidden = !supported;
  const next = supported && !motionPreference.matches && !shortView.matches ?
    (narrowView.matches ? 'portrait' : 'wide') : null;
  if (next === framing) return;
  const onStage = atJourney();
  const oldChapter = stops[stopIndex].chapter;
  clearTimeout(pendingLoad);
  video.pause();
  cancelAnimationFrame(playbackFrame);
  playbackFrame = 0;
  if (presentationCallback) video.cancelVideoFrameCallback(presentationCallback);
  presentationCallback = 0;
  framing = next;
  moving = false;
  pendingFrame = null;
  swipe = null;
  journey.classList.toggle('is-stepped', Boolean(framing));
  chapters.forEach((chapter, i) => {
    const [target, previous] = framing ? [anchors[i], chapter] : [chapter, anchors[i]];
    previous.removeAttribute('id');
    target.id = chapterIds[i];
  });
  if (!framing) {
    video.removeAttribute('src');
    video.load();
    chapters.forEach(chapter => { chapter.inert = false; });
    venues.forEach(venue => { venue.hidden = false; });
    if (onStage && oldChapter) oldChapter.scrollIntoView({ behavior: 'instant' });
    return;
  }
  currentCamera = outreachMapCameras[framing];
  decodedFrame = 0;
  selectVenue(0);
  video.poster = media[framing].poster;
  video.preload = 'auto';
  video.src = media[framing].video;
  if (video.requestVideoFrameCallback) presentationCallback = video.requestVideoFrameCallback(onVideoFrame);
  video.playbackRate = 1.5;
  positionRoutes();
  showStop(stopIndex, false);
  watchForStall();
}

function useStaticJourney() {
  if (!framing) return;
  unavailable = true;
  setMode();
}

function watchForStall() {
  clearTimeout(pendingLoad);
  pendingLoad = setTimeout(() => {
    if (framing && (video.seeking || video.readyState < 2 || (moving && video.readyState < 3))) {
      useStaticJourney();
    }
  }, 15000);
}

video.addEventListener('seeking', watchForStall);
video.addEventListener('waiting', watchForStall);
video.addEventListener('loadeddata', () => { clearTimeout(pendingLoad); requestPlayback(); });
video.addEventListener('seeked', () => {
  clearTimeout(pendingLoad);
  if (!framing) return;
  presentPose(video.currentTime);
  requestPlayback();
});
video.addEventListener('canplay', requestPlayback);
video.addEventListener('error', useStaticJourney);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) video.pause();
  else if (framing) showStop(stopIndex, false);
});
[motionPreference, narrowView, shortView].forEach(query => query.addEventListener('change', setMode));
window.addEventListener('resize', setMode);
// CSS also hides the chapter controls in the linear layout. Observe their
// visibility so a restored/background tab picks up a missed media-query event.
new ResizeObserver(setMode).observe(chapterNav);
window.addEventListener('pageshow', setMode);
window.addEventListener('hashchange', followChapterHash);
setMode();
followChapterHash();
