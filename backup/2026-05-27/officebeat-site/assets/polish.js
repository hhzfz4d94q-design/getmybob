// OfficeBeat — small polish layer: scroll-reveal + animated stat counters
(function(){
  // Scroll-reveal: add .reveal to every section, then toggle .in when 30% visible
  document.querySelectorAll('section').forEach(s => s.classList.add('reveal'));
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { threshold: 0.15 });
    document.querySelectorAll('.reveal').forEach(el => io.observe(el));
  } else {
    document.querySelectorAll('.reveal').forEach(el => el.classList.add('in'));
  }

  // Animated stat counters: any .stat .num with text like "35+" or "$15M+" or "20+"
  function animateCounter(el) {
    const raw = el.textContent.trim();
    const m = raw.match(/^(\$?)(\d+(?:\.\d+)?)([KMB+]*)$/);
    if (!m) return;
    const prefix = m[1], target = parseFloat(m[2]), suffix = m[3];
    let start = 0;
    const dur = 1200;
    const t0 = performance.now();
    el.classList.add('counting');
    function step(now) {
      const p = Math.min(1, (now - t0) / dur);
      const v = Math.floor(start + (target - start) * (0.5 - 0.5 * Math.cos(Math.PI * p)));
      el.textContent = prefix + v + suffix;
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = raw;
    }
    requestAnimationFrame(step);
  }
  if ('IntersectionObserver' in window) {
    const co = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) { animateCounter(e.target); co.unobserve(e.target); }
      });
    }, { threshold: 0.5 });
    document.querySelectorAll('.stat .num').forEach(el => co.observe(el));
  }
})();

// Testimonial slider
(function(){
  const track = document.getElementById('t-track');
  const dotsEl = document.getElementById('t-dots');
  if (!track || !dotsEl) return;
  const slides = track.querySelectorAll('.testimonial');
  let idx = 0;
  slides.forEach((_, i) => {
    const b = document.createElement('button');
    b.className = 't-dot' + (i === 0 ? ' active' : '');
    b.setAttribute('aria-label', 'Show testimonial ' + (i+1));
    b.addEventListener('click', () => go(i));
    dotsEl.appendChild(b);
  });
  function go(i){
    idx = (i + slides.length) % slides.length;
    track.style.transform = 'translateX(-' + (idx * 100) + '%)';
    dotsEl.querySelectorAll('.t-dot').forEach((d, j) => d.classList.toggle('active', j === idx));
  }
  let timer = setInterval(() => go(idx + 1), 6500);
  const slider = document.getElementById('t-slider');
  slider.addEventListener('mouseenter', () => clearInterval(timer));
  slider.addEventListener('mouseleave', () => { timer = setInterval(() => go(idx + 1), 6500); });
})();
