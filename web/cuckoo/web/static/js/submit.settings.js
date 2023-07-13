(function() {

  const conclude = document.querySelector('#conclude-analysis');
  const finish = conclude.querySelector('#start-analysis');
  const delete_analysis = conclude.querySelector('#delete-analysis');
  const { analysis_id, category } = window.Application;

  /**
   * @class
   * @description 'UI Retrieving Model' implementation to keep a global track of
   * all the various settings. The values in this model are resolved each time when
   * called to be up-to-date whenever it is requested.
   *
   * usage:
   *
   * let value = Model.[property] // returns current value for field 'property'
   * let obj = Model.serialize() // outputs JSON format populated with all current values
   * let str = Model.stringify() // outputs stringified format of Model.serialize method output
   */
  const Model = window.Model = (function() {

    // shorthand querySelector for readability
    const getElement = (q,p=document) => p.querySelector(q);

    return new class SubmitOptions {

      // getters for the various DOM fields
      get fileid() {
        if(category !== "file") return null;
        const selected = getElement('input[name="selected-file"]:checked');
        if(selected)
          return selected.value;
        else
          return false;
      }
      get timeout() {
        const checkedOption = getElement('input[name="timeout"]:checked');
        let ret = parseInt(checkedOption.value);
        if(isNaN(ret)) {
          // assume that the timeout is from the custom field
          ret = parseInt(getElement('input#to-custom-value').value) || 120;
        }
        return ret;
      }
      get priority() { return parseInt(getElement('select[name="priority"]').value); }
      get command() { return getElement('input[name="command"]').value; }
      get orig_filename() { return getElement('input[name="orig-filename"]').checked }
      get disable_monitor() { return getElement('input[name="disablemonitor"]').checked }
      get browser() { return category == "url" ? getElement('select[name="browser"]').value : null; }
      get route() {
        let ret = {};
        let type = getElement('input[name="route"]:checked').value;
        if(type.length) {
          ret.type = type;
          if(type.toLowerCase() === 'vpn' && getElement('select[name="country"]').value.length) {
            ret.options = {};
            ret.options.country = getElement('select[name="country"]').value;
          };
        }
        return ret;
      }
      get platforms() {

        if(getElement('input#machine-auto').checked)
          return [];

        return [...document.querySelectorAll('[data-machine]')].map(machine => {
          let t = getElement('input[data-tags]', machine);

          // specific machine option overrides
          let s = {};

          let machineNetwork = getElement('[data-route-type]:checked', machine).value;
          let machineNetworkCountry = getElement('[data-route-country]', machine).value;
          let machineCommand = getElement('[data-command]', machine).value;
          let machineBrowser;

          // append route type and country if set
          if(machineNetwork.length) {
            s.route = {
              type: machineNetwork
            };
            if(machineNetwork.toLowerCase() == 'vpn' && machineNetworkCountry.length) {
              s.route.options = {};
              s.route.options.country = machineNetworkCountry;
            }
          }

          // append other options if set
          if(machineCommand.length)
            s.command = machineCommand;

          if(category === 'url') {
            machineBrowser = getElement('[data-browser]', machine).value;
            if(machineBrowser.length)
              s.browser = machineBrowser;
          }

          // return bundle of machine config for json serialization
          return {
            platform: machine.dataset.platform,
            os_version: machine.dataset.version,
            tags: t.value.length ? t.value.split(',') : [],
            settings: s
          }
        });
      }
      get options() {
        return JSON.parse(document.querySelector('#custom-options').dataset.value || '{}');
      }
      // returns object populated with field values
      serialize() {
        let ret = {
          timeout: this.timeout,
          priority: this.priority,
          command: this.command,
          orig_filename: this.orig_filename,
          route: this.route,
          platforms: this.platforms,
          options: {
            ...this.options
          }
        }

        if(this.disable_monitor === true)
          ret.options.disablemonitor = this.disable_monitor;

        switch(category) {
          case "file":
            ret.fileid = this.fileid;
          break;
          case "url":
            ret.browser = this.browser;
          break;
        }
        return ret;
      }

      // returns a stringified output of SubmitOptions.serialize method
      stringify() {
        return JSON.stringify(this.serialize());
      }

    }();

  }());

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

    const { category }  = window.Application;
    const tab           = document.querySelector('.tabbar-link[href="#machines"]');
    const platforms     = document.querySelector('select[name="platform"]');
    const versions      = document.querySelector('select[name="version"]');
    const addPlatform   = document.querySelector('#add-platform');
    const machinery     = document.querySelector('#machinery');
    const totalMachines = document.querySelector('#total-machines');
    const picker        = document.querySelector('#pick-machine');
    const autoMachine   = document.querySelector('input#machine-auto')
    let banner, dot;

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

      let count;
      if(autoMachine.checked) {
        count = 1;
      } else {
        count = machinery.querySelectorAll('[data-machine]').length;
      }

      totalMachines.textContent = count;
      blink(totalMachines);

      if(count > 0) {
        if(banner)
          banner.remove();
        finish.removeAttribute('disabled');
        if(tab.querySelector('.dot')) tab.querySelector('.dot').remove();
      } else {
        if(banner) banner.remove();
        banner = lib.banner('Add at least one machine to start analysis or tick the default box.', 'danger');
        machinery.appendChild(banner);
        finish.setAttribute('disabled', true);

        dot = document.createElement('span');
        dot.classList.add('dot');
        dot.classList.add('is-red');
        tab.appendChild(dot);
      }
    }

    // handle machines being added to the list
    function addMachine(data={}) {

      const { routes, browsers } = Application.possible_settings;
      const uniq = Math.floor(Number.MAX_SAFE_INTEGER * Math.random()).toString(4);

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

              <div class="field" data-routing>
                <label class="label is-link has-no-underline" onclick="toggleVisibility(this.parentNode.querySelector('[data-toggle-network]'), null, event);">
                  <span class="icon is-caret">
                    <i class="fas fa-caret-right"></i>
                  </span>
                  Network routing
                </label>
                <div data-toggle-network hidden>

                  <div class="field">
                    <div class="multi-toggle">
                      <div class="control">
                        <input type="radio" value="" name="route-${uniq}" id="route-none-${uniq}" checked data-route-type />
                        <label class="label" for="route-none-${uniq}">No route</label>
                      </div>
                      <div class="control">
                        <input type="radio" value="drop" id="route-drop-${uniq}" name="route-${uniq}" data-route-type ${routes.available.indexOf('drop') == -1 ? 'disabled' : ''} />
                        <label class="label" for="route-drop-${uniq}">Drop</label>
                      </div>
                      <div class="control">
                        <input type="radio" value="internet" id="route-internet-${uniq}" name="route-${uniq}" data-route-type ${routes.available.indexOf('internet') == -1 ? 'disabled' : ''} />
                        <label class="label" for="route-internet-${uniq}">Internet</label>
                      </div>
                      <div class="control">
                        <input type="radio" value="vpn" id="route-vpn-${uniq}" name="route-${uniq}" data-route-type ${routes.available.indexOf('vpn') == -1 ? 'disabled' : ''} />
                        <label class="label" for="route-vpn-${uniq}">VPN</label>
                      </div>
                    </div>
                  </div>
                  <div class="field is-inline no-padding-y no-padding-right no-margin-top" data-route-country-field hidden>
                    <label class="label">Country</label>
                    <div class="control is-select">
                      <select class="input" data-route-country>
                        <option value="">First available</option>
                        <optgroup label="Available countries">
                          ${ routes.vpn.countries.map(c => {
                            return `<option value="${c}">${lib.SafeString(c)}</option>`;
                          }).join('') }
                        </optgroup>
                      </select>
                    </div>
                  </div>
                  <p class="has-text-small has-half-opacity">
                    <span class="icon">
                      <i class="fas fa-info-circle"></i>
                    </span>
                    Configure type of network routing
                  </p>
                </div>
              </div>

              ${category == 'url' ? `
                <div class="field">
                  <label class="label is-link has-no-underline" onclick="toggleVisibility(this.parentNode.querySelector('.control'), null, event)">
                    <span class="icon is-caret">
                      <i class="fas fa-caret-right"></i>
                    </span> Browser
                  </label>
                  <div class="control is-select" hidden>
                    <select class="input" data-browser>
                      <option value>Platform default</option>
                      ${ browsers.map(b => `<option value="${b}">${b}</option>`).join('') }
                    </select>
                    <p class="has-text-small has-half-opacity">
                      <span class="icon">
                        <i class="fas fa-info-circle"></i>
                      </span>
                      Choose browser to open the submitted URL in.
                    </p>
                  </div>
                </div>
              ` : ''}

              <div class="field">
                <label class="label is-link has-no-underline" onclick="toggleVisibility(this.parentNode.querySelector('.control'), null, event)">
                  <span class="icon is-caret">
                    <i class="fas fa-caret-right"></i>
                  </span> Commands
                </label>
                <div class="control" hidden>
                  <input class="input" type="text" id="command" data-command />
                  <p class="has-text-small has-half-opacity">
                    <span class="icon">
                      <i class="fas fa-info-circle"></i>
                    </span>
                    Command that is used to launch the target. Use <span data-click-to-copy class="is-monospace has-text-red">%PAYLOAD%</span> where the target name should be on launch
                  </p>
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
      routingHandler(machine.querySelector('[data-routing]'));

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
    // countMachines();

    autoMachine.addEventListener('change', () => {
      let isChecked = autoMachine.checked;
      picker.querySelectorAll('input, select, button').forEach(inp => inp.toggleAttribute('disabled', isChecked));
      picker.classList.toggle('is-disabled', autoMachine.checked);
      document.querySelectorAll('[data-machine]').forEach(m => m.classList.toggle('is-disabled', autoMachine.checked));


      if(isChecked) {
        if(banner) banner.remove();
        if(dot) dot.remove(); dot = null;
        finish.removeAttribute('disabled');
      } else {
        countMachines();
      }

    });
    autoMachine.dispatchEvent(new Event('change'));

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
    const routes = el.querySelectorAll('input[name^="route"]');
    if(!routes) return;

    const country = el.querySelector('[data-route-country-field]');
    routes.forEach(r => r.addEventListener('change', () => {
      if(r.checked && r.value == 'vpn') {
        country.removeAttribute('hidden');
      } else {
        country.setAttribute('hidden', true);
      }
    }));

  }

  // handles custom options field interactions
  function customOptionsHandler() {

    const elem = document.querySelector('#custom-options');
    if(!elem) {
      console.info('not initializing custom options because the element is not on this page.');
      return false;
    };

    const entries     = [];
    const customBody  = elem.querySelector('tbody');
    const customKey   = elem.querySelector('input#key-custom');
    const customValue = elem.querySelector('input#value-custom');
    const customAdd   = elem.querySelector('button#add-custom');

    const template = (data={}) => parseDOM(`
      <table>
        <tr data-id="${data.id}">
          <td class="field-key">${lib.SafeString(data.key)}</td>
          <td class="field-value">${lib.SafeString(data.value)}</td>
          <td>
            <button type="button" class="button is-small is-red">
              <i class="fas fa-times"></i>
            </button>
          </td>
        </tr>
      </table>
    `).querySelector('tr');

    function writeEntries() {
      let result = {};
      for(let e in entries) {
        result[entries[e].key] = entries[e].value;
      }
      elem.dataset.value = JSON.stringify(result);
    }

    function addRow(key, value) {

      if(!key || !value)
        return;

      const id = Math.random().toString(16).substr(2, 8);
      const data = { key, value, id };
      const tmpl = template(data);
      customBody.appendChild(tmpl);

      tmpl.querySelector('button').addEventListener('click', () => {
        tmpl.remove();
        let entryIndex = entries.map(e => e.id).indexOf(id);
        entries.splice(entryIndex, 1);
        writeEntries();
      });

      entries.push(data);
      writeEntries();

    }

    customAdd.addEventListener('click', ev => {
      addRow(customKey.value, customValue.value);
      customKey.value   = '';
      customValue.value = '';
      customKey.focus();
    });

    [customKey, customValue].forEach(el => {
      el.addEventListener('keypress', ev => {
        if(ev.keyCode === 13) {
          if(customKey.value.length == 0) {
            customKey.focus();
            return;
          }
          if(customValue.value.length == 0) {
            customValue.focus();
            return;
          }
          customAdd.dispatchEvent(new Event('click'));
        }
      });
    })

  }

  // sends a PUT request to the settings api to conclude and finalize the
  // submission and proceed to analysis
  function finishSubmission() {

    if(!analysis_id)
      return handleError('Found no analysis ID to send this request to. Refresh the page and try again.');

    if(category == "file" && !Model.fileid)
      return handleError('No file selected. Select a file from the tree and try again.');

    fetch('/api/analyses/'+analysis_id+'/settings', {
      method: 'PUT',
      body: Model.stringify(),
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

  function deleteSubmission() {

    if(!analysis_id)
      return handleError('Found no analysis ID to send this request to. Refresh the page and try again.');


    fetch('/api/analyses/'+analysis_id+'/deleteanalysis', {
      method: 'GET',
      headers: {
        'X-CSRFToken': window.csrf_token
      }
    }).then(response => response.json())
      .then(response => {
        const { error } = response;

        if(error) {
          handleError(error);
        } else {
          window.location = '/analyses/';
        }
      });

  }

  // apply all the handlers
  document.addEventListener('DOMContentLoaded', () => {
    fileTreeHandler();
    platformHandler();
    customTimeoutHandler();
    routingHandler();
    customOptionsHandler();
    finish.addEventListener('click', ev => {
      finishSubmission();
    });
    delete_analysis.addEventListener('click', ev => {
      deleteSubmission();
    });
  });

}());
