(function () {
  window.attachKeystroke = function (input, holdsId, intervalsId) {
    if (!input) return;
    var holds = [];
    var intervals = [];
    var lastDown = 0;

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Tab' || e.key === 'Shift' || e.key === 'Control' || e.key === 'Alt') return;
      var now = performance.now();
      if (lastDown) {
        intervals.push(now - lastDown);
      }
      lastDown = now;
    });

    input.addEventListener('keyup', function (e) {
      if (e.key === 'Tab' || e.key === 'Shift' || e.key === 'Control' || e.key === 'Alt') return;
      var now = performance.now();
      if (lastDown) {
        holds.push(now - lastDown);
      }
    });

    var form = input.form;
    if (form) {
      form.addEventListener('submit', function () {
        var h = document.getElementById(holdsId);
        var i = document.getElementById(intervalsId);
        if (h) h.value = holds.slice(0, 40).join(',');
        if (i) i.value = intervals.slice(0, 40).join(',');
      });
    }
  };
})();
