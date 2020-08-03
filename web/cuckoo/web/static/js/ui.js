// Copyright (C) 2016-2020 Cuckoo Foundation.
// This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
// See the file 'docs/LICENSE' for copying permission.

const lib = {
  // splits url in its counterparts
  url(url) {
    return url.split('/');
  },
  // returns a parent of a child node matching a certain class name
  // ex: lib.parent('parent', document.querySelector('.test'))
  parent(sel, ref) {
    if((!ref instanceof HTMLElement) || (!sel instanceof String)) return null;
    let node = ref;
    let result;
    while(node.tagName.toLowerCase() !== 'body') {
      if(node.classList.contains(sel)) {
        result = node;
        break;
      }
      node = node.parentNode;
    }
    return result;
  }
}
/**
 * handles navbar interaction (small-screen exclusive enhancement)
 * @param {HTMLElement} toggle - element target
 * @param {number} index - iteration index number
 * @return null;
 */
function handleNavbar(toggle) {
  let n = lib.parent('navbar', toggle);
  if(!n) return;
  toggle.addEventListener("click", ev => {
    ev.preventDefault();
    n.classList.toggle("is-expanded");
    n.setAttribute("aria-expanded", n.classList.contains("is-expanded"));
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
  const { url } = lib;
  input.addEventListener("change", ev => {
    if(previousElementSibling) {
      const file = input.files[0];
      if(file instanceof File) {
        previousElementSibling.textContent = file.name;
        previousElementSibling.classList.add("is-disabled");
        previousElementSibling.classList.remove("is-blue");
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
 * Initializes in-page tab behavior. Clicking tab links will hide or show the
 * referenced elements
 * @param {HTMLElement} tabContext
 */
function handlePageTabs(tabContext) {

  const links = [...tabContext.querySelectorAll('.tabbar-link')];
  const refs = links.map(link => document.querySelector(link.getAttribute('href')));

  // hides all the referenced tabs before displaying the new one
  function hideAllRelatedTabs() {
    links.forEach(link => link.classList.remove('is-active'));
    refs.forEach(ref => ref.setAttribute('hidden', true));
  }

  links.forEach(link => {
    link.addEventListener('click', ev => {
      ev.preventDefault();
      const href = ev.currentTarget.getAttribute('href');
      const target = document.querySelector(href);
      if(target) {
        hideAllRelatedTabs();
        target.removeAttribute('hidden');
        link.classList.add('is-active');
      }
    })
  })
}
/**
 * Toggles [hidden] attribute on html element. Can be called inline for simplicity
 * of performing this routine.
 * @param {HTMLElement|String} element - target element to toggle, if this is a
 *                                       string, it will querySelector to an element.
 * @param {Boolean} force              - optional, if set it will force the state
 *                                       of the visibility.
 * @example
 * <button onclick="toggleVisibility('#element', true)">
 */
function toggleVisibility(element, force=null) {
  if(typeof element == 'string')
    element = document.querySelector(element);
  if(!element) return;
  if(force !== null && force instanceof Boolean)
    element.toggleAttribute('');
  else
    element.toggleAttribute('hidden');
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
document.addEventListener("DOMContentLoaded", () => {
  applyHandler(".navbar .navbar-toggle", handleNavbar);
  applyHandler(".input[type='file'][data-enhance]", handleFileInput);
  applyHandler(".list.is-tree[data-enhance]", handleListTree);
  applyHandler(".tabbar[data-enhance]", handlePageTabs);
});
