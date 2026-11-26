(function () {
  var latin = {
    "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
    "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
    "٠": "0", "١": "1", "٢": "2", "٣": "3", "٤": "4",
    "٥": "5", "٦": "6", "٧": "7", "٨": "8", "٩": "9"
  };

  function toLatin(value) {
    return String(value).replace(/[۰-۹٠-٩]/g, function (digit) {
      return latin[digit];
    });
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    form.querySelectorAll("input, textarea").forEach(function (field) {
      if (field.type === "file" || field.type === "checkbox" || field.type === "radio") return;
      field.value = toLatin(field.value);
    });
  }, true);
})();
