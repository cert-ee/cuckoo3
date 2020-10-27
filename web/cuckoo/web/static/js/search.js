(function() {

  // dom references
  const searchForm    = document.querySelector('#search-form');
  const submit        = searchForm.querySelector('input[type="submit"]');
  const results       = document.querySelector('#results tbody');
  const skip          = document.querySelectorAll('#pagination [data-skip]');
  const pages         = document.querySelector('#pagination .current-page');
  const selectLimit   = document.querySelector('#select-limit select');
  const selectedLimit = document.querySelector('#selected-limit');
  const currentPage   = document.querySelector('#current-page');
  const possiblePages = document.querySelector('#possible-pages');

  const props = window.props = {
    offset: 0,
    query: searchForm.elements[0].value,
    limit: 20,
    count: 0,
    possible: 0,
    max: 0
  };

  // indicates something running in the background inside a button
  // - the button disabled when the spinner is loading
  function buttonLoader(btn) {
    if(!btn instanceof HTMLElement) return;
    const originalContent = btn.textContent;
    return {
      start: () => {
        btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i>`;
        btn.disabled = true;
      },
      stop: () => {
        btn.textContent = originalContent;
        btn.disabled = false;
      }
    }
  }

  // prints a message in the table with a formatted error.
  function handleError(data) {

    if(data instanceof Error)
      data = { error: data.name + ': ' + data.message + ' (javascript error)' };

    const currentError = results.querySelector('tr#search-error');
    if(currentError) currentError.remove();

    results.innerHTML = `
      <tr class="has-background-red" id="search-error">
        <td colspan="4">
          <p class="has-text-center">${data.error}</p>
        </td>
      </tr>
    `;
  }

  // a single row with a message to display for idle and empty states
  function messageRow(rowText) {
    if(!rowText)
      rowText = 'Type a query in the search bar above to display results.';
    results.innerHTML = `
      <tr>
        <td colspan="4">
          <p class="has-half-opacity has-text-center">${rowText}</p>
        </td>
      </tr>
    `;
  }

  // request serializer
  function search(query, reset = false) {

    if(!window.csrf_token) return Promise.reject({error: 'No CSRF token present.'});
    if(query) props.query = query;

    if(reset) {
      props.offset = 0;
      props.count  = 0;
      props.possible = 0;
      props.max = 0;
    };

    const data = {...props};
    if(data.count) delete data.count;
    if(data.possible) delete data.possible;
    if(data.max) delete data.max;

    return new Promise((resolve, reject) => {

      const btn = buttonLoader(submit);
      btn.start();

      fetch('/api/search', {
        method: 'POST',
        headers: {
          'X-CSRFToken': window.csrf_token,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      }).then(res => res.json())
        .then(res => resolve(res))
        .catch(err => reject(err))
        .finally(() => btn.stop());

    });

  }

  // renders rows with results
  function displayResults(data, rowText) {

    const { count, matches, offset, possible, max } = data;
    const { limit } = props;

    props.count = count;
    props.possible = possible;
    props.max = Math.floor(possible / limit);

    results.innerHTML = '';

    if(matches && matches.length) {
      results.innerHTML = matches.map(match => `
        <tr>
          <td>${match.analysis_id}</td>
          <td>${match.task_id}</td>
          ${match.matches.map(m => `
            <td>${m.field}</td>
            <td>${m.matches.join('<br />')}</td>
          `).join('')}
        </tr>
      `).join('');
    } else {
      messageRow('No results returned.');
    }

    updatePagination();
  }

  // when this function is called, the props state will be used to reflect the
  // offset, limit and pagination models into the UI.
  function updatePagination() {
    const { offset, limit, count, possible, max } = props;
    const navigational = [currentPage, possiblePages, pages];

    // set up 'disabled' features to indicate possibilities
    let disableElement = el => el.classList.add('is-disabled');
    skip.forEach(s => s.classList.remove('is-disabled'));
    navigational.forEach(s => s.parentNode.classList.remove('is-disabled'));

    // if the offset is zero or less, disable previous buttons
    if(offset <= 0)
      [skip[0], skip[1], skip[2]].forEach(disableElement);

    // if the count of results is smaller than the limit, disable 'next' buttons
    if((count !== limit) || (offset / limit >= max))
      [skip[3], skip[4], skip[5]].forEach(disableElement);

    // disable the buttons that point to 'impossible' pages
    if(offset + (limit * 10) >= possible) disableElement(skip[5])
    if(offset + (limit * 5) >= possible) disableElement(skip[4])
    if(offset + limit >= possible) disableElement(skip[3]);

    if(offset - (limit * 10) < 0) disableElement(skip[0]);
    if(offset - (limit * 5) < 0) disableElement(skip[1]);
    if(offset - limit < 0) disableElement(skip[2]);

    // 'disable' navigational elements when there are no records
    if(count == 0) navigational.forEach(s => disableElement(s.parentNode));

    // update text values to reflect the current search state
    pages.textContent = `Rows ${offset} - ${offset + count}`;
    selectedLimit.textContent = props.limit;
    currentPage.textContent = offset / limit;
    possiblePages.textContent = max;
  }

  document.addEventListener('DOMContentLoaded', () => {

    // engage async search by submitting the search form (enter or click)
    searchForm.addEventListener('submit', ev => {
      ev.preventDefault();
      const values = new FormData(searchForm);
      search(values.get('query'), true)
        .then(displayResults)
        .catch(handleError);
    });

    // bind pagination buttons
    skip.forEach(s => s.addEventListener('click', ev => {
      ev.preventDefault();
      props.offset += parseInt(s.getAttribute('href')) * props.limit;
      if(props.offset <= 0) props.offset = 0;
      search(props.query)
        .then(displayResults)
        .catch(handleError);
    }));

    // limit selector
    selectLimit.addEventListener('change', ev => {
      props.limit = parseInt(selectLimit.value);
      search(props.query)
        .then(displayResults)
        .catch(handleError);
    });

    // display idle message on startup
    messageRow();
    updatePagination();

  });

}());
