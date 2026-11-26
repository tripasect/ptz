(function () {
  var MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"];
  var LEAP_REMAINDERS = [1, 5, 9, 13, 17, 22, 26, 30];

  function div(a, b) {
    return Math.trunc(a / b);
  }

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  function isLeap(year) {
    return LEAP_REMAINDERS.indexOf(year % 33) !== -1;
  }

  function daysInMonth(year, month) {
    if (month <= 6) return 31;
    if (month <= 11) return 30;
    return isLeap(year) ? 30 : 29;
  }

  function gregorianToJalali(gy, gm, gd) {
    var monthDays = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
    var gy2 = gm > 2 ? gy + 1 : gy;
    var days = 355666 + (365 * gy) + div(gy2 + 3, 4) - div(gy2 + 99, 100) + div(gy2 + 399, 400) + gd + monthDays[gm - 1];
    var jy = -1595 + (33 * div(days, 12053));
    days %= 12053;
    jy += 4 * div(days, 1461);
    days %= 1461;
    if (days > 365) {
      jy += div(days - 1, 365);
      days = (days - 1) % 365;
    }
    if (days < 186) {
      return { y: jy, m: 1 + div(days, 31), d: 1 + (days % 31) };
    }
    return { y: jy, m: 7 + div(days - 186, 30), d: 1 + ((days - 186) % 30) };
  }

  function todayJalali() {
    var now = new Date();
    return gregorianToJalali(now.getFullYear(), now.getMonth() + 1, now.getDate());
  }

  function latinDigits(value) {
    return String(value)
      .replace(/[۰-۹]/g, function (digit) { return "۰۱۲۳۴۵۶۷۸۹".indexOf(digit); })
      .replace(/[٠-٩]/g, function (digit) { return "٠١٢٣٤٥٦٧٨٩".indexOf(digit); });
  }

  function parseInput(value) {
    var match = latinDigits(value).trim().match(/^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$/);
    if (!match) return null;
    var year = Number(match[1]);
    var month = Number(match[2]);
    var day = Number(match[3]);
    if (month < 1 || month > 12 || day < 1 || day > daysInMonth(year, month)) return null;
    return { y: year, m: month, d: day };
  }

  function addOption(select, value, label) {
    var option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    select.appendChild(option);
  }

  function mount(input) {
    if (input.dataset.jalaliReady === "1") return;
    input.dataset.jalaliReady = "1";

    var today = todayJalali();
    var selected = parseInput(input.value);
    var box = document.createElement("div");
    box.className = "jalali-selects";

    var year = document.createElement("select");
    var month = document.createElement("select");
    var day = document.createElement("select");
    year.className = month.className = day.className = "input";
    year.setAttribute("aria-label", "سال");
    month.setAttribute("aria-label", "ماه");
    day.setAttribute("aria-label", "روز");

    addOption(year, "", "سال");
    var y;
    for (y = today.y; y >= 1280; y -= 1) addOption(year, String(y), String(y));

    addOption(month, "", "ماه");
    MONTHS.forEach(function (name, index) {
      addOption(month, String(index + 1), name);
    });

    function maxDay() {
      var yearValue = Number(year.value);
      var monthValue = Number(month.value);
      if (!yearValue || !monthValue) return 31;
      var length = daysInMonth(yearValue, monthValue);
      if (yearValue === today.y && monthValue === today.m) return Math.min(length, today.d);
      return length;
    }

    function refillDays() {
      var previous = day.value;
      day.innerHTML = "";
      addOption(day, "", "روز");
      var limit = maxDay();
      var number;
      for (number = 1; number <= limit; number += 1) addOption(day, String(number), String(number));
      if (previous && Number(previous) <= limit) day.value = previous;
    }

    function limitMonths() {
      var yearValue = Number(year.value);
      Array.prototype.forEach.call(month.options, function (option) {
        if (!option.value) return;
        option.disabled = yearValue === today.y && Number(option.value) > today.m;
      });
      if (month.selectedOptions[0] && month.selectedOptions[0].disabled) month.value = "";
    }

    function write() {
      if (!year.value || !month.value || !day.value) {
        input.value = "";
        return;
      }
      input.value = year.value + "/" + pad(month.value) + "/" + pad(day.value);
    }

    year.addEventListener("change", function () {
      limitMonths();
      refillDays();
      write();
    });
    month.addEventListener("change", function () {
      refillDays();
      write();
    });
    day.addEventListener("change", write);

    refillDays();
    if (selected) {
      year.value = String(selected.y);
      limitMonths();
      month.value = String(selected.m);
      refillDays();
      day.value = String(selected.d);
      write();
    }

    box.appendChild(year);
    box.appendChild(month);
    box.appendChild(day);
    input.insertAdjacentElement("afterend", box);
  }

  function mountAll() {
    document.querySelectorAll("input.jalali-picker").forEach(mount);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountAll);
  } else {
    mountAll();
  }
})();
