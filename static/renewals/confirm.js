(function () {
  var dialog = document.getElementById("confirm-dialog");
  var word = document.getElementById("confirm-word");
  var input = document.getElementById("confirm-input");
  var error = document.getElementById("confirm-error");
  if (!dialog || !word || !input) return;

  var pending = null;

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    var phrase = form.getAttribute("data-confirm");
    if (!phrase || form.dataset.confirmed === "1") return;
    event.preventDefault();
    pending = form;
    word.textContent = phrase;
    input.value = "";
    error.hidden = true;
    dialog.showModal();
    input.focus();
  }, true);

  dialog.querySelector("form").addEventListener("submit", function (event) {
    var submitter = event.submitter;
    if (!submitter || submitter.value !== "ok") {
      pending = null;
      return;
    }
    event.preventDefault();
    if (input.value.trim() !== word.textContent) {
      error.hidden = false;
      input.focus();
      return;
    }
    var form = pending;
    pending = null;
    dialog.close();
    if (!form) return;
    form.dataset.confirmed = "1";
    form.requestSubmit();
  });
})();
