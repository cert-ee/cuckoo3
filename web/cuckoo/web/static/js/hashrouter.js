/*
 * hash-based inline navigation 1.0
 *
 * This script utilizes HTML5 'role' attributes to determine its contribution
 * to inline navigation methods. Using that, and a format that works for
 * single-level tabs as well as multi-dimensional deep tabs.
 *
 *
 * <div role="tablist" id="tabs-index">
 *   <a role="tab" href="#test"></a>
 *   <a role="tab" href="#test-two"></a>
 * </div>
 * <div role="region" id="test">Test</div>
 * <div role="region" id="test-two" hidden>
 *   <div role="tablist" id="tabs-index">
 *     <a role="tab" href="#test:test-three"></a>
 *     <a role="tab" href="#test:test-four"></a>
 *   </div>
 *   <div role="region" id="test:test-three"></div>
 *   <div role="region" id="test:test-four"></div>
 * </div>
 *
 * @NOTE: uses WAI-ARIA attributes/roles as indicator for each tab element, no
 * fixation on class names or id's.
 */

(function() {

  window.hashRouted  = false;
  let _tabs          = [...document.querySelectorAll('[role="tab"]')];
  let _tabpages      = [...document.querySelectorAll('[role="region"]')];

  // _tabs.forEach(tab => tab.addEventListener('click', e => e.preventDefault()));

  function parseHash(url) {
    return url.replace('#', '').split(':');
  }

  /**
   * Whenever the URL changes after a client action (eg a href to a #domain),
   * this function gets called to 're-hide/show' parts of the UI that are
   * connected to it. Currently automatically will pick up on existing 'tabs'
   */
  function onURLChanged(evt) {

    let url = (evt.newUrl ? substring(evt.newUrl.indexOf('#'), evt.newUrl.length) : false) || window.location.hash;
    if(!url.length) {
      window.hashRouted = false;
      return;
    };

    // clean the current state of the ui
    _tabs.forEach(tab => tab.classList.remove('is-active'));
    _tabpages.forEach(page => page.setAttribute('hidden', true));

    // propagate hashed view state
    let hash = parseHash(url);

    hash.forEach((part, i) => {
      let id = hash.slice(0, i+1).join(':');
      let el = document.querySelector('[id="'+id+'"]');
      let links = document.querySelectorAll('[role="tab"][href="#'+id+'"]');
      links.forEach(link => link.classList.add('is-active'));
      if(el && el.getAttribute('role') == 'region')
        el.removeAttribute('hidden');
    });

    window.hashRouted = true;

  }

  window.addEventListener('hashchange', onURLChanged);
  window.dispatchEvent(new HashChangeEvent("hashchange"));

  /**
   * Jumps to a hash from the global scope
   *
   * @param {String} hash - the target hash to jump to
   * @example
   *
   *    const { gotoHash } = window;
   *    gotoHash('#tab:nested-tab')
   */
  window.gotoHash = function(hash) {
    if(hash) window.location.hash = hash;
    return;
  }

}());
