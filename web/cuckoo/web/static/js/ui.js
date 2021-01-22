// Copyright (C) 2016-2020 Cuckoo Foundation.
// This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
// See the file 'docs/LICENSE' for copying permission.
window.lib = Object.assign(window.lib || {}, {
  // splits url in its counterparts
  url(url) {
    return url.split('/').filter(p => p.length > 0);
  },
  // returns a parent of a child node matching a certain property
  // ex: lib.parent('parent', document.querySelector('.test'))
  // when sel(ector) starts with a '.', a match is looked up by class name
  // when sel(ector) starts with a '#', a match is looked up by its id
  // by default, it will try to match a node name (e.g <p>, <li>, etc.)
  parent(sel, ref) {
    if((!ref instanceof HTMLElement) || (!sel instanceof String)) return null;
    let node = ref;
    let result;
    while(node.tagName.toLowerCase() !== 'body') {
      if(sel[0] == '.') {
        // search in class name if first char is '.'
        if(node.classList.contains(sel.replace('.',''))) {
          result = node;
          break;
        }
      } else if(sel[0] == '#') {
        // search in id if first char is '#'
        if(node.id == sel) {
          result = node;
          break;
        }
      } else {
        // by default, search for a matching node name
        if(node.tagName.toLowerCase() == sel) {
          result = node;
          break;
        }
      }
      node = node.parentNode;
    }
    return result;
  },
  // generates a banner element with a type + text
  banner(content="", type) {
    let icon;
    switch(type) {
      case 'info':
        icon = 'fas fa-info';
      break;
      case 'danger':
        icon = 'fas fa-exclamation';
      break;
      default:
        icon = 'fas fa-comment';
    }
    return parseDOM(`
      <div class="banner is-${type}">
        <div class="banner-icon"><i class="${icon}"></i></div>
        <p class="column no-margin-y">${content}</p>
      </div>
    `);
  }
});

/**
 * Parses a string to DOM object to be injected into the page.
 * @param {string} str - HTML as a string
 * @param {string} type - DOM format, should be 'text/html' or 'text/svg'
 * @return {HTMLElement}
 */
function parseDOM(str='', type='text/html') {
  return new DOMParser().parseFromString(str, type).body.firstChild;
}

/**
 * handles navbar interaction (small-screen exclusive enhancement)
 * @param {HTMLElement} toggle - element target
 * @param {number} index - iteration index number
 * @return null;
 */
function handleNavbar(toggle) {
  let n = lib.parent('.navbar', toggle);
  if(!n) return;
  toggle.addEventListener('click', ev => {
    ev.preventDefault();
    n.classList.toggle('is-expanded');
    n.setAttribute('aria-expanded', n.classList.contains('is-expanded'));
  });
  return null;
}

/**
 * enhances default file input experience
 * @param {HTMLElement} input - element target
 * @param {number} index - iteration index number
 * @return {null}
 */
function handleFileInput(input) {
  const { previousElementSibling } = input;
  input.addEventListener('change', ev => {
    if(previousElementSibling) {
      const file = input.files[0];
      if(file instanceof File) {
        previousElementSibling.textContent = file.name;
        previousElementSibling.classList.add('is-disabled');
        previousElementSibling.classList.remove('is-blue');
      }
    }
  });
  // @TODO: handle multiple files
  return null;
}

/**
 * Enhances list-tree variations.
 * @param {HTMLElement} list - list target
 */
function handleListTree(list) {
  // make sure that 'checked' list tree items are visible inside the tree
  [...list.querySelectorAll('input:checked')].forEach(input => {
    let node = input.parentNode;
    while(node !== list) {
      if(node.tagName.toLowerCase() == 'li') {
        const handle = [...node.children].find(n => {
          return (
            n.tagName.toLowerCase() == 'input'
            && n.type == 'checkbox'
            && !n.hasAttribute('value')
          );
        });
        if(handle) handle.checked = true;
      }
      node = node.parentNode;
    }
  });
}

/**
 * Enhances in-page tab behavior. Clicking tab links will hide or show the
 * referenced elements
 * @param {HTMLElement} tabContext
 *
 * if tabContext is an element containing the class '.tabbar', it initializes
 * all tabbar-links within the bar.
 * if tabContext is an element containing the class '.tabbar-link', it will hook
 * that link to the target tab context - if the appropriate ID has been set
 * explicitly for the target tabs.
 */
function handlePageTabs(tabContext) {

  let tabbar;
  if(tabContext.classList.contains('tabbar')) {
    tabbar = tabContext;
  } else if(tabContext.classList.contains('tabbar-link')) {
    tabbar = document.querySelector(tabContext.dataset.tabbar);
  }

  let links = [
    ...tabContext.querySelectorAll('.tabbar-link'),
    ...document.querySelectorAll('[data-tabbar="#'+tabbar.getAttribute('id')+'"]')
  ];

  // hides all the referenced tabs before displaying the new one
  function hideAllRelatedTabs() {
    links.forEach(link => link.classList.remove('is-active'));
    let refs = links.map(link => document.querySelector(link.getAttribute('href')));
    refs.forEach(ref => {
      if(ref)
        ref.setAttribute('hidden', true);
    });
  }

  links.forEach(link => {
    link.addEventListener('click', ev => {
      ev.preventDefault();
      const href = ev.currentTarget.getAttribute('href');
      const target = document.querySelector(href);
      if(target) {
        hideAllRelatedTabs(tabContext);
        target.removeAttribute('hidden');
        link.classList.add('is-active');
      }
    })
  });

}

/**
 * Toggles [hidden] attribute on html element. Can be called inline for simplicity
 * of performing this routine.
 * @param {HTMLElement|String} element - target element to toggle, if this is a
 *                                       string, it will querySelector to an element.
 * @param {Boolean} force              - optional, if set it will force the state
 *                                       of the visibility.
 * @param {Undefined} event            - optional, if set it will escape the default
 *                                       event behavior (e.g onclick-like events)
 * @example
 * <button onclick="toggleVisibility('#element', true)">
 */
function toggleVisibility(element, force=null, event) {

  if(event instanceof Event)
    event.preventDefault();

  if(typeof element == 'string')
    element = document.querySelector(element);
  if(!element) return;
  if(force !== null && force instanceof Boolean)
    element.toggleAttribute('hidden', force);
  else
    element.toggleAttribute('hidden');

  // approach 1: if the dispatcher sent an event, take the target of the event
  // to indicate said toggleable visibility for appropriate style changes.
  if(event) {
    if(element.getAttribute('hidden') === null) {
      event.currentTarget.classList.remove('visibility-hidden');
      event.currentTarget.classList.add('visibility-visible');
    } else {
      event.currentTarget.classList.remove('visibility-visible');
      event.currentTarget.classList.add('visibility-hidden');
    }
  }

}

/**
 * Lets an element blink for a moment to indicate a change caused by another
 * action.
 * @param {HTMLElement} el - the element to apply the effect on
 * @param {String} blinkColor - a HEX value of the color that the element blinks into
 * @param {Number} speed - the speed in milliseconds of the blink animation
 */
function blink(el, blinkColor = '#fffae8', speed = 75) {
  const background = getComputedStyle(el).getPropertyValue('background-color');
  el.style.transition = `background-color ${speed}ms linear`;
  let mode = 1;
  let step = 0;
  const iv = setInterval(() => {
    if(mode)
      el.style.backgroundColor = blinkColor;
    else
      el.style.backgroundColor = background;
    mode = mode ? 0 : 1;
    step++;
    if(step == 4) {
      clearInterval(iv);
      el.style.transition = null;
      el.style.backgroundColor = background;
    }
  }, speed * 2);
}

/**
 * Toggles all <details> elements on or off
 * @param {Boolean} force - force toggle into a state (true=open/false=closed)
 * @param {HTMLElement} context - look for details inside this context
 * @return {Boolean}
 */
function toggleDetails(force=null, context=document, ev) {

  // escape default event cycle
  if(ev instanceof Event)
    ev.preventDefault();

  const details = context.querySelectorAll('details');
  if(details.length) {
    [...details].forEach(d => {
      if(force === true) {
        return d.setAttribute('open', true);
      } else if(force === false) {
        return d.removeAttribute('open');
      } else {
        if(d.hasAttribute('open')) {
          d.removeAttribute('open');
        } else {
          d.setAttribute('open', true);
        }
      }
    });
  }
}

/**
 * Creates a popover that will toggle on click
 * @param {HTMLElement} trigger - the button that holds the popover
 */
function handlePopover(trigger) {

  const elem  = document.querySelector('.popover' + trigger.getAttribute('data-popover'));
  const close = elem.querySelector('[data-popover-close]');

  function onBodyClick(e) {
    const inPopover = !(lib.parent('.popover', e.target));
    if(inPopover) {
      elem.classList.remove('in');
      document.body.removeEventListener('click', onBodyClick);
    }
  }

  trigger.addEventListener('click', ev => {
    ev.preventDefault();
    elem.classList.toggle('in');
    // register body click
    setTimeout(() => document.body.addEventListener('click', onBodyClick), 100);
  });

  if(close)
    close.addEventListener('click', ev => {
      ev.preventDefault();
      document.body.click();
    });

}

/*
 * Creates a tooltip
 */
function handleTooltip(elem) {

  let tip;
  const text = (elem.getAttribute('title') || elem.getAttribute('data-tooltip'));

  const removeTip = t => setTimeout(() => {
    t.classList.remove('in');
  }, 100);

  elem.classList.add('has-tooltip');

  if(elem.getAttribute('title')) {
    elem.dataset.title = elem.getAttribute('title');
    elem.removeAttribute('title');
  }

  elem.addEventListener('mouseenter', ev => {
    ev.stopPropagation();
    tip = parseDOM(`<span class="tooltip is-bottom">${text}</span>`);
    elem.appendChild(tip);
    setTimeout(() => {
      tip.classList.add('in');
    }, 10);
  }, false);

  elem.addEventListener('mouseout', ev => {
    removeTip(tip);
  });

}

/**
 * Makes a certain password field reveal on demand
 * @param {HTMLElement} input - the password field to toggle
 * @return {null}
 * @note Requires an already existing addon/button element within the control
 *       group that has 'data-toggle' assigned. An additional [data-hide] and
 *       [data-hidden] are toggled to use different icons for the states.
 */
function handlePasswordHide(input) {
  const control   = lib.parent('.control', input);
  const button    = control.querySelector('[data-toggle]');
  const revealed  = control.querySelector('[data-revealed]');
  const hidden    = control.querySelector('[data-hide]');

  function getState() {
    return input.getAttribute('type') == 'password' ? false : true;
  }

  let isRevealed = getState();

  function toggleButton() {
    if(isRevealed === false) {
      hidden.removeAttribute('hidden');
      revealed.setAttribute('hidden', true);
    } else {
      hidden.setAttribute('hidden', true);
      revealed.removeAttribute('hidden');
    }
  }

  if(button) {
    button.addEventListener('click', ev => {
      ev.preventDefault();

      if(isRevealed) {
        input.setAttribute('type', 'password');
      } else {
        input.setAttribute('type', 'text');
      }

      isRevealed = getState();
      toggleButton();
    });
  }

  toggleButton(isRevealed);

}

/**
 * This enables interactions on tag lists such as; 'type-to-tag'
 * @param * @param {HTMLElement} tagList - the password field to toggle
 * @return {null}
 */
function handleTagInput(tagList) {

  const tagValue   = tagList.querySelector('input[data-tag-value]');
  const addTag     = tagList.querySelector('button[data-add-tag]');
  let tagStore     = tagList.querySelector('input[data-tags]');
  const tags       = tagStore.value.length > 0 ? tagStore.value.split(',') : [];

  function commit(str) {
    if(str)
      tags.push(str);
    tagStore.value = tags.join(',');
    tagStore.dispatchEvent(new Event('change'));
  }

  function createTagStore() {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.setAttribute('data-tags', true);
    tagList.appendChild(input);
    tagStore = input;
  }

  function createTag(str, store=true) {
    const tag = document.createElement(`div`);
    tag.classList.add('tag');
    tag.textContent = str;
    tagList.insertBefore(tag, lib.parent('.control', addTag));
    // append removal 'x'
    const closeTag = document.createElement('a');
    const closeIcon = document.createElement('i');
    closeIcon.classList.add('fas');
    closeIcon.classList.add('fa-times');
    closeTag.appendChild(closeIcon);
    closeTag.classList.add('tag-remove');
    tag.appendChild(closeTag);
    closeTag.addEventListener('click', () => removeTag(tag));
    if(store) {
      blink(tag);
      commit(str);
    }
  }

  function removeTag(tag) {
    if(!tag) {
      tagList.querySelectorAll('.tag').forEach(t => removeTag(t));
    } else {
      let index = tags.indexOf(tag.textContent);
      if(index !== -1) {
        tags.splice(index, 1);
      }
      tag.parentNode.removeChild(tag);
      commit();
    }
  }

  tagList.querySelectorAll('.tag .tag-remove').forEach(rm => {
    rm.addEventListener('click', () => removeTag(lib.parent('.tag', rm)));
  });

  tagValue.addEventListener('keydown', e => {
    switch(e.keyCode) {
      case 13:
        addTag.dispatchEvent(new Event('click'));
      break;
    }
  });

  addTag.addEventListener('click', () => {
    if(tagValue.value.length) {
      createTag(tagValue.value);
      tagValue.value = "";
      tagValue.focus();
    }
  });

  if(tags.length) {
    tags.forEach(tag => {
      if(tag.length)
        createTag(tag, false);
    });
  }

  if(!tagStore)
    createTagStore();

 }

/**
 * multi-applier for handlers on DOMNodeList selectors
 * @param {string} sel - querySelector string
 * @param {function} fn - iterator function (Array.forEach callback)
 * @return {null}
 */
function applyHandler(sel=null, fn=null) {
  if(sel && fn) [...document.querySelectorAll(sel)].forEach(fn);
  return null;
}

/**
 * document ready state initializer
 */
document.addEventListener('DOMContentLoaded', () => {
  applyHandler('.navbar .navbar-toggle', handleNavbar);
  applyHandler('.input[type="file"][data-enhance]', handleFileInput);
  applyHandler('.input[type="password"][data-enhance]', handlePasswordHide);
  applyHandler('.list.is-tree[data-enhance]', handleListTree);
  applyHandler('.tabbar[data-enhance]', handlePageTabs);
  applyHandler('.tag-list[data-enhance]', handleTagInput);
  applyHandler('[data-popover]', handlePopover);
  applyHandler('[data-tooltip]', handleTooltip);
});
