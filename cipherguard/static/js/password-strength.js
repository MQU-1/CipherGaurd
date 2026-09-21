(function () {
  const input = document.querySelector('input[data-strength]');
  if (!input) {
    return;
  }

  const meter = document.querySelector('[data-strength-meter]');
  const label = document.querySelector('[data-strength-label]');
  const advice = document.querySelector('[data-strength-advice]');
  let timer = null;

  function render(report) {
    if (meter) {
      meter.dataset.score = String(report.score);
    }
    if (label) {
      label.textContent = report.entropy ? report.label + ' · ' + report.entropy + ' bits' : '';
    }
    if (advice) {
      advice.textContent = report.advice.join(' ');
    }
  }

  function evaluate() {
    const value = input.value;
    if (!value) {
      render({ score: 0, label: '', entropy: 0, advice: [] });
      return;
    }
    fetch('/api/password-strength', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: value }),
    })
      .then((response) => response.json())
      .then(render)
      .catch(() => undefined);
  }

  input.addEventListener('input', () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(evaluate, 220);
  });
})();
