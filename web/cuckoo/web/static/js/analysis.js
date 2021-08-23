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

  tree.classList.add('process-tree');

  function template(process, meta) {
    return parseDOM(`
      <div class="columns is-divided is-vcenter">
        <div class="column is-auto">
          &nbsp;
        </div>
        <div class="column">
          <p title="${process.image}">
            <span class="icon has-half-opacity" title="Process name">
              <i class="fas fa-tag"></i>
            </span>
            <span class="is-monospace has-margin-right" title="Process identifier">
              <span class="is-uppercase has-half-opacity">process</span>
              <strong>${lib.SafeString(process.procid)}</strong>
              &mdash;
            </span>
            ${lib.SafeString(process.name)}
          </p>
          <p title="Executed command">
            <span class="icon has-half-opacity">
              <i class="fas fa-terminal"></i>
            </span>
            <code class="code">${lib.SafeString(process.commandline)}</code>
          </p>
          <div class="has-margin-y">
            <span class="icon has-half-opacity">
              <i class="fas fa-stopwatch"></i>
            </span>
            <div class="duration" title="Process duration">
              <div class="duration--inner" style="width: ${meta.duration.length}%; left: ${meta.duration.offset}%;"></div>
            </div>
            <span title="Process state">${lib.SafeString(process.state)}</span>
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

  const signatures  = document.querySelector('#signatures');

  if(!signatures) return;

  const table       = signatures.querySelector('.table');
  const filters     = [...signatures.querySelectorAll('[name="toggle-sig"]')];

  function onUnselected() {
    if(!filters.find(f => f.checked))
      filters[0].checked = true;
  }

  signatures.querySelectorAll('.table tbody tr[data-row]').forEach(row => {

    let toggle = row.querySelector('.toggle-ioc');
    if(!toggle) return;

    let oldContent = toggle.textContent;

    row.querySelector('.toggle-ioc').addEventListener('click', ev => {
      ev.preventDefault();
      let link = ev.currentTarget;
      let target = signatures.querySelector('tr[data-row-of="'+row.dataset.row+'"]');

      if(target.hasAttribute('hidden')) {
        target.removeAttribute('hidden');
        link.textContent = "Hide IOC's";
        row.classList.add('is-shown');
      } else {
        target.setAttribute('hidden', true);
        link.textContent = oldContent;
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

// comparison form
(function compareTasksWidget() {

  const compareForm = document.querySelector('form#compare-tasks')
  if(compareForm) {

    const submit = compareForm.querySelector('input[type="submit"]');
    const checkboxes = compareForm.querySelectorAll('input[type="checkbox"]');
    const checked = () => [...checkboxes].filter(checkbox => checkbox.checked);

    compareForm.addEventListener('submit', ev => {
      ev.preventDefault();
      const ids = checked().map(checkbox => checkbox.value);
      window.location = '/compare/' + ids.join('/');
    });

    // limits selectable tasks to max 2
    function checkValidity() {

      if(checked().length == 2) {
        submit.disabled = false;
        checkboxes.forEach(cb => {
          if(cb.checked == false)
            cb.disabled = true;
        })
      } else {
        submit.disabled = true;
        checkboxes.forEach(cb => {
          cb.disabled = false
        });
      }
    }

    checkboxes.forEach(checkbox => {
      checkbox.addEventListener('change', checkValidity)
    });

    // in the case of browser-cached ticked checkboxes, make sure
    // the rules listen to that too.
    setTimeout(checkValidity, 20);

  }

}());

// threat radar chart
(function renderThreatChart() {

  const ctx = document.querySelector('canvas#behavior-map');
  if(!window.Chart || !ctx || !window.data || !window.data.chart) return;
  const { tags, labels, values } = window.data.chart;

  // console.log(tags, labels, values);
  // console.log(labels.map(label => label.trim().replace(/^\w/, c => c.toUpperCase())));

  const opacity = .8;
  const type = 'radar';

  // remove the chart if the data is not sufficient to display anything
  // that matches. Needs review to as if this behavior is wanted like this.
  if(values.indexOf(90) == -1) {
    lib.parent('.box', ctx).remove();
    return;
  } else {
    lib.parent('.box', ctx).removeAttribute('hidden');
  }

  let chart;

  function renderChart() {
    if(chart)
      chart.destroy();
    chart = new Chart(ctx.getContext('2d'), {
      type,
      data: {
        labels: labels.map(label => label.trim().replace(/^\w/, c => c.toUpperCase())),
        datasets: [{
          data: values,
          fill: true,
          backgroundColor: ['rgba(249,93,106, '+opacity+')'],
          pointRadius: 0
        }]
      },
      options: {
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          r: {
            ticks: {
              startAtZero: true,
              min: 0,
              max: 100,
              stepSize: 10,
              display: false
            }
          }
        },
        animation: {
          duration: 0
        },
        hover: {
          animationDuration: 0
        },
        responsive: true,
        maintainAspectRatio: true,
        responsiveAnimationDuration: 0
      }
    });
  }

  // wait for window ready, then render the chart
  document.addEventListener('DOMContentLoaded', renderChart);
  window.addEventListener("resize", renderChart);

}());

// screenshot module
(function screenshots() {

  const elem      = document.querySelector('#screenshot');
  const data      = Application.screenshot;
  const baseURL   = Application.screenshotURL;

  if(!elem || !data.length)
    return;

  const image     = elem.querySelector('.screenshot-image');
  const slider    = elem.querySelector('input[type="range"]');
  const scdetails = elem.querySelector('.screenshot-details');
  let loaded;

  function loadImage(sc, index) {
    let img = new Image();
    img.src = baseURL(sc.name);
    img.onload = function() {
      if(image.querySelector('img'))
        image.querySelector('img').remove();
      image.appendChild(img);
      loaded = sc;

      scdetails.querySelector('[data-screenshot-index]').textContent = index+1 + '/' + data.length;
      scdetails.querySelector('[data-screenshot-name]').textContent = sc.name;
    }
  }

  slider.addEventListener('change', ev => {
    let index = parseInt(ev.target.value)-1;
    let target = data[index];
    loadImage(target, index);
  });

  slider.dispatchEvent(new Event('change'));

  [image, scdetails.querySelector('[data-screenshot-name]')].forEach(e => {
    e.addEventListener('click', ev => {
      window.open(baseURL(loaded.name), "_blank");
    });
  });

}());
