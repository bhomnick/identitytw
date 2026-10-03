// identity.tw — the three bits of behaviour the page needs. No dependencies.
(function () {
  'use strict';

  // Report: text search, category filter, and sorting by the select or by
  // clicking a column header. Rows are sorted in place; nothing is hidden
  // from find-in-page except by the filters.
  var search = document.getElementById('report-search');
  var category = document.getElementById('report-category');
  var sortSelect = document.getElementById('report-sort');
  var table = document.querySelector('.report-table');
  var rows = table ? table.querySelectorAll('tbody tr[data-name]') : [];
  var emptyRow = table ? table.querySelector('.empty') : null;
  var count = document.getElementById('report-count');
  if (search && category && rows.length) {
    var tbody = rows[0].parentNode;
    var all = Array.prototype.slice.call(rows);
    var headers = table.querySelectorAll('th[data-sort]');
    // First click on a column sorts it this way; a second click flips it.
    var defaultDir = { name: 'asc', category: 'asc', score: 'desc', updated: 'desc',
                       legacy_arc: 'asc', new_arc: 'asc', service: 'asc', registration: 'asc' };
    // The select's options, as column + direction.
    var presets = { name: ['name', 'asc'], category: ['category', 'asc'], best: ['score', 'desc'],
                    worst: ['score', 'asc'], updated: ['updated', 'desc'] };
    var current = { key: 'name', dir: 'asc' };

    var valueOf = function (row, key) {
      if (key === 'name') { return row.dataset.name; }
      if (key === 'category') { return row.dataset.categoryName + '\u0000' + row.dataset.name; }
      if (key === 'updated') { return row.dataset.updated; }
      return parseFloat(row.dataset[key.replace(/_([a-z])/g, function (m, c) { return c.toUpperCase(); })]);
    };
    var compare = function (a, b, key) {
      var va = valueOf(a, key), vb = valueOf(b, key);
      if (typeof va === 'number') { return va - vb; }
      return va < vb ? -1 : (va > vb ? 1 : 0);
    };
    var applySort = function () {
      var sorted = all.slice().sort(function (a, b) {
        var c = compare(a, b, current.key) || compare(a, b, 'name');
        return current.dir === 'asc' ? c : -c;
      });
      sorted.forEach(function (row) { tbody.insertBefore(row, emptyRow); });
      Array.prototype.forEach.call(headers, function (th) {
        if (th.dataset.sort === current.key) {
          th.setAttribute('aria-sort', current.dir === 'asc' ? 'ascending' : 'descending');
        } else {
          th.removeAttribute('aria-sort');
        }
      });
      if (sortSelect) {
        var match = Object.keys(presets).filter(function (name) {
          return presets[name][0] === current.key && presets[name][1] === current.dir;
        })[0];
        if (match) { sortSelect.value = match; }
      }
    };
    Array.prototype.forEach.call(headers, function (th) {
      th.querySelector('button').addEventListener('click', function () {
        var key = th.dataset.sort;
        if (current.key === key) {
          current.dir = current.dir === 'asc' ? 'desc' : 'asc';
        } else {
          current = { key: key, dir: defaultDir[key] || 'asc' };
        }
        applySort();
      });
    });
    if (sortSelect) {
      sortSelect.addEventListener('change', function () {
        var preset = presets[sortSelect.value];
        if (preset) { current = { key: preset[0], dir: preset[1] }; applySort(); }
      });
    }
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
