// The camera positions the anchor. Only the card and the free end of its tether move.
(() => {
  const stage = document.querySelector('.v5-stage');
  const picker = stage.querySelector('.v5-picker');
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const pins = Array.from(stage.querySelectorAll('.v5-pin'), (element, index) => ({
    element,
    card: element.querySelector('.v5-card'),
    phase: index * 1.7,
    x: 0, y: 0, vx: 0, vy: 0,
    drag: null,
    suppressClick: false,
  }));
  let selection = picker.querySelector(':checked').id;
  let inView = false;
  let frame = 0;
  let lastTime = 0;

  function position(pin, x, y) {
    pin.x = x;
    pin.y = y;
    pin.element.style.setProperty('--dx', x.toFixed(2) + 'px');
    pin.element.style.setProperty('--dy', y.toFixed(2) + 'px');
  }

  function animate(time) {
    const dt = Math.min((time - lastTime) / 1000, 1 / 30);
    lastTime = time;
    for (const pin of pins) {
      if (pin.drag || (selection !== 'v5-overview' && pin.card.htmlFor !== selection)) continue;
      const phase = time / 1400 + pin.phase;
      const targetX = 2.5 * Math.sin(phase);
      const targetY = 3 * Math.sin(phase * .78 + pin.phase);
      // An underdamped spring keeps release velocity and settles into a gentle drift.
      pin.vx += ((targetX - pin.x) * 145 - 12 * pin.vx) * dt;
      pin.vy += ((targetY - pin.y) * 145 - 12 * pin.vy) * dt;
      position(pin, pin.x + pin.vx * dt, pin.y + pin.vy * dt);
    }
    frame = requestAnimationFrame(animate);
  }

  function syncMotion() {
    cancelAnimationFrame(frame);
    if (reducedMotion.matches) {
      for (const pin of pins) {
        pin.vx = pin.vy = 0;
        if (!pin.drag) position(pin, 0, 0);
      }
    } else if (inView && !document.hidden) {
      lastTime = performance.now();
      frame = requestAnimationFrame(animate);
    }
  }

  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
  for (const pin of pins) {
    const { card } = pin;
    card.addEventListener('pointerdown', event => {
      if (!event.isPrimary || event.button !== 0 || pin.drag) return;
      const box = card.getBoundingClientRect();
      const bounds = stage.getBoundingClientRect();
      const dock = picker.getBoundingClientRect();
      pin.drag = {
        id: event.pointerId, startX: event.clientX, startY: event.clientY,
        initialX: pin.x, initialY: pin.y, time: event.timeStamp, moved: false,
        minX: pin.x + bounds.left + 5 - box.left, maxX: pin.x + bounds.right - 5 - box.right,
        minY: pin.y + bounds.top + 5 - box.top, maxY: pin.y + dock.top - 5 - box.bottom,
      };
      pin.vx = pin.vy = 0;
      pin.suppressClick = false;
      card.setPointerCapture(event.pointerId);
    });

    card.addEventListener('pointermove', event => {
      const drag = pin.drag;
      if (drag?.id !== event.pointerId) return;
      const dx = event.clientX - drag.startX;
      const dy = event.clientY - drag.startY;
      const distance = Math.hypot(dx, dy);
      if (!drag.moved && distance < 5) return;
      drag.moved = true;
      pin.element.classList.add('is-dragging');
      const resistance = 1 / (1 + distance / 104);
      const x = clamp(drag.initialX + dx * resistance, drag.minX, drag.maxX);
      const y = clamp(drag.initialY + dy * resistance, drag.minY, drag.maxY);
      const dt = Math.max(.008, (event.timeStamp - drag.time) / 1000);
      pin.vx = clamp((x - pin.x) / dt, -200, 200);
      pin.vy = clamp((y - pin.y) / dt, -200, 200);
      drag.time = event.timeStamp;
      position(pin, x, y);
    });

    function release(event) {
      if (pin.drag?.id !== event.pointerId) return;
      pin.suppressClick = pin.drag.moved;
      if (event.timeStamp - pin.drag.time > 80) pin.vx = pin.vy = 0;
      pin.drag = null;
      pin.element.classList.remove('is-dragging');
      if (reducedMotion.matches) position(pin, 0, 0);
    }
    card.addEventListener('pointerup', release);
    card.addEventListener('pointercancel', release);
    card.addEventListener('lostpointercapture', release);
    card.addEventListener('click', event => {
      if (pin.suppressClick) {
        event.preventDefault();
        pin.suppressClick = false;
      } else if (card.control.checked) {
        event.preventDefault();
        picker.querySelector('#v5-overview').click();
      }
    });
  }

  picker.addEventListener('change', event => { selection = event.target.id; });
  window.addEventListener('pageshow', () => { selection = picker.querySelector(':checked').id; });
  new IntersectionObserver(([entry]) => {
    inView = entry.isIntersecting;
    syncMotion();
  }).observe(stage);
  reducedMotion.addEventListener('change', syncMotion);
  document.addEventListener('visibilitychange', syncMotion);
})();
