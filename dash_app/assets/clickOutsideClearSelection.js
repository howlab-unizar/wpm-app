(function () {
  if (window.__outsideClickHandlerInstalled__) return;
  window.__outsideClickHandlerInstalled__ = true;

  document.addEventListener(
    "click",
    function (e) {
      var grids = [
        document.getElementById("no-procesados-grid"),
        document.getElementById("procesados-grid"),
      ];

      var anyGridPresent = grids.some(function (g) { return !!g; });
      if (!anyGridPresent) return;

      // ¿Click dentro de algún grid?
      var gridClicked = grids.find(function (g) {
        return g && e.target && e.target.closest && e.target.closest("#" + g.id);
      });

      // ¿Click sobre alguna fila?
      var onRow = gridClicked ? !!e.target.closest(".ag-row") : false;

      // Dispara si:
      // 1) el click fue FUERA de todos los grids, o
      // 2) el click fue DENTRO de un grid pero NO sobre una fila (header, huecos, barra lateral…)
      if (!gridClicked || (gridClicked && !onRow)) {
        var btn = document.getElementById("outside-click");
        if (btn) btn.click();
      }
      // Si fue sobre una fila, no hacemos nada (deja la selección como esté)
    },
    true
  );
})();