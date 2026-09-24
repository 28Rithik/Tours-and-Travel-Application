(function(){
  function syncUrgencyHeight(){
    const bar = document.querySelector('.gt-urgency-bar');
    if (!bar) return;
    const height = Math.ceil(bar.getBoundingClientRect().height);
    document.documentElement.style.setProperty('--gt-urgency-height', `${height}px`);
  }

  window.toggleGroupTourMenu = function(){
    const menu = document.getElementById('mobileGroupToursMenu');
    const icon = document.getElementById('groupTourMenuIcon');
    if (!menu) return;
    const open = menu.style.display === 'block';
    menu.style.display = open ? 'none' : 'block';
    if (icon) icon.style.transform = open ? 'rotate(0deg)' : 'rotate(180deg)';
  };

  syncUrgencyHeight();
  window.addEventListener('load', syncUrgencyHeight);
  window.addEventListener('resize', syncUrgencyHeight);
  document.fonts?.ready?.then(syncUrgencyHeight);
})();
