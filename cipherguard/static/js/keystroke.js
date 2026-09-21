(function () {
  const TARGETS = {
    primary: ['holds', 'intervals'],
    confirm: ['holds_confirm', 'intervals_confirm'],
  };
  const IGNORED = ['Tab', 'Shift', 'Control', 'Alt', 'Meta', 'CapsLock', 'Enter'];
  const LIMIT = 40;

  function attach(input) {
    const channel = TARGETS[input.dataset.keystroke];
    if (!channel || !input.form) {
      return;
    }

    const holds = [];
    const intervals = [];
    let pressedAt = 0;
    let previousPress = 0;

    input.addEventListener('keydown', (event) => {
      if (IGNORED.indexOf(event.key) !== -1 || event.repeat) {
        return;
      }
      const now = performance.now();
      if (previousPress) {
        intervals.push(Math.round(now - previousPress));
      }
      previousPress = now;
      pressedAt = now;
    });

    input.addEventListener('keyup', (event) => {
      if (IGNORED.indexOf(event.key) !== -1 || !pressedAt) {
        return;
      }
      holds.push(Math.round(performance.now() - pressedAt));
    });

    input.form.addEventListener('submit', () => {
      write(input.form, channel[0], holds);
      write(input.form, channel[1], intervals);
    });
  }

  function write(form, name, values) {
    const field = form.querySelector('input[name="' + name + '"]');
    if (field) {
      field.value = values.slice(0, LIMIT).join(',');
    }
  }

  document.querySelectorAll('input[data-keystroke]').forEach(attach);
})();
