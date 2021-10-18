(function() {

  let error, url;
  const form = document.querySelector('form#compare-form');

  function makeError(msg) {
    if(error)
      error.remove();
    error = document.createElement('div');
    error.classList.add('has-padding-x');
    error.appendChild(lib.banner(msg || 'Something went wrong', 'danger'));
    if(form)
      form.parentNode.insertBefore(error, form);
    else
      return error;
  }

  window.validate = function validate(id) {
    return new RegExp(/[0-9]{8}-[A-Z0-9]{6}_[0-9]{1,3}/).test(id);
  }

  if(form) {
    form.addEventListener('submit', ev => {
      ev.preventDefault();
      const left = form.querySelector('input#task-left');
      const right = form.querySelector('input#task-right');

      if(!(validate(left.value) && validate(right.value))) {
        return makeError('Incorrect task ID. Task ID format is YYYYMMDD-XXXXXX_<task number>.');
      }

      if((left.value && right.value)) {
        if(left.value !== right.value) {
          url = '/compare/'+left.value+'/'+right.value;
          // test url to prevent ugly django error on incorrect input
          fetch(url)
            .then(res => {
              console.log(res);
              if(res.status == 200)
                window.location = url;
              else
                makeError('Task comparison could not be completed, do both tasks exist?');
            });
        } else {
          makeError('IDs cannot be equal.');
        }
      }
    });
  }

}());
