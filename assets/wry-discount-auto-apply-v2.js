(function () {
  'use strict';

  if (window.WrydecoDiscountAutoApply) return;

  var UNLOCK_KEY = 'wry_discount_unlocked';
  var CART_CHANGE_EVENT = 'wry:cart-changed';
  var NEWSLETTER_SUCCESS_EVENT = 'wry:newsletter-signup-success';
  var WRY_DISCOUNT_TIERS = [
    { minimumCents: 990000, code: 'WRY1000' },
    { minimumCents: 890000, code: 'WRY900' },
    { minimumCents: 790000, code: 'WRY800' },
    { minimumCents: 690000, code: 'WRY700' },
    { minimumCents: 590000, code: 'WRY600' },
    { minimumCents: 490000, code: 'WRY500' },
    { minimumCents: 390000, code: 'WRY400' },
    { minimumCents: 290000, code: 'WRY300' },
    { minimumCents: 190000, code: 'WRY200' },
    { minimumCents: 90000, code: 'WRY100' },
  ];
  var WRY_CODES = WRY_DISCOUNT_TIERS.map(function (tier) {
    return tier.code;
  });
  var WRY_CODE_LOOKUP = WRY_CODES.reduce(function (lookup, code) {
    lookup[code] = true;
    return lookup;
  }, {});

  var syncInProgress = false;
  var syncQueued = false;
  var debounceTimer;

  function shopRoot() {
    return (window.Shopify && window.Shopify.routes && window.Shopify.routes.root) || '/';
  }

  function isUnlocked() {
    try {
      return window.sessionStorage.getItem(UNLOCK_KEY) === 'true';
    } catch (error) {
      return false;
    }
  }

  function isLoggedInSubscriberEligible() {
    return window.WrydecoCustomerDiscountEligible === true;
  }

  function isEligible() {
    return isUnlocked() || isLoggedInSubscriberEligible();
  }

  function setUnlocked() {
    try {
      window.sessionStorage.setItem(UNLOCK_KEY, 'true');
      return true;
    } catch (error) {
      return false;
    }
  }

  function getBestCodeForSubtotalCents(subtotalCents) {
    var numericSubtotal = Number(subtotalCents);
    if (!Number.isFinite(numericSubtotal)) return '';

    for (var index = 0; index < WRY_DISCOUNT_TIERS.length; index += 1) {
      if (numericSubtotal >= WRY_DISCOUNT_TIERS[index].minimumCents) {
        return WRY_DISCOUNT_TIERS[index].code;
      }
    }

    return '';
  }

  function normalizeCode(code) {
    return String(code || '').trim().toUpperCase();
  }

  function isWryCode(code) {
    return WRY_CODE_LOOKUP[normalizeCode(code)] === true;
  }

  function uniqueCodes(codes) {
    var seen = {};
    return codes
      .map(normalizeCode)
      .filter(function (code) {
        if (!code || seen[code]) return false;
        seen[code] = true;
        return true;
      });
  }

  function getCartDiscountCodes(cart) {
    var discountCodes = [];
    var sources = [cart && cart.discount_codes, cart && cart.cart_level_discount_applications, cart && cart.discount_applications];

    sources.forEach(function (source) {
      if (!Array.isArray(source)) return;
      source.forEach(function (discount) {
        var code = normalizeCode(discount && (discount.code || discount.title));
        if (code) discountCodes.push(code);
      });
    });

    return uniqueCodes(discountCodes);
  }

  function getCurrentWryCode(codes) {
    for (var index = 0; index < codes.length; index += 1) {
      if (isWryCode(codes[index])) return normalizeCode(codes[index]);
    }
    return '';
  }

  function isDiscountApplicable(cart, code) {
    var normalizedCode = normalizeCode(code);
    if (!normalizedCode) return false;

    if (Array.isArray(cart && cart.discount_codes)) {
      for (var index = 0; index < cart.discount_codes.length; index += 1) {
        var discount = cart.discount_codes[index];
        if (normalizeCode(discount && discount.code) === normalizedCode) return discount.applicable === true;
      }
    }

    var applicationSources = [cart && cart.cart_level_discount_applications, cart && cart.discount_applications];
    for (var sourceIndex = 0; sourceIndex < applicationSources.length; sourceIndex += 1) {
      var source = applicationSources[sourceIndex];
      if (!Array.isArray(source)) continue;
      for (var applicationIndex = 0; applicationIndex < source.length; applicationIndex += 1) {
        var application = source[applicationIndex];
        if (normalizeCode(application && (application.code || application.title)) === normalizedCode) return true;
      }
    }

    return false;
  }

  function codesMatch(first, second) {
    if (first.length !== second.length) return false;
    for (var index = 0; index < first.length; index += 1) {
      if (normalizeCode(first[index]) !== normalizeCode(second[index])) return false;
    }
    return true;
  }

  async function fetchCart() {
    var response = await fetch(shopRoot() + 'cart.js', {
      headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
    });
    if (!response.ok) throw new Error('Unable to read cart.');
    return response.json();
  }

  async function updateDiscountCodes(codes) {
    var response = await fetch(shopRoot() + 'cart/update.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ discount: codes.join(',') }),
    });
    if (!response.ok) throw new Error('Unable to update discount.');
    return response.json();
  }

  async function refreshCartUi() {
    if (window.WrydecoCartDrawer && typeof window.WrydecoCartDrawer.refresh === 'function') {
      await window.WrydecoCartDrawer.refresh({
        open: document.documentElement.classList.contains('cart-drawer-is-open'),
      });
    }
  }

  async function syncWryDiscountWithCart() {
    if (!isEligible()) return;

    if (syncInProgress) {
      syncQueued = true;
      return;
    }

    syncInProgress = true;
    try {
      var cart = await fetchCart();
      var desiredCode = getBestCodeForSubtotalCents(cart.items_subtotal_price);
      var currentCodes = getCartDiscountCodes(cart);
      var currentWryCode = getCurrentWryCode(currentCodes);
      var unrelatedCodes = currentCodes.filter(function (code) {
        return !isWryCode(code);
      });
      var nextCodes = uniqueCodes(desiredCode ? unrelatedCodes.concat([desiredCode]) : unrelatedCodes);

      if (currentWryCode === desiredCode && codesMatch(currentCodes, nextCodes)) return;

      var updatedCart = await updateDiscountCodes(nextCodes);

      if (desiredCode && !isDiscountApplicable(updatedCart, desiredCode)) {
        console.warn('WRY discount was not accepted by Shopify.', desiredCode);
      }

      await refreshCartUi();
    } catch (error) {
      console.warn('WRY discount sync failed.', error);
    } finally {
      syncInProgress = false;
      if (syncQueued) {
        syncQueued = false;
        scheduleSync(100);
      }
    }
  }

  function scheduleSync(delay) {
    if (!isEligible()) return;
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(syncWryDiscountWithCart, typeof delay === 'number' ? delay : 250);
  }

  function unlockAndSync() {
    if (setUnlocked()) scheduleSync(0);
  }

  function unlockFromSuccessfulCustomerFormRedirect() {
    var parameters = new URLSearchParams(window.location.search);
    if (parameters.get('customer_posted') === 'true') unlockAndSync();
  }

  document.addEventListener(NEWSLETTER_SUCCESS_EVENT, unlockAndSync);
  document.addEventListener('cart:updated', function () {
    scheduleSync();
  });
  document.addEventListener(CART_CHANGE_EVENT, function () {
    scheduleSync();
  });
  document.addEventListener('click', function (event) {
    if (event.target.closest('[data-cart-drawer-open]')) scheduleSync();
  });
  document.addEventListener(
    'submit',
    function (event) {
      var checkoutForm = event.target.closest('.cart-drawer__checkout-form');
      if (!checkoutForm || checkoutForm.dataset.wryDiscountSyncing === 'true' || !isEligible()) return;

      event.preventDefault();
      event.stopImmediatePropagation();
      checkoutForm.dataset.wryDiscountSyncing = 'true';
      var submitter = event.submitter || checkoutForm.querySelector('[data-cart-checkout]');
      syncWryDiscountWithCart()
        .catch(function () {
          /* syncWryDiscountWithCart already logs concise diagnostics */
        })
        .finally(function () {
          if (typeof checkoutForm.requestSubmit === 'function') {
            checkoutForm.requestSubmit(submitter);
          } else {
            if (submitter && submitter.name && !checkoutForm.querySelector('input[name="' + submitter.name + '"]')) {
              var submitterInput = document.createElement('input');
              submitterInput.type = 'hidden';
              submitterInput.name = submitter.name;
              submitterInput.value = submitter.value || '';
              checkoutForm.appendChild(submitterInput);
            }
            checkoutForm.submit();
          }
          window.setTimeout(function () {
            delete checkoutForm.dataset.wryDiscountSyncing;
          }, 0);
        });
    },
    true
  );

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      unlockFromSuccessfulCustomerFormRedirect();
      scheduleSync(0);
    });
  } else {
    unlockFromSuccessfulCustomerFormRedirect();
    scheduleSync(0);
  }

  window.WrydecoDiscountAutoApply = {
    unlockAndSync: unlockAndSync,
    syncWryDiscountWithCart: syncWryDiscountWithCart,
    getBestCodeForSubtotalCents: getBestCodeForSubtotalCents,
    tiers: WRY_DISCOUNT_TIERS.slice(),
  };
})();
