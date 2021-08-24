(function() {

  const conclude = document.querySelector('#conclude-analysis');
  const finish = conclude.querySelector('#start-analysis');

  // prints error in the conclusive block
  function handleError(msg) {
    const err = conclude.querySelector('#error');
    if(err) err.remove();

    const html = parseDOM(`
      <div class="box has-background-red no-margin-top" id="error">
        <p class="no-margin-top"><strong>${lib.SafeString(msg)}</strong></p>
        <button class="button is-red has-text-small">Dismiss</button>
      </div>
    `);

    conclude.insertBefore(html, conclude.children[0]);
    html.querySelector('button').onclick = () => html.remove();
  }

  // binds ux handlers to the file tree
  function fileTreeHandler() {
    const filetree       = document.querySelector('#filetree');
    const toggleDisabled = document.querySelector('#toggle-disabled');
    const count          = document.querySelector('#count');

    let countHidden   = () => filetree.querySelectorAll('input[data-uninteresting]').length;
    let setCount      = () => count.querySelector('span').textContent = countHidden();

    if(filetree && toggleDisabled) {
      toggleDisabled.addEventListener('click', ev => {
        let isHidden = false;
        let f = [...filetree.querySelectorAll('input[data-uninteresting]')].forEach(s => {
          let item = lib.parent('li', s);
          toggleVisibility(item, !!s.hidden);
          isHidden = item.hidden;
          if(!isHidden) blink(item);
        });
        toggleVisibility(count, !!isHidden);
      });
      setCount();
    }
  }

  // when an OS is picked in the OS dropdown, display only the supported version
  // in the version dropdown
  function platformHandler() {

    const platforms     = document.querySelector('select[name="platform"]');
    const versions      = document.querySelector('select[name="version"]');
    const addPlatform   = document.querySelector('#add-platform');
    const machinery     = document.querySelector('#machinery');
    const totalMachines = document.querySelector('#total-machines');
    let banner;

    // display available versions for selected platform
    platforms.addEventListener('change', ev => {
      const val = ev.currentTarget.value;
      versions.querySelectorAll('option[data-platform]').forEach(o => o.setAttribute('hidden', true));
      if(val.length) {
        versions.querySelectorAll('option[data-platform]').forEach(o => o.removeAttribute('selected'));
        versions.querySelectorAll('option[data-platform='+val+']').forEach(o => o.removeAttribute('hidden'));
        const opts = versions.querySelectorAll('option[data-platform='+val+']');
        if(opts.length) {
          opts[0].selected = true;
        }
        blink(versions);
      }
    });

    function countMachines() {
      const count = machinery.querySelectorAll('[data-machine]').length;
      totalMachines.textContent = count;
      blink(totalMachines);

      if(count > 0) {
        if(banner)
          banner.remove();
        finish.removeAttribute('disabled');
      } else {
        banner = lib.banner('No machines selected.', 'info');
        machinery.appendChild(banner);
        finish.setAttribute('disabled', true);
      }
    }

    // handle machines being added to the list
    function addMachine(data={}) {

      data = Object.assign({
        platform: null,
        version: null
      }, data);

      // @TODO make network routing, browser and command also configurable per machine
      // network: data-route-type, data-route-country-field, data-route-country
      const machine = parseDOM(`
        <div class="box has-border has-background-white no-padding" data-machine data-platform="${lib.SafeString(data.platform)}" data-version="${lib.SafeString(data.version)}">
          <div class="columns is-divided is-gapless">
            <div class="column has-padding-x">
              <p>
                <strong>${lib.SafeString(data.platform)}</strong> ${lib.SafeString(data.version)}
              </p>
              <div class="field is-inline has-padding-x no-margin-top">
                <label class="label"><i class="fas fa-tags"></i></label>
                <div class="control is-tags tag-list">
                  <div class="tag control has-addon no-padding-right">
                    <div class="addon is-left has-half-opacity"><i class="fas fa-tag"></i></div>
                    <input class="input is-small no-shadow" type="text" placeholder="New tag" data-tag-value />
                    <button type="button" class="addon is-right button is-dark is-small no-radius-right" data-add-tag>
                      <i class="fas fa-plus"></i>
                    </button>
                  </div>
                  <input type="hidden" data-tags />
                </div>
              </div>

              <div class="field" data-network-routing>
                <label class="label is-link has-no-underline" onclick="toggleVisibility(this.parentNode.querySelector('[data-toggle-network]'), null, event);">
                  <span class="icon is-caret">
                    <i class="fas fa-caret-right"></i>
                  </span>
                  Network routing
                </label>
                <div data-toggle-network hidden>
                  <div class="control is-select">
                    <select class="input" data-route-type>
                      <option value="" selected>Default</option>
                      <option value="drop">Drop</option>
                      <option value="internet">Internet</option>
                      <option value="vpn">VPN</option>
                    </select>
                  </div>
                  <div class="field is-inline no-padding-y no-padding-right no-margin-top" data-route-country-field hidden>
                    <label class="label">Country</label>
                    <div class="control is-select">
                      <select class="input" data-route-country>
                        <option>First available</option>
                        <optgroup label="Available countries">
                          <option value="fr">France</option>
                          <option value="de">Germany</option>
                          <option value="nl">Netherlands</option>
                          <option value="ee">Estonia</option>
                        </optgroup>
                      </select>
                    </div>
                  </div>
                </div>
              </div>

              <div class="field">
                <label class="label is-link has-no-underline" onclick="toggleVisibility(this.parentNode.querySelector('.control'), null, event)">
                  <span class="icon is-caret">
                    <i class="fas fa-caret-right"></i>
                  </span> Browser
                </label>
                <div class="control is-select" hidden>
                  <select class="input" data-browser>
                    <option value="default">Default</option>
                    <option value="ie">Internet Explorer</option>
                    <option value="firefox">Firefox</option>
                    <option value="chrome">Chrome</option>
                  </select>
                </div>
              </div>

              <div class="field">
                <label class="label is-link has-no-underline" onclick="toggleVisibility(this.parentNode.querySelector('.control'), null, event)">
                  <span class="icon is-caret">
                    <i class="fas fa-caret-right"></i>
                  </span> Launch commands
                </label>
                <div class="control" hidden>
                  <input class="input" type="text" id="command" data-command />
                </div>
              </div>

              <p class="has-text-small has-half-opacity">
                <span class="icon">
                  <i class="fas fa-info-circle"></i>
                </span>
                If set, these options override the default options as set in the options/advanced section for this machine setup.
              </p>

            </div>
            <button type="button" class="column is-auto button has-hover-red no-radius-left" data-delete-machine>
              <i class="fas fa-times"></i>
            </button>
          </div>
        </div>
      `);

      // if more machines exist, append it before the first one in the list
      if(machinery.querySelector('[data-machine]'))
        machinery.insertBefore(machine, machinery.querySelector('[data-machine]'));
      else
        machinery.appendChild(machine);

      handleTagInput(machine.querySelector('.tag-list'));
      routingHandler(machine.querySelector('[data-network-routing]'));

      // blink the created item
      blink(machine);

      // remove the machine from the list by clicking
      machine.querySelector('[data-delete-machine]').addEventListener('click', () => {
        machine.remove();
        countMachines();
      });

      countMachines();

    }

    addPlatform.addEventListener('click', () => {
      let platform = platforms.value;
      let version = versions.value;
      addMachine({platform, version});
    });

    // display the correct versions for the initialized platforms
    platforms.dispatchEvent(new Event('change'));

    // run count once to initialize the state
    countMachines();

  }

  // enables a few usablity features for the custom timeout field
  function customTimeoutHandler() {
    const cr = document.querySelector('#to-custom');
    const ci = document.querySelector('#to-custom-value');
    cr.addEventListener('click', ev => ci.focus());
    ci.addEventListener('click', ev => cr.checked = true);
    ci.addEventListener('change', ev => {
      if(cr.checked) cr.value = ev.currentTarget.value;
    });
  }

  // toggles extra fields for certain selected options
  function routingHandler(el = document) {
    const route   = el.querySelector('select[data-route-type]');
    if(!route) return;

    const country = el.querySelector('[data-route-country-field]');
    route.addEventListener('change', ev => {
      if(ev.target.value == 'vpn')
        country.removeAttribute('hidden');
      else
        country.setAttribute('hidden', true);
    });
  }

  // sends a PUT request to the settings api to conclude and finalize the
  // submission and proceed to analysis
  function finishSubmission() {

    const { analysis_id, category } = window.Application;

    if(!analysis_id)
      return handleError('Found no analysis ID to send this request to. Refresh the page and try again.');

    const options = {
      timeout: parseInt(document.querySelector('input[name="timeout"]:checked').value),
      priority: parseInt(document.querySelector('select[name="priority"]').value),
      command: document.querySelector('input[name="command"]').value,
      orig_filename: document.querySelector('input[name="orig-filename"]').checked,
      route: {
        type: document.querySelector('select[name="route"]').value
      },
      platforms: [...document.querySelectorAll('[data-machine]')].map(machine => {
        let t = machine.querySelector('input[data-tags]');

        /** @TODO platforms expose a subset for a few default parameters. They override what the global
        settings already define when encountered. */
        let s = {};

        return {
          platform: machine.dataset.platform,
          os_version: machine.dataset.version,
          tags: t.value.length ? t.value.split(',') : [],
          settings: s
        }
      })
    };

    if(options.route && options.route.type.toLowerCase() == 'vpn')
      options.route.country = document.querySelector('select[name="country"]');

    if(category == 'file') {
      const selectedFile = document.querySelector('input[name="selected-file"]:checked');
      if(!selectedFile)
        return handleError('No file has been selected. Select a file and try again.');
      options.fileid = document.querySelector('input[name="selected-file"]:checked').value;
    }

    fetch('/api/analyses/'+analysis_id+'/settings', {
      method: 'PUT',
      body: JSON.stringify(options),
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.csrf_token
      }
    }).then(response => response.json())
      .then(response => {
        const { error } = response;
        if(error) {
          handleError(error);
        } else {
          window.location = '/analyses?submission='+analysis_id;
        }
      });

  }

  // apply all the handlers
  document.addEventListener('DOMContentLoaded', () => {
    fileTreeHandler();
    platformHandler();
    customTimeoutHandler();
    routingHandler();
    finish.addEventListener('click', ev => {
      finishSubmission();
    });
  });

}());
