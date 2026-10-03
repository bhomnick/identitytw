// identity.tw — the three bits of behaviour the page needs. No dependencies.
(function () {
  'use strict';

  // Report filters: category select and text search.
  var search = document.getElementById('report-search');
  var category = document.getElementById('report-category');
  var sort = document.getElementById('report-sort');
  var rows = document.querySelectorAll('.report-table tbody tr[data-name]');
  var emptyRow = document.querySelector('.report-table .empty');
  var count = document.getElementById('report-count');
  if (search && category && rows.length) {
    var tbody = rows[0].parentNode;
    var original = Array.prototype.slice.call(rows);
    var orders = {
      category: function (a, b) { return original.indexOf(a) - original.indexOf(b); },
      worst: function (a, b) { return (+a.dataset.score) - (+b.dataset.score) || a.dataset.name.localeCompare(b.dataset.name); },
      best: function (a, b) { return (+b.dataset.score) - (+a.dataset.score) || a.dataset.name.localeCompare(b.dataset.name); },
      name: function (a, b) { return a.dataset.name.localeCompare(b.dataset.name); },
      updated: function (a, b) { return b.dataset.updated.localeCompare(a.dataset.updated) || a.dataset.name.localeCompare(b.dataset.name); }
    };
    var reorder = function () {
      var sorted = original.slice().sort(orders[sort && sort.value] || orders.category);
      sorted.forEach(function (row) { tbody.insertBefore(row, emptyRow); });
    };
    if (sort) { sort.addEventListener('change', reorder); }
    var apply = function () {
      var query = search.value.trim().toLowerCase();
      var wanted = category.value;
      var shown = 0;
      Array.prototype.forEach.call(rows, function (row) {
        var ok = (!wanted || row.dataset.category === wanted) &&
                 (!query || row.dataset.name.indexOf(query) !== -1);
        row.hidden = !ok;
        if (ok) { shown += 1; }
      });
      if (emptyRow) { emptyRow.hidden = shown > 0; }
      if (count) { count.textContent = shown + ' / ' + rows.length; }
    };
    search.addEventListener('input', apply);
    category.addEventListener('change', apply);
    apply();
  }

  // Code sample tabs.
  Array.prototype.forEach.call(document.querySelectorAll('.tabs'), function (tabs) {
    var buttons = tabs.querySelectorAll('[role="tab"]');
    var select = function (button) {
      Array.prototype.forEach.call(buttons, function (other) {
        var selected = other === button;
        other.setAttribute('aria-selected', selected ? 'true' : 'false');
        other.tabIndex = selected ? 0 : -1;
        document.getElementById(other.getAttribute('aria-controls')).hidden = !selected;
      });
    };
    Array.prototype.forEach.call(buttons, function (button, index) {
      button.addEventListener('click', function () { select(button); });
      button.addEventListener('keydown', function (event) {
        var next = null;
        if (event.key === 'ArrowRight') { next = buttons[(index + 1) % buttons.length]; }
        if (event.key === 'ArrowLeft') { next = buttons[(index - 1 + buttons.length) % buttons.length]; }
        if (next) { event.preventDefault(); select(next); next.focus(); }
      });
    });
  });

  // "Try it out": call the API and show the raw exchange.
  var form = document.getElementById('api-form');
  if (form) {
    var apiUrl = form.getAttribute('data-api-url');
    var input = document.getElementById('api-id');
    var button = document.getElementById('api-submit');
    var example = document.getElementById('api-example');
    var requestCode = document.getElementById('api-request');
    var responseCode = document.getElementById('api-response');
    input.addEventListener('input', function () { button.disabled = input.value.trim() === ''; });
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var id = input.value.trim();
      if (!id) { return; }
      var url = apiUrl + encodeURIComponent(id);
      requestCode.textContent = 'GET ' + url;
      responseCode.textContent = '…';
      example.hidden = false;
      fetch(url)
        .then(function (response) { return response.text(); })
        .then(function (text) { responseCode.textContent = text; })
        .catch(function (error) { responseCode.textContent = 'Request failed: ' + error; });
    });
  }
})();
