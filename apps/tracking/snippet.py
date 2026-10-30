"""
The script a customer puts on their own website.

Phase 1 serves popups only. The popup configuration is baked into the script
body rather than fetched, which is why this feature needs no CORS at all: a
`<script src>` is not subject to it, and the form inside the popup is an iframe
on our own origin, so its submission is same-origin too. The project's CORS
setup is a single global allowlist with `CORS_ALLOW_CREDENTIALS = True`, and
not having to touch it is worth a short cache window on config changes.

The script is deliberately one hand-written IIFE with no build step. It is
~250 lines; a tracker this size is not worth a bundler, and a customer who
loads it on every page of their marketing site should not pay for one.
"""
import json

from django.conf import settings

# Long enough that a page view rarely pays for the lookup, short enough that a
# marketer who changes a trigger sees it the same morning.
CACHE_SECONDS = 300


def build_config(organization, forms, *, form_origin):
    """The JSON object inlined into the script."""
    return {
        'origin': form_origin.rstrip('/'),
        'popups': [
            {
                'id': str(form.id),
                'type': form.form_type,
                'rules': form.display_rules or {},
            }
            for form in forms
        ],
    }


def render(config):
    """The script body, with `config` inlined."""
    # json.dumps escapes the quotes; `</script>` cannot appear because the only
    # strings here are uuids, a form type from a fixed choice list, and the
    # display-rules blob, whose string values are authored in our own UI. The
    # `<` escape is belt-and-braces for the day one of those becomes free text.
    payload = json.dumps(config, separators=(',', ':')).replace('<', '\\u003c')
    return SCRIPT.replace('__MAILFLOW_CONFIG__', payload)


SCRIPT = r"""(function () {
  'use strict';

  var CONFIG = __MAILFLOW_CONFIG__;
  if (!CONFIG || !CONFIG.popups || !CONFIG.popups.length) return;

  var STORE_PREFIX = 'mf_popup_';

  /* Storage can throw -- Safari private mode historically did, and a blocked
     storage-access context still does. A popup must never break the page it
     is on, so every access is guarded and falls back to showing nothing
     rather than throwing into the host page. */
  function remembered(key) {
    try { return window.localStorage.getItem(STORE_PREFIX + key); }
    catch (e) { return null; }
  }
  function remember(key, value) {
    try { window.localStorage.setItem(STORE_PREFIX + key, value); }
    catch (e) { /* nothing to do; the popup shows again next time */ }
  }

  function suppressed(popup) {
    var rules = popup.rules || {};
    var mark = remembered(popup.id);
    if (!mark) return false;
    if (rules.showOnce) return true;
    var days = Number(rules.cooldownDays || 0);
    if (!days) return false;
    return (Date.now() - Number(mark)) < days * 86400000;
  }

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

  function isMobile() {
    return window.matchMedia('(max-width: 639px)').matches;
  }

  function targeted(popup) {
    var rules = popup.rules || {};
    var devices = rules.devices || ['desktop', 'mobile'];
    if (devices.indexOf(isMobile() ? 'mobile' : 'desktop') === -1) return false;
    if ((rules.excludeUrls || []).length && urlMatches(rules.excludeUrls)) return false;
    if ((rules.includeUrls || []).length && !urlMatches(rules.includeUrls)) return false;
    return true;
  }

  /* ------------------------------------------------------------- rendering */

  function overlayStyle(rules) {
    var o = rules.overlay || {};
    var position = rules.position || 'center';
    var width = o.width || '420px';
    var base =
      'position:fixed;z-index:2147483646;box-sizing:border-box;' +
      'opacity:0;transition:opacity .22s ease, transform .22s ease;';

    if (isMobile()) {
      /* dvh, not vh: vh is wrong while the iOS URL bar collapses, and a
         fixed-height centred modal puts the submit button behind the
         keyboard. A bottom sheet with its own scroll avoids both. */
      return base +
        'left:0;right:0;bottom:0;width:100%;max-height:88dvh;' +
        'transform:translateY(12px);';
    }
    var corner = {
      center: 'top:50%;left:50%;transform:translate(-50%,-50%) scale(.98);',
      bottom_right: 'right:24px;bottom:24px;transform:translateY(12px);',
      bottom_left: 'left:24px;bottom:24px;transform:translateY(12px);',
      top: 'top:24px;left:50%;transform:translate(-50%,-12px);'
    }[position] || 'top:50%;left:50%;transform:translate(-50%,-50%) scale(.98);';

    return base + corner + 'width:' + width + ';max-width:92vw;max-height:85vh;';
  }

  function shownTransform(rules) {
    if (isMobile()) return 'translateY(0)';
    var position = rules.position || 'center';
    if (position === 'center') return 'translate(-50%,-50%) scale(1)';
    if (position === 'top') return 'translate(-50%,0)';
    return 'translateY(0)';
  }

  function build(popup) {
    var rules = popup.rules || {};
    var o = rules.overlay || {};
    var radius = isMobile() ? '16px 16px 0 0' : (o.borderRadius || '12px');

    var backdrop = null;
    if (o.backdrop !== false) {
      backdrop = document.createElement('div');
      backdrop.setAttribute('style',
        'position:fixed;inset:0;z-index:2147483645;opacity:0;' +
        'transition:opacity .22s ease;background:' +
        (o.backdropColor || 'rgba(15, 23, 42, 0.55)') + ';');
      backdrop.addEventListener('click', function () { close(popup); });
      document.body.appendChild(backdrop);
    }

    var shell = document.createElement('div');
    shell.setAttribute('role', 'dialog');
    shell.setAttribute('aria-modal', 'true');
    shell.setAttribute('aria-label', 'Sign-up form');
    /* The radius lives on the wrapper, not the iframe: a border-radius on an
       iframe is unreliable in older WebKit. */
    shell.setAttribute('style', overlayStyle(rules) +
      'background:#fff;border-radius:' + radius + ';overflow:hidden;' +
      'box-shadow:0 24px 60px rgba(15,23,42,.28);');

    var close_ = document.createElement('button');
    close_.setAttribute('aria-label', 'Close');
    close_.innerHTML = '&times;';
    close_.setAttribute('style',
      'position:absolute;top:8px;right:10px;z-index:2;cursor:pointer;' +
      'border:0;background:transparent;font-size:26px;line-height:1;' +
      'color:#64748b;padding:4px 8px;');
    close_.addEventListener('click', function () { close(popup); });

    var frame = document.createElement('iframe');
    frame.src = CONFIG.origin + '/f/' + popup.id + '?embed=1';
    frame.setAttribute('title', 'Sign-up form');
    frame.setAttribute('loading', 'lazy');
    /* A fixed height with the iframe scrolling internally. Negotiating height
       over postMessage means resize -> message -> parent sets height ->
       content reflows -> resize again, which is the usual source of jank in
       embedded widgets, and buys nothing here. */
    frame.setAttribute('style',
      'display:block;border:0;width:100%;height:' +
      (isMobile() ? '72dvh' : '460px') + ';');

    shell.appendChild(close_);
    shell.appendChild(frame);
    document.body.appendChild(shell);

    requestAnimationFrame(function () {
      if (backdrop) backdrop.style.opacity = '1';
      shell.style.opacity = '1';
      shell.style.transform = shownTransform(rules);
    });

    popup._nodes = [shell, backdrop];
    return shell;
  }

  function close(popup) {
    remember(popup.id, String(Date.now()));
    (popup._nodes || []).forEach(function (node) {
      if (!node) return;
      node.style.opacity = '0';
      setTimeout(function () {
        if (node.parentNode) node.parentNode.removeChild(node);
      }, 240);
    });
    popup._nodes = null;
    popup._open = false;
    document.removeEventListener('keydown', popup._onKey);
  }

  function show(popup) {
    if (popup._open || suppressed(popup)) return;
    popup._open = true;
    build(popup);
    popup._onKey = function (e) { if (e.key === 'Escape') close(popup); };
    document.addEventListener('keydown', popup._onKey);
  }

  /* --------------------------------------------------------------- triggers */

  function arm(popup) {
    var rules = popup.rules || {};
    var trigger = rules.trigger || 'time';
    var fire = function () { show(popup); };

    if (trigger === 'scroll') {
      var wanted = Number(rules.scrollPercent || 50);
      var onScroll = function () {
        var doc = document.documentElement;
        var scrollable = doc.scrollHeight - window.innerHeight;
        var percent = scrollable > 0
          ? (window.scrollY / scrollable) * 100
          : 100;
        if (percent >= wanted) {
          window.removeEventListener('scroll', onScroll);
          fire();
        }
      };
      window.addEventListener('scroll', onScroll, { passive: true });
      onScroll();
      return;
    }

    if (trigger === 'click') {
      var selector = String(rules.clickSelector || '').trim();
      if (!selector) return;
      document.addEventListener('click', function (e) {
        var target = e.target;
        /* closest() so a click on an icon inside the button still counts. */
        if (target && target.closest && target.closest(selector)) {
          e.preventDefault();
          fire();
        }
      });
      return;
    }

    if (trigger === 'exit_intent') {
      /* No mobile equivalent exists, so touch devices fall back to the timer
         rather than never seeing the popup at all. */
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

  /* The form posts its own result up; the parent owns navigation, because a
     redirect inside the iframe would render the customer's thank-you page
     inside a 400px modal. */
  window.addEventListener('message', function (e) {
    if (e.origin !== CONFIG.origin) return;
    var data = e.data || {};
    if (data.source !== 'mailflow-form') return;

    var popup = null;
    for (var i = 0; i < CONFIG.popups.length; i++) {
      if (CONFIG.popups[i].id === data.formId) popup = CONFIG.popups[i];
    }
    if (!popup) return;

    if (data.type === 'submitted') {
      remember(popup.id, String(Date.now()));
      if (data.redirectUrl) {
        window.location.href = data.redirectUrl;
      } else {
        setTimeout(function () { close(popup); }, 2200);
      }
    } else if (data.type === 'close') {
      close(popup);
    }
  });

  function start() {
    CONFIG.popups.forEach(function (popup) {
      if (!targeted(popup) || suppressed(popup)) return;
      arm(popup);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
"""
