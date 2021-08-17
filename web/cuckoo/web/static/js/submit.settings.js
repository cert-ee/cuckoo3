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

      const machine = parseDOM(`
        <div class="box has-border has-background-light no-padding" data-machine data-platform="${data.platform}" data-version="${data.version}">
          <div class="columns is-divided is-gapless">
            <div class="column has-padding-x has-padding-bottom">
              <div class="columns is-divided">
                <p class="column"><strong>${lib.SafeString(data.platform)}</strong></p>
                <p class="column">${lib.SafeString(data.version)}</p>
              </div>
              <div class="field is-inline">
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

  // sends a PUT request to the settings api to conclude and finalize the
  // submission and proceed to analysis
  function finishSubmission() {

    const { analysis_id, category } = window.Application;

    if(!analysis_id)
      return handleError('Found no analysis ID to send this request to. Refresh the page and try again.');

    const options = {
      timeout: parseInt(document.querySelector('input[name="timeout"]:checked').value),
      priority: parseInt(document.querySelector('select[name="priority"]').value),
      platforms: [...document.querySelectorAll('[data-machine]')].map(machine => {
        let t = machine.querySelector('input[data-tags]');
        return {
          platform: machine.dataset.platform,
          os_version: machine.dataset.version,
          tags: t.value.length ? t.value.split(',') : []
        }
      })
    };

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
    finish.addEventListener('click', ev => {
      finishSubmission();
    });
  });

}());
