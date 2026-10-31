"""
The pop-up half of the website script.

Kept separate from tracker.js-the-string because together they are past the
point where one file is readable. They are still served as one response: a
customer should install one tag, not two.

The popup draws its own content -- title, image, buttons -- and only reaches
for an iframe when there is a form to render, because that is the one part
worth reusing the application for. An announcement with no form never loads it.
"""

POPUP_JS = r"""
  /* ---------------------------------------------------------------- popups */

  var SESSION_KEY = 'mf_popup_session';
  var PAGES_KEY = 'mf_pages';

  function sessionMark(id) {
    try { return window.sessionStorage.getItem(SESSION_KEY + id); }
    catch (e) { return null; }
  }
  function markSession(id) {
    try { window.sessionStorage.setItem(SESSION_KEY + id, '1'); } catch (e) {}
  }

  function pagesThisVisit() {
    var n = 0;
    try { n = Number(window.sessionStorage.getItem(PAGES_KEY) || 0); } catch (e) {}
    return n;
  }
  function countPage() {
    try {
      window.sessionStorage.setItem(PAGES_KEY, String(pagesThisVisit() + 1));
    } catch (e) {}
  }

  function suppressed(popup) {
    var freq = popup.frequency || {};
    var mode = freq.mode || 'once_per_visitor';
    if (mode === 'every_visit') return false;
    if (mode === 'once_per_session') return !!sessionMark(popup.id);

    var mark = remembered(popup.id);
    if (!mark) return false;
    if (mode === 'once_per_visitor') return true;
    var days = Number(freq.days || 0);
    if (!days) return false;
    return (Date.now() - Number(mark)) < days * 86400000;
  }

  /* ------------------------------------------------------------- targeting */

  function urlMatches(patterns) {
    var here = window.location.pathname + window.location.search;
    for (var i = 0; i < patterns.length; i++) {
      var p = String(patterns[i] || '').trim();
      if (!p) continue;
      /* A trailing * is the only wildcard. Anything richer is a regex in a
         text box, which customers get wrong and we then have to debug. */
      if (p.slice(-1) === '*') {
        if (here.indexOf(p.slice(0, -1)) === 0) return true;
      } else if (here === p) {
        return true;
      }
    }
    return false;
  }

  function utmParams() {
    var out = {};
    try {
      var params = new URLSearchParams(window.location.search);
      params.forEach(function (value, key) {
        if (key.indexOf('utm_') === 0) out[key] = value;
      });
      /* Remembered for the visit: the campaign that brought someone in still
         describes them on the third page, where the query string is gone. */
      if (Object.keys(out).length) {
        window.sessionStorage.setItem('mf_utm', JSON.stringify(out));
      } else {
        out = JSON.parse(window.sessionStorage.getItem('mf_utm') || '{}');
      }
    } catch (e) {}
    return out;
  }

  function targeted(popup) {
    var rules = popup.targeting || {};

    var devices = rules.devices || ['desktop', 'mobile'];
    if (devices.indexOf(isMobile() ? 'mobile' : 'desktop') === -1) return false;

    if ((rules.excludeUrls || []).length && urlMatches(rules.excludeUrls)) return false;
    if ((rules.includeUrls || []).length && !urlMatches(rules.includeUrls)) return false;

    var visitorType = rules.visitorType || 'any';
    if (visitorType !== 'any') {
      var returning = !!remembered('seen');
      if (visitorType === 'new' && returning) return false;
      if (visitorType === 'returning' && !returning) return false;
    }

    var referrers = rules.referrers || [];
    if (referrers.length) {
      var from = (document.referrer || '').toLowerCase();
      var hit = false;
      for (var i = 0; i < referrers.length; i++) {
        if (from.indexOf(String(referrers[i]).toLowerCase()) !== -1) hit = true;
      }
      if (!hit) return false;
    }

    var wantedUtm = rules.utm || {};
    var keys = Object.keys(wantedUtm);
    if (keys.length) {
      var actual = utmParams();
      for (var k = 0; k < keys.length; k++) {
        if ((actual[keys[k]] || '') !== wantedUtm[keys[k]]) return false;
      }
    }

    return true;
  }

  /* Rules the browser cannot answer on its own. Resolved once per page by a
     single call, and only when some popup actually asks. */
  function needsAudience() {
    for (var i = 0; i < CONFIG.popups.length; i++) {
      var rules = CONFIG.popups[i].targeting || {};
      if (rules.country && rules.country.length) return true;
      var audience = rules.audience || {};
      if ((audience.segments || []).length) return true;
      if ((audience.tags || []).length) return true;
      if ((audience.contactFields || []).length) return true;
    }
    return false;
  }

  function audienceAllows(popup, audience) {
    var rules = popup.targeting || {};

    if (rules.country && rules.country.length) {
      /* Unknown location fails the rule rather than passing it: an
         Ireland-only offer shown to the world is worse than one nobody
         sees. */
      if (!audience || !audience.country) return false;
      if (rules.country.indexOf(audience.country) === -1) return false;
    }

    var wanted = rules.audience || {};
    if (!wanted.segments && !wanted.tags && !wanted.contactFields) return true;
    if (!audience || !audience.known) {
      /* Targeting a contact property only makes sense for someone we can
         name, and most visitors are nobody yet. */
      return false;
    }

    var segments = wanted.segments || [];
    for (var i = 0; i < segments.length; i++) {
      if (!(audience.segments || {})[segments[i]]) return false;
    }
    var tags = wanted.tags || [];
    for (var t = 0; t < tags.length; t++) {
      if (!(audience.tags || {})[tags[t]]) return false;
    }
    var fields = wanted.contactFields || [];
    for (var f = 0; f < fields.length; f++) {
      var rule = fields[f];
      var key = rule.field + ':' + (rule.operator || 'is_not_empty') + ':' +
        (rule.value === undefined ? '' : rule.value);
      if (!(audience.fields || {})[key]) return false;
    }
    return true;
  }

  /* --------------------------------------------------------------- drawing */

  function placement(popup) {
    var design = popup.design || {};
    var kind = popup.type;

    if (kind === 'floating_bar') {
      return (design.position === 'bottom'
        ? 'left:0;right:0;bottom:0;'
        : 'left:0;right:0;top:0;') + 'width:100%;';
    }
    if (kind === 'full_screen') {
      return 'inset:0;width:100%;height:100%;display:flex;' +
        'align-items:center;justify-content:center;';
    }
    if (isMobile()) {
      /* dvh, not vh: vh is wrong while the iOS URL bar collapses, and a
         centred box sits behind the keyboard. */
      return 'left:0;right:0;bottom:0;width:100%;max-height:88dvh;';
    }
    var width = design.maxWidth || '440px';
    var spot = {
      center: 'top:50%;left:50%;transform:translate(-50%,-50%);',
      bottom_right: 'right:24px;bottom:24px;',
      bottom_left: 'left:24px;bottom:24px;',
      top: 'top:24px;left:50%;transform:translate(-50%,0);'
    }[design.position || 'center'];
    return spot + 'width:' + width + ';max-width:92vw;max-height:85vh;';
  }

  function el(tag, style, text) {
    var node = document.createElement(tag);
    if (style) node.setAttribute('style', style);
    if (text) node.textContent = text;
    return node;
  }

  function build(popup) {
    var design = popup.design || {};
    var content = popup.content || {};
    var bar = popup.type === 'floating_bar';
    var full = popup.type === 'full_screen';
    var radius = bar || full ? '0' : (isMobile() ? '16px 16px 0 0' : design.borderRadius || '12px');

    var backdrop = null;
    if (design.backdrop !== false && !bar) {
      backdrop = el('div',
        'position:fixed;inset:0;z-index:2147483645;opacity:0;' +
        'transition:opacity .22s ease;background:' +
        (design.backdropColor || 'rgba(15, 23, 42, 0.55)') + ';');
      backdrop.addEventListener('click', function () { dismiss(popup); });
      document.body.appendChild(backdrop);
    }

    var shell = el('div',
      'position:fixed;z-index:2147483646;box-sizing:border-box;opacity:0;' +
      'transition:opacity .22s ease, transform .22s ease;' +
      placement(popup) +
      'background:' + (design.backgroundColor || '#ffffff') + ';' +
      'color:' + (design.textColor || '#0f172a') + ';' +
      'font-family:' + (design.fontFamily || 'system-ui, sans-serif') + ';' +
      'border-radius:' + radius + ';overflow:auto;' +
      'box-shadow:0 24px 60px rgba(15,23,42,.28);');
    shell.setAttribute('role', 'dialog');
    shell.setAttribute('aria-modal', full || !bar ? 'true' : 'false');
    shell.setAttribute('aria-label', content.title || 'Message');

    var inner = el('div', bar
      ? 'display:flex;align-items:center;gap:16px;padding:' + (design.padding || '12px 20px') + ';'
      : 'padding:' + (design.padding || '28px') + ';max-width:' +
        (full ? '520px' : '100%') + ';margin:0 auto;');

    if (content.imageUrl && !bar && (design.image || {}).position !== 'none') {
      var img = el('img',
        'display:block;width:100%;object-fit:cover;border-radius:8px;' +
        'margin-bottom:14px;height:' + ((design.image || {}).height || '160px') + ';');
      img.src = content.imageUrl;
      img.alt = content.imageAlt || '';
      inner.appendChild(img);
    }

    var textWrap = el('div', bar ? 'flex:1;min-width:0;' : '');
    if (content.title) {
      textWrap.appendChild(el('p',
        'margin:0;font-size:' + (bar ? '14px' : '19px') + ';font-weight:700;' +
        'line-height:1.3;color:' + (design.headingColor || design.textColor || '#0f172a') + ';',
        content.title));
    }
    if (content.description && !bar) {
      textWrap.appendChild(el('p',
        'margin:8px 0 0;font-size:14px;line-height:1.55;opacity:.85;',
        content.description));
    }
    inner.appendChild(textWrap);

    if (popup.formId) {
      /* The one place the application is worth loading: the form renders
         itself, with its own fields, conditional logic and validation. */
      var frame = document.createElement('iframe');
      frame.src = CONFIG.origin + '/f/' + popup.formId + '?embed=1&popup=' + popup.id;
      frame.setAttribute('title', 'Form');
      frame.setAttribute('style',
        'display:block;border:0;width:100%;margin-top:14px;height:' +
        (isMobile() ? '60dvh' : '320px') + ';');
      inner.appendChild(frame);
    } else if (content.ctaText) {
      var button = el('a',
        'display:inline-block;margin-top:' + (bar ? '0' : '18px') + ';' +
        'padding:11px 20px;text-decoration:none;font-size:14px;font-weight:600;' +
        'cursor:pointer;white-space:nowrap;' +
        'background:' + ((design.primaryButton || {}).backgroundColor || '#4f46e5') + ';' +
        'color:' + ((design.primaryButton || {}).textColor || '#ffffff') + ';' +
        'border-radius:' + ((design.primaryButton || {}).borderRadius || '8px') + ';' +
        ((design.primaryButton || {}).fullWidth && !bar ? 'width:100%;text-align:center;' : ''),
        content.ctaText);
      if (content.ctaUrl) button.href = content.ctaUrl;
      button.addEventListener('click', function () {
        record(popup, 'popup_clicked');
        remember(popup.id, String(Date.now()));
        markSession(popup.id);
      });
      inner.appendChild(button);
    }

    shell.appendChild(inner);

    var close = (design.closeButton || {});
    if (close.show !== false) {
      var button2 = el('button',
        'position:absolute;top:8px;right:10px;z-index:2;cursor:pointer;border:0;' +
        'background:transparent;font-size:26px;line-height:1;padding:4px 8px;' +
        'color:' + (close.color || '#64748b') + ';' +
        (close.delaySeconds ? 'display:none;' : ''));
      button2.setAttribute('aria-label', 'Close');
      button2.innerHTML = '&times;';
      button2.addEventListener('click', function () { dismiss(popup); });
      shell.style.position = 'fixed';
      shell.appendChild(button2);
      if (close.delaySeconds) {
        setTimeout(function () { button2.style.display = 'block'; },
          Number(close.delaySeconds) * 1000);
      }
    }

    document.body.appendChild(shell);
    requestAnimationFrame(function () {
      if (backdrop) backdrop.style.opacity = '1';
      shell.style.opacity = '1';
    });

    popup._nodes = [shell, backdrop];
  }

  function teardown(popup) {
    (popup._nodes || []).forEach(function (node) {
      if (!node) return;
      node.style.opacity = '0';
      setTimeout(function () {
        if (node.parentNode) node.parentNode.removeChild(node);
      }, 240);
    });
    popup._nodes = null;
    popup._open = false;
    if (popup._onKey) document.removeEventListener('keydown', popup._onKey);
  }

  function dismiss(popup) {
    if (!popup._open) return;
    record(popup, 'popup_dismissed');
    remember(popup.id, String(Date.now()));
    markSession(popup.id);
    teardown(popup);
  }

  function show(popup) {
    if (popup._open || suppressed(popup)) return;
    popup._open = true;
    build(popup);
    record(popup, 'popup_shown');
    /* Escape always closes, even when the close button is hidden. A popup
       nobody can dismiss is how a site gets reported. */
    popup._onKey = function (e) { if (e.key === 'Escape') dismiss(popup); };
    document.addEventListener('keydown', popup._onKey);
  }

  /* -------------------------------------------------------------- triggers */

  function arm(popup) {
    var rules = popup.triggers || {};
    var kind = rules.type || 'time';
    var fire = function () { show(popup); };

    if (kind === 'scroll') {
      var wanted = Number(rules.scrollPercent || 50);
      var onScroll = function () {
        var doc = document.documentElement;
        var scrollable = doc.scrollHeight - window.innerHeight;
        var percent = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 100;
        if (percent >= wanted) {
          window.removeEventListener('scroll', onScroll);
          fire();
        }
      };
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
      return;
    }

    if (kind === 'page_visit') {
      if (pagesThisVisit() >= Number(rules.pageVisitCount || 2)) fire();
      return;
    }

    if (kind === 'inactivity') {
      var idle = Number(rules.inactivitySeconds || 30) * 1000;
      var timer = null;
      var reset = function () {
        if (timer) clearTimeout(timer);
        timer = setTimeout(fire, idle);
      };
      ['mousemove', 'keydown', 'scroll', 'touchstart'].forEach(function (name) {
        window.addEventListener(name, reset, { passive: true });
      });
      reset();
      return;
    }

    if (kind === 'click') {
      var selector = String(rules.clickSelector || '').trim();
      if (!selector) return;
      document.addEventListener('click', function (e) {
        var target = e.target;
        if (target && target.closest && target.closest(selector)) {
          e.preventDefault();
          fire();
        }
      });
      return;
    }

    if (kind === 'exit_intent') {
      /* No mobile equivalent exists, so touch devices fall back to the delay
         rather than never seeing it at all. */
      if (isMobile()) {
        setTimeout(fire, Number(rules.delaySeconds || 5) * 1000);
        return;
      }
      var onLeave = function (e) {
        if (e.clientY > 0) return;
        document.removeEventListener('mouseout', onLeave);
        fire();
      };
      document.addEventListener('mouseout', onLeave);
      return;
    }

    setTimeout(fire, Number(rules.delaySeconds || 5) * 1000);
  }

  function record(popup, type) {
    send([{ t: type, pu: popup.id, u: location.href.slice(0, 2000),
            p: (location.pathname + location.search).slice(0, 500),
            at: new Date().toISOString() }]);
  }

  /* The form inside a popup reports its own result; the parent owns
     navigation, because a redirect inside the iframe would render the
     customer's thank-you page inside a 400px box. */
  window.addEventListener('message', function (e) {
    if (e.origin !== CONFIG.origin) return;
    var data = e.data || {};
    if (data.source !== 'mailflow-form') return;

    var popup = null;
    for (var i = 0; i < CONFIG.popups.length; i++) {
      if (CONFIG.popups[i].formId === data.formId) popup = CONFIG.popups[i];
    }
    if (!popup) return;

    if (data.type === 'submitted') {
      remember(popup.id, String(Date.now()));
      markSession(popup.id);
      if (data.redirectUrl) {
        window.location.href = data.redirectUrl;
      } else {
        setTimeout(function () { teardown(popup); }, 2200);
      }
    } else if (data.type === 'close') {
      dismiss(popup);
    }
  });

  function startPopups(audience) {
    CONFIG.popups.forEach(function (popup) {
      if (!targeted(popup)) return;
      if (!audienceAllows(popup, audience)) return;
      if (suppressed(popup)) return;
      arm(popup);
    });
    /* Marked after the decisions above, so "new visitor" means new on this
       page rather than new until the first popup runs. */
    remember('seen', String(Date.now()));
  }
"""
