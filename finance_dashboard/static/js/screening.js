// Render the RSI14 screening table with sorting, search, and pagination.
//
// This is the whole of the JavaScript this repository writes; gridjs.umd.js
// beside it is a third-party bundle. Nothing here fetches anything: the rows
// are read out of the JSON script element index.html already emitted, so the
// table is built from markup that was delivered with the page and this
// application needs no API of its own.
//
// The screening section is the one part of the site not rendered on the
// server. index.html emits an empty container for this script to fill, and a
// <noscript> copy of the same table for a reader without JavaScript. This
// script returns without touching the page when the container, the data
// element or Grid.js is absent, or when there are no rows, which leaves the
// section empty rather than half built or raising.

document.addEventListener("DOMContentLoaded", function () {
  var wrapper = document.getElementById("screening-grid");
  var source = document.getElementById("screening-data");
  if (!wrapper || !source || typeof gridjs === "undefined") {
    return;
  }

  var rows = JSON.parse(source.textContent || "[]");
  if (rows.length === 0) {
    return;
  }

  var template = wrapper.dataset.stockUrl || "/stock/__CODE__";

  function link(code, label) {
    var anchor = document.createElement("a");
    anchor.href = template.replace("__CODE__", encodeURIComponent(code));
    anchor.textContent = label;
    return gridjs.html(anchor.outerHTML);
  }

  function number(value) {
    var parsed = Number(String(value).replace(/,/g, ""));
    return isNaN(parsed) ? 0 : parsed;
  }

  function delimited(cell) {
    return Math.trunc(cell).toLocaleString("en-US");
  }

  var columns = [
    { name: "銘柄", formatter: function (cell) { return link(cell, cell); } },
    { name: "企業名", formatter: function (cell, row) { return link(row.cells[0].data, cell); } },
    { name: "始値", formatter: delimited },
    { name: "高値", formatter: delimited },
    { name: "安値", formatter: delimited },
    { name: "終値", formatter: delimited },
    { name: "差", formatter: delimited },
    { name: "比率", formatter: function (cell) { return cell + "%"; } },
    { name: "RSI14", formatter: function (cell) { return cell.toFixed(2); } }
  ];

  var data = rows.map(function (row) {
    return [
      row.code,
      row.name,
      number(row.open),
      number(row.high),
      number(row.low),
      number(row.close),
      number(row.diff),
      number(row.ratio),
      number(row.rsi)
    ];
  });

  new gridjs.Grid({
    columns: columns,
    data: data,
    sort: true,
    search: true,
    pagination: { limit: 50 }
  }).render(wrapper);
});
