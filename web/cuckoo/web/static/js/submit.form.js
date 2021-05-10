(function toggleEncryptedPassword() {

  // provide a text box to fill in a password if the archive uploaded
  // is encrypted

  const hasPassword = document.querySelector('input#has-password');
  const password    = document.querySelector('#password-field');
  hasPassword.addEventListener("change", ev => toggleVisibility(password, ev.target.checked));

}());
