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

from .popup_js import POPUP_JS

# Long enough that a page view rarely pays for the lookup, short enough that a
# marketer who changes a trigger sees it the same morning.
CACHE_SECONDS = 300


def build_config(organization, popups, *, form_origin):
    """The JSON object inlined into the script."""
    return {
        'origin': form_origin.rstrip('/'),
        'key': str(organization.tracking_key),
        'track': organization.tracking_enabled,
        'requireConsent': organization.tracking_requires_consent,
        'popups': [_popup_config(popup) for popup in popups],
    }


def _popup_config(popup):
    """
    One popup, flattened for the browser.

    Only what the script needs to draw and decide. Notably absent: anything
    about who the visitor is, because this response is cached per
    organization and shared by every visitor to their site.
    """
    return {
        'id': str(popup.id),
        'type': popup.popup_type,
        'content': {
            'title': popup.title,
            'description': popup.description,
            'imageUrl': popup.image_url,
            'imageAlt': popup.image_alt,
            'ctaText': popup.cta_text,
            'ctaUrl': popup.cta_url,
            'secondaryCtaText': popup.secondary_cta_text,
            'secondaryCtaUrl': popup.secondary_cta_url,
        },
        # The form is rendered in an iframe by the existing public form route,
        # so the popup only needs to know whether there is one.
        'formId': str(popup.form_id) if popup.form_id else None,
        'design': popup.design or {},
        'triggers': popup.triggers or {},
        'targeting': popup.targeting or {},
        'frequency': popup.frequency or {},
    }


def render(config):
    """The script body, with `config` inlined."""
    # json.dumps escapes the quotes; `</script>` cannot appear because the only
    # strings here are uuids, a form type from a fixed choice list, and the
    # display-rules blob, whose string values are authored in our own UI. The
    # `<` escape is belt-and-braces for the day one of those becomes free text.
    payload = json.dumps(config, separators=(',', ':')).replace('<', '\\u003c')
    return (
        SCRIPT
        .replace('__POPUP_JS__', POPUP_JS)
        .replace('__MAILFLOW_CONFIG__', payload)
    )


SCRIPT = r"""(function () {
  'use strict';

  var CONFIG = __MAILFLOW_CONFIG__;
  if (!CONFIG) return;
  CONFIG.popups = CONFIG.popups || [];

  var STORE_PREFIX = 'mf_popup_';

  /* Storage can throw -- Safari private mode historically did, and a blocked
     storage-access context still does. Nothing here may break the page it is
     on, so every access is guarded. */
  function remembered(key) {
    try { return window.localStorage.getItem(STORE_PREFIX + key); }
    catch (e) { return null; }
  }
  function remember(key, value) {
    try { window.localStorage.setItem(STORE_PREFIX + key, value); } catch (e) {}
  }

  function isMobile() {
    return window.matchMedia('(max-width: 639px)').matches;
  }

  /* ------------------------------------------------------------- tracking */

  var VISITOR_KEY = 'mf_vid';

  /* The id lives in localStorage on the customer's own origin, so it is
     first-party. A cookie set by us would be third-party and is blocked by
     Safari and Firefox and going away in Chrome; a cookie on their domain is
     not ours to set. One store, one failure mode.

     Safari still purges script-writable storage on origins with no
     interaction for 7 days, so expect some visitors to return as new ones.
     No cookie strategy fixes that either. */
  function visitorId() {
    var id = null;
    try { id = window.localStorage.getItem(VISITOR_KEY); } catch (e) {}
    if (id) return id;
    id = (window.crypto && window.crypto.randomUUID)
      ? window.crypto.randomUUID()
      : 'v' + Date.now() + Math.random().toString(36).slice(2, 10);
    try { window.localStorage.setItem(VISITOR_KEY, id); } catch (e) {}
    return id;
  }

  function consented() {
    if (!CONFIG.requireConsent) return true;
    /* The customer's own banner sets this. We do not draw one for them. */
    return window.__mfConsent === true;
  }

  function send(events) {
    if (!CONFIG.key || !events.length || !consented()) return;
    var body = JSON.stringify({ k: CONFIG.key, vid: visitorId(), e: events });
    var url = CONFIG.origin + '/track/collect';
    try {
      /* text/plain keeps this a *simple* request: no preflight, no CORS. And
         sendBeacon survives the page unloading, which fetch does not. */
      var blob = new Blob([body], { type: 'text/plain;charset=UTF-8' });
      if (navigator.sendBeacon && navigator.sendBeacon(url, blob)) return;
    } catch (e) {}
    try {
      fetch(url, {
        method: 'POST', body: body, keepalive: true,
        credentials: 'omit', mode: 'no-cors',
        headers: { 'Content-Type': 'text/plain;charset=UTF-8' }
      });
    } catch (e) {}
  }

  function pageview() {
    /* A headless browser taking a screenshot is not a visitor, and a
       prerendered page was never seen. Two cheap checks catch most of it;
       user-agent blocklists are a time sink with a bad hit rate. */
    if (navigator.webdriver) return;
    if (document.visibilityState === 'prerender') return;
    send([{
      t: 'pageview',
      u: location.href.slice(0, 2000),
      p: (location.pathname + location.search).slice(0, 500),
      ti: (document.title || '').slice(0, 255),
      r: (document.referrer || '').slice(0, 2000),
      at: new Date().toISOString()
    }]);
  }

  function watchNavigation() {
    /* Single-page sites change the URL without reloading, so history has to
       be wrapped or every visit looks like one page. */
    var last = location.href;
    var fire = function () {
      if (location.href === last) return;
      last = location.href;
      pageview();
    };
    ['pushState', 'replaceState'].forEach(function (name) {
      var original = history[name];
      if (typeof original !== 'function') return;
      history[name] = function () {
        var result = original.apply(this, arguments);
        setTimeout(fire, 0);
        return result;
      };
    });
    window.addEventListener('popstate', fire);
  }

  /* The form inside a popup posts its visitor id with the submission, so the
     server links the visitor to the contact it already resolved from the
     email. The email itself never crosses the frame boundary -- every script
     on this page can listen for `message`, including their ad tech. */
  function answerVisitorRequests() {
    window.addEventListener('message', function (e) {
      if (e.origin !== CONFIG.origin) return;
      var data = e.data || {};
      if (data.source !== 'mailflow-form' || data.type !== 'who') return;
      try {
        e.source.postMessage(
          { source: 'mailflow-site', type: 'visitor', visitorId: visitorId() },
          CONFIG.origin
        );
      } catch (err) {}
    });
  }

__POPUP_JS__

  function start() {
    answerVisitorRequests();
    countPage();
    if (CONFIG.track !== false) {
      pageview();
      watchNavigation();
    }
    if (!CONFIG.popups.length) return;

    if (!needsAudience()) {
      startPopups(null);
      return;
    }
    /* One call, only when some popup targets something the browser cannot
       answer on its own. Everyone else pays nothing for the feature. */
    try {
      fetch(CONFIG.origin + '/track/audience', {
        method: 'POST', credentials: 'omit',
        headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
        body: JSON.stringify({ k: CONFIG.key, vid: visitorId() })
      })
        .then(function (r) { return r.json(); })
        .then(startPopups)
        .catch(function () { startPopups(null); });
    } catch (e) {
      startPopups(null);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
"""
