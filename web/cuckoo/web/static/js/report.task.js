// map the processes and provide a lookup api
const processes = (function() {

  if(!window.Application || !window.Application.processes) return;

  function findChild(procid) {
    return Application.processes.find(p => p.procid == procid);
  }

  function findParent(pprocid) {
    return Application.processes.find(p => p.procid == pprocid) || false;
  }

  // apply a new property 'children' to all processes, these will be used for
  // storing child references, then hard-find direct children of the process
  // to create a tree structure format.
  const mapped = Application.processes.map(p => {
    // firstly, look up children by their parent processes
    if(!p.children) p.children = [];
    let parent = findParent(p.parent_procid);
    if(parent) {
      parent.children.push(p.procid);
    }
    return p;
  }).map(p => {
    // then, replace the child id's with the actual child keys and flag
    // replaced childs for 'removal' in UI array
    if(p.children.length) {
      p.children = p.children.map(c => {
        let child = findChild(c);
        child.rm = true;
        return child;
      });
    }
    return p;
  }).filter(p => !p.rm);

  return {
    mapped,
    findChild,
    findParent
  };

}());

// renders processes to interactive nodes view
(function renderProcessNodes() {

  const nodes = document.querySelector('#tab-process-nodes');

  if(!nodes)
    return;

  // recursively construct a tree structure containing all information of the
  // children
  const nodesMarkup = parseDOM(`
    <ul class="list is-tree-diagram">
      <li>
        <span class="leading-node">...</span>
        <ul></ul>
      </li>
    </ul>`);

  function recurse(a=[], dom) {
    a.forEach(p => {

      let html  = document.createElement('li');
      let label = document.createElement('span');
      label.setAttribute('data-procid', p.procid);
      label.textContent = p.name;
      html.appendChild(label);
      html.appendChild(document.createElement('ul'));
      dom.appendChild(html);

      if(p.children.length) {
        recurse(p.children, dom.querySelector('ul'));
      }

    });
  }
  recurse(processes.mapped, nodesMarkup.querySelector('ul'));
  nodes.appendChild(nodesMarkup);

  // add an interactive pane switcher that allows a click-through inspection
  // tool
  let panel;
  function displayProcessInformation(ev) {

    const id      = ev.currentTarget.dataset.procid;
    const proc    = processes.findChild(id);

    if(panel)
      panel.remove();

    if(proc) {
      panel = parseDOM(`
        <div class="box has-background-light has-padding">
          <h4></h4>
        </div>
      `);
      nodes.insertBefore(panel, nodesMarkup.nextSibling);
    }

  }
  nodesMarkup.querySelectorAll('span').forEach(s => s.addEventListener('click', displayProcessInformation));

}());

// renders processes to indented tree view
(function renderProcessTree() {

  const processTreeTab  = document.querySelector('#tab-process-tree');

  if(!processTreeTab) return;

  const { mapped }      = processes;
  const tree            = document.createElement('ul');

  tree.classList.add('list');
  tree.classList.add('process-tree');

  function template(process, meta) {
    return parseDOM(`
      <div class="columns is-divided is-vcenter">
        <div class="column is-auto">
          &nbsp;
        </div>
        <div class="column">
          <p title="${process.image}">
            <span class="icon has-half-opacity">
              <i class="fas fa-tag"></i>
            </span>
            <span class="tag">${process.procid}</span>
            ${process.name}
          </p>
          <p>
            <span class="icon has-half-opacity">
              <i class="fas fa-terminal"></i>
            </span>
            <code class="code">${process.commandline}</code>
          </p>
          <div class="has-margin-y">
            <span class="icon has-half-opacity">
              <i class="fas fa-stopwatch"></i>
            </span>
            <div class="duration">
              <div class="duration--inner" style="width: ${meta.duration.length}%; left: ${meta.duration.offset}%;"></div>
            </div>
            ${process.state}
          </div>
        </div>
        ${(process.children.length > 0) ? `
          <div class="column is-auto">
            <span class="icon">
              <i class="fas caret"></i>
            </span>
          </div>
        ` : ''}
      </div>
    `);
  }

  function getDuration(process) {
    let dur = Application.duration;
    let start = process.start_ts;
    let end   = process.end_ts || Application.duration;
    return {
      length: ((end - start) / dur) * 100,
      offset: (start / dur) * 100
    }
  }

  function recurse(a=[], dom, it=0) {
    a.forEach((p, i) => {

      let id = 'process-'+p.pid;
      let item = document.createElement('li');

      let content = template(p, {
        duration: getDuration(p)
      });

      // enable tooltips
      // content.querySelectorAll('[data-tooltip]').forEach(handleTooltip);

      if(p.children.length) {

        let cb    = document.createElement('input');
        let label = document.createElement('label');
        let list  = document.createElement('ul');

        cb.classList.add('list-collapse');
        cb.setAttribute('type', 'checkbox');
        cb.setAttribute('checked', true);
        cb.setAttribute('id', id);
        label.setAttribute('for', id);

        item.appendChild(cb);
        item.appendChild(label);
        label.appendChild(content);
        item.appendChild(list);

        recurse(p.children, list);
      } else {
        item.appendChild(content);
      }
      dom.appendChild(item);
    });
  }
  recurse(mapped, tree);

  processTreeTab.appendChild(tree);
}());

// tap through various levels of signature severities
(function signatureFilters() {

  const signatures  = document.querySelector('#box-Signatures');
  const table       = signatures.querySelector('.table');
  const filters     = [...signatures.querySelectorAll('[name="toggle-sig"]')];

  function onUnselected() {
    if(!filters.find(f => f.checked))
      filters[0].checked = true;
  }

  signatures.querySelectorAll('.table tbody tr[data-row]').forEach(row => {
    row.querySelector('.toggle-ioc').addEventListener('click', ev => {
      ev.preventDefault();
      let link = ev.currentTarget;
      let target = signatures.querySelector('tr[data-row-of="'+row.dataset.row+'"]');

      if(target.hasAttribute('hidden')) {
        target.removeAttribute('hidden');
        link.textContent = 'Hide IOCs';
        row.classList.add('is-shown');
      } else {
        target.setAttribute('hidden', true);
        link.textContent = 'Display IOCs';
        row.classList.remove('is-shown');
      }

    });
  });

  filters.forEach(filter => {
    filter.addEventListener('change', ev => {
      switch(ev.currentTarget.value) {
        case 'all':
          filters.forEach(f => f.value !== 'all' ? f.checked = false : null);
        break;
        default:
          filters.find(f => f.value == 'all').checked = false;
      }
      onUnselected();
    });
  });

}());
