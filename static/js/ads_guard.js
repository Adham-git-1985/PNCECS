// ads_guard.js — keeps the right padding and sticky top in sync with real sizes
// - Measures header height and ads sidebar width live (supports browser zoom)
// - Updates CSS variables: --header-h and --ads-w

(function(){
  function $(sel, root){ return (root||document).querySelector(sel); }
  const rootStyle = document.documentElement.style;
  const header = $('header.fixed-top') || $('header');
  const ads = $('.announcements-vertical');
  const content = $('.content-wrapper');

  function setVar(name, px){
    rootStyle.setProperty(name, Math.max(0, Math.round(px)) + 'px');
  }

  function measure(){
    if(header){ setVar('--header-h', header.offsetHeight || 0); }
    if(ads && getComputedStyle(ads).position === 'fixed'){
      // measure real width including borders/padding
      const rect = ads.getBoundingClientRect();
      // if hidden or zero-width, reserve 0
      setVar('--ads-w', rect.width || 0);
    } else {
      setVar('--ads-w', 0);
    }
  }

  // Initial measure
  document.addEventListener('DOMContentLoaded', measure);

  // Re-measure on resize (fires on zoom in most browsers)
  window.addEventListener('resize', measure);

  // Observe header size changes (wraps on zoom)
  if('ResizeObserver' in window && header){
    new ResizeObserver(measure).observe(header);
  }
  // Observe ads size changes too
  if('ResizeObserver' in window && ads){
    new ResizeObserver(measure).observe(ads);
  }

  // Also re-check after images load (carousel images affecting layout)
  window.addEventListener('load', measure);
})();