(function () {
  function postJSON(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {})
    }).then(function (r) { return r.json(); });
  }

  function refreshBadge() {
    fetch('/api/cart/count')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var badge = document.getElementById('cart-badge');
        if (badge) {
          badge.textContent = data.count;
          badge.style.display = data.count > 0 ? 'inline-block' : 'none';
        }
      })
      .catch(function () {});
  }

  function showToast(message, category) {
    var wrap = document.getElementById('toast-wrap');
    if (!wrap) return;
    var toast = document.createElement('div');
    toast.className = 'toast ' + (category || '');
    toast.textContent = message;
    wrap.appendChild(toast);
    setTimeout(function () {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.4s';
      setTimeout(function () { toast.remove(); }, 420);
    }, 3800);
  }
  window.showToast = showToast;

  document.querySelectorAll('.toast').forEach(function (t) {
    setTimeout(function () {
      t.style.opacity = '0';
      t.style.transition = 'opacity 0.4s';
      setTimeout(function () { t.remove(); }, 420);
    }, 4200);
  });

  document.querySelectorAll('.add-to-cart').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var id = btn.getAttribute('data-id');
      var label = btn.textContent;
      btn.textContent = 'Adding...';
      postJSON('/api/cart/add', { id: id })
        .then(function (data) {
          btn.textContent = label;
          if (data.ok) {
            refreshBadge();
            showToast('Added to cart.', 'ok');
          }
        })
        .catch(function () { btn.textContent = label; });
    });
  });

  document.querySelectorAll('.qty-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      postJSON('/api/cart/set', { id: btn.getAttribute('data-id'), qty: Number(btn.getAttribute('data-qty')) })
        .then(function () { window.location.reload(); });
    });
  });

  document.querySelectorAll('[data-toggle-password]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var input = document.getElementById(btn.getAttribute('data-toggle-password'));
      if (!input) return;
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.textContent = show ? 'Hide' : 'Show';
    });
  });

  document.querySelectorAll('input[type=password][data-holds]').forEach(function (input) {
    window.attachKeystroke(input, input.getAttribute('data-holds'), input.getAttribute('data-intervals'));
  });

  var strengthInput = document.querySelector('input[data-strength]');
  if (strengthInput) {
    var bar = document.getElementById('meter-bar');
    var feedback = document.getElementById('meter-feedback');
    var COLORS = ['#f87171', '#fb923c', '#fbbf24', '#a3e635', '#34d399'];
    var LABELS = ['Very weak', 'Weak', 'Fair', 'Strong', 'Excellent'];
    var pending = null;
    function refresh() {
      clearTimeout(pending);
      pending = setTimeout(function () {
        fetch('/api/strength?password=' + encodeURIComponent(strengthInput.value))
          .then(function (r) { return r.json(); })
          .then(function (res) {
            bar.style.width = ((res.score + 1) * 20) + '%';
            bar.style.background = COLORS[res.score];
            bar.title = LABELS[res.score] + ' ~' + res.entropy + ' bits';
            feedback.innerHTML = '';
            res.feedback.forEach(function (f) {
              var li = document.createElement('li');
              li.textContent = f;
              feedback.appendChild(li);
            });
          })
          .catch(function () {});
      }, 180);
    }
    strengthInput.addEventListener('input', refresh);
    refresh();
  }

  var chart = document.getElementById('audit-chart');
  if (chart) {
    var labels = JSON.parse(chart.getAttribute('data-labels') || '[]');
    var values = JSON.parse(chart.getAttribute('data-values') || '[]');
    var max = Math.max(1, Math.max.apply(null, values));
    var width = chart.parentElement.clientWidth || 800;
    var height = 160;
    chart.setAttribute('width', width);
    chart.setAttribute('height', height);
    var ctx = chart.getContext('2d');
    var pad = { top: 16, right: 10, bottom: 26, left: 10 };
    var n = values.length;
    var slot = (width - pad.left - pad.right) / n;
    var barW = Math.min(26, slot * 0.55);

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = '#8aa0c0';
    ctx.strokeStyle = '#233252';
    ctx.lineWidth = 1;
    ctx.font = '11px system-ui';

    for (var g = 0; g <= 4; g++) {
      var gy = pad.top + ((height - pad.top - pad.bottom) * g) / 4;
      ctx.beginPath();
      ctx.moveTo(pad.left, gy);
      ctx.lineTo(width - pad.right, gy);
      ctx.stroke();
    }

    for (var i = 0; i < n; i++) {
      var x = pad.left + slot * i + (slot - barW) / 2;
      var h = ((height - pad.top - pad.bottom) * values[i]) / max;
      var y = height - pad.bottom - h;
      var grad = ctx.createLinearGradient(0, y, 0, height - pad.bottom);
      grad.addColorStop(0, '#38bdf8');
      grad.addColorStop(1, '#818cf8');
      ctx.fillStyle = grad;
      ctx.fillRect(x, y, barW, h);
      ctx.fillStyle = '#8aa0c0';
      ctx.textAlign = 'center';
      if (i % 2 === 0 || n <= 8) ctx.fillText(labels[i], pad.left + slot * i + slot / 2, height - 10);
      ctx.fillStyle = '#8aa0c0';
      if (values[i] > 0) ctx.fillText(String(values[i]), pad.left + slot * i + slot / 2, Math.max(y - 4, 10));
    }
  }

  refreshBadge();
})();
