(function(){
  function qsa(sel, root){ return Array.prototype.slice.call((root||document).querySelectorAll(sel)); }
  function closest(el, sel){ while(el && el!==document){ if(el.matches && el.matches(sel)) return el; el=el.parentElement; } return null; }

  var overlay, imgEl, captionEl, btnClose, btnPrev, btnNext;
  var groupLinks = []; var currentIndex = 0;

  function ensureOverlay(){
    if(overlay) return;
    overlay = document.createElement('div');
    overlay.className = 'slb-overlay';
    overlay.innerHTML =
      '<div class="slb-content" role="dialog" aria-modal="true" aria-label="Image viewer">'+
        '<div class="slb-img-wrap">'+
          '<button type="button" class="slb-btn slb-prev" aria-label="Previous">‹</button>'+
          '<img class="slb-img" alt="">'+
          '<button type="button" class="slb-btn slb-next" aria-label="Next">›</button>'+
          '<button type="button" class="slb-btn slb-close" aria-label="Close">×</button>'+
        '</div>'+
        '<div class="slb-caption"></div>'+
      '</div>';
    document.body.appendChild(overlay);
    imgEl = overlay.querySelector('.slb-img');
    captionEl = overlay.querySelector('.slb-caption');
    btnClose = overlay.querySelector('.slb-close');
    btnPrev = overlay.querySelector('.slb-prev');
    btnNext = overlay.querySelector('.slb-next');

    overlay.addEventListener('click', function(e){ if(e.target === overlay) close(); });
    btnClose.addEventListener('click', close);
    btnPrev.addEventListener('click', function(){ nav(-1); });
    btnNext.addEventListener('click', function(){ nav(1); });

    document.addEventListener('keydown', function(e){
      if(!overlay.classList.contains('is-open')) return;
      if(e.key === 'Escape') close();
      if(e.key === 'ArrowLeft') nav(-1);
      if(e.key === 'ArrowRight') nav(1);
    });
  }

  function openAt(index){
    ensureOverlay();
    currentIndex = index;
    var a = groupLinks[currentIndex];
    var href = a.getAttribute('href');
    var title = a.getAttribute('data-lightbox-title') || a.getAttribute('data-title') || a.getAttribute('title') || '';
    imgEl.src = href;
    captionEl.textContent = title;

    var many = groupLinks.length > 1;
    btnPrev.style.display = many ? '' : 'none';
    btnNext.style.display = many ? '' : 'none';

    overlay.classList.add('is-open');
    document.documentElement.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';
    btnClose.focus();
  }

  function close(){
    if(!overlay) return;
    overlay.classList.remove('is-open');
    imgEl.src = '';
    document.documentElement.style.overflow = '';
    document.body.style.overflow = '';
  }

  function nav(dir){
    if(groupLinks.length <= 1) return;
    currentIndex = (currentIndex + dir + groupLinks.length) % groupLinks.length;
    openAt(currentIndex);
  }

  function handleClick(e){
    var a = closest(e.target, 'a[data-lightbox-group], a[data-lightbox]');
    if(!a) return;
    var group = a.getAttribute('data-lightbox-group') || a.getAttribute('data-lightbox') || 'default';

    // CSS.escape may not exist on older browsers
    var esc = (window.CSS && CSS.escape) ? CSS.escape(group) : group.replace(/"/g,'\\"');

    groupLinks = qsa('a[data-lightbox-group="'+esc+'"], a[data-lightbox="'+esc+'"]');
    if(!groupLinks.length){
      groupLinks = qsa('a[data-lightbox-group], a[data-lightbox]').filter(function(x){
        return (x.getAttribute('data-lightbox-group')||x.getAttribute('data-lightbox')) === group;
      });
    }

    var idx = groupLinks.indexOf(a);
    if(idx < 0) idx = 0;
    e.preventDefault();
    openAt(idx);
  }

  document.addEventListener('click', handleClick, true);
})();
