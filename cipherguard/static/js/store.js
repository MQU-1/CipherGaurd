(function () {
  const currency = document.documentElement.dataset.currency || 'USD';
  const formatter = new Intl.NumberFormat(undefined, { style: 'currency', currency: currency });
  const drawer = document.getElementById('cart-drawer');
  const badges = document.querySelectorAll('[data-cart-count]');
  const toastHost = document.getElementById('toasts');
  let lastFocus = null;

  function money(value) {
    return formatter.format(Number(value) || 0);
  }

  function request(url, options) {
    return fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' } }, options))
      .then((response) => {
        if (!response.ok) {
          throw new Error('request failed');
        }
        return response.json();
      });
  }

  function setCount(count) {
    badges.forEach((badge) => {
      badge.textContent = count;
      badge.dataset.empty = count === 0 ? 'true' : 'false';
    });
  }

  function toast(message, tone) {
    if (!toastHost) {
      return;
    }
    const node = document.createElement('div');
    node.className = 'toast toast--' + (tone || 'notice');
    node.setAttribute('role', 'status');
    node.innerHTML = '<span></span><button type="button" aria-label="Dismiss">&times;</button>';
    node.querySelector('span').textContent = message;
    node.querySelector('button').addEventListener('click', () => node.remove());
    toastHost.appendChild(node);
    window.setTimeout(() => node.remove(), 5200);
  }

  function lineMarkup(line) {
    const unit = line.kind === 'course' ? 'Seat' : money(line.price) + ' each';
    const controls = line.kind === 'course'
      ? '<span class="line-item__note">Lifetime access</span>'
      : '<div class="stepper" data-slug="' + line.slug + '" data-quantity="' + line.quantity + '">' +
        '<button type="button" data-step="-1" aria-label="Decrease">&minus;</button>' +
        '<output>' + line.quantity + '</output>' +
        '<button type="button" data-step="1" aria-label="Increase">+</button>' +
        '</div>';
    return '<div class="line-item">' +
      '<div class="line-item__thumb"><span class="mono">' + line.name.slice(0, 2).toUpperCase() + '</span></div>' +
      '<div><a class="line-item__name" href="' + line.url + '">' + line.name + '</a>' +
      '<div class="line-item__note">' + unit + '</div>' +
      '<div style="margin-top:10px">' + controls + '</div></div>' +
      '<div><div class="line-item__price">' + money(line.subtotal) + '</div>' +
      '<button class="line-item__remove" type="button" data-remove="' + line.slug + '">Remove</button></div>' +
      '</div>';
  }

  function paint(payload) {
    setCount(payload.count);
    if (!drawer) {
      return;
    }
    const body = drawer.querySelector('[data-drawer-body]');
    const foot = drawer.querySelector('[data-drawer-foot]');
    if (!payload.lines.length) {
      body.innerHTML = '<p class="muted" style="padding:40px 0">Your bag is empty.</p>';
      foot.hidden = true;
      return;
    }
    body.innerHTML = payload.lines.map(lineMarkup).join('');
    foot.hidden = false;
    foot.querySelector('[data-subtotal]').textContent = money(payload.subtotal);
    const shipping = foot.querySelector('[data-shipping]');
    shipping.textContent = payload.shipping ? money(payload.shipping) : 'Free';
    const gap = foot.querySelector('[data-gap]');
    if (payload.freeShippingGap > 0) {
      gap.hidden = false;
      gap.textContent = money(payload.freeShippingGap) + ' away from free delivery';
    } else {
      gap.hidden = true;
      gap.textContent = '';
    }
  }

  function refresh() {
    return request('/api/cart').then(paint);
  }

  function openDrawer() {
    if (!drawer) {
      return;
    }
    lastFocus = document.activeElement;
    drawer.dataset.open = 'true';
    document.body.style.overflow = 'hidden';
    const close = drawer.querySelector('[data-drawer-close]');
    if (close) {
      close.focus();
    }
  }

  function closeDrawer() {
    if (!drawer) {
      return;
    }
    drawer.dataset.open = 'false';
    document.body.style.overflow = '';
    if (lastFocus) {
      lastFocus.focus();
    }
  }

  function addToCart(trigger) {
    const slug = trigger.dataset.add;
    const quantity = Number(trigger.dataset.quantity || 1);
    trigger.disabled = true;
    request('/api/cart/items', { method: 'POST', body: JSON.stringify({ slug: slug, quantity: quantity }) })
      .then((payload) => {
        paint(payload);
        if (trigger.dataset.then === 'checkout') {
          window.location.assign('/checkout');
          return;
        }
        toast(payload.added + ' added to your bag.', 'success');
        openDrawer();
      })
      .catch(() => toast('That item could not be added.', 'error'))
      .finally(() => {
        trigger.disabled = false;
      });
  }

  function changeQuantity(stepper, delta) {
    const slug = stepper.dataset.slug;
    const next = Math.max(0, Number(stepper.dataset.quantity || 0) + delta);
    request('/api/cart/items/' + encodeURIComponent(slug), {
      method: 'PUT',
      body: JSON.stringify({ quantity: next }),
    }).then((payload) => {
      if (stepper.closest('[data-cart-page]')) {
        window.location.reload();
        return;
      }
      paint(payload);
    });
  }

  function removeLine(slug, inPage) {
    request('/api/cart/items/' + encodeURIComponent(slug), { method: 'DELETE' }).then((payload) => {
      if (inPage) {
        window.location.reload();
        return;
      }
      paint(payload);
      toast('Removed from your bag.', 'notice');
    });
  }

  document.addEventListener('click', (event) => {
    const add = event.target.closest('[data-add]');
    if (add) {
      event.preventDefault();
      addToCart(add);
      return;
    }

    const step = event.target.closest('[data-step]');
    if (step) {
      event.preventDefault();
      changeQuantity(step.closest('.stepper'), Number(step.dataset.step));
      return;
    }

    const remove = event.target.closest('[data-remove]');
    if (remove) {
      event.preventDefault();
      removeLine(remove.dataset.remove, Boolean(remove.closest('[data-cart-page]')));
      return;
    }

    if (event.target.closest('[data-drawer-open]')) {
      event.preventDefault();
      refresh().then(openDrawer);
      return;
    }

    if (event.target.closest('[data-drawer-close]') || event.target.closest('[data-drawer-veil]')) {
      event.preventDefault();
      closeDrawer();
      return;
    }

    const searchToggle = event.target.closest('[data-search-toggle]');
    if (searchToggle) {
      event.preventDefault();
      const panel = document.getElementById('search-panel');
      const open = panel.dataset.open !== 'true';
      panel.dataset.open = open ? 'true' : 'false';
      searchToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (open) {
        panel.querySelector('input').focus();
      }
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') {
      return;
    }
    const panel = document.getElementById('search-panel');
    if (panel && panel.dataset.open === 'true') {
      panel.dataset.open = 'false';
    }
    if (drawer && drawer.dataset.open === 'true') {
      closeDrawer();
    }
  });

  document.querySelectorAll('.toast button').forEach((button) => {
    button.addEventListener('click', () => button.parentElement.remove());
  });

  window.setTimeout(() => {
    document.querySelectorAll('#toasts .toast').forEach((node) => node.remove());
  }, 6000);
})();
