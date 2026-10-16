#!/usr/bin/env python3
"""Builds kosherno.app from content/<lang>.json.

Every page exists once per language at its own URL (/, /ru/, /he/ and
/partners/, /ru/partners/, /he/partners/), so search engines and links in
letters open the right language without JavaScript.

    python3 tools/build.py          # production pages into the repo root (GitHub Pages)
    python3 tools/build.py --dev    # local preview into .preview/, forms go to a local kosher-forms Worker

Forms post to the kosher-forms Cloudflare Worker (../kosher-forms-worker),
which checks Turnstile and mails the team through Resend. The production
build refuses to run until site.config.json holds the Worker address and the
Turnstile site key: a form that silently goes nowhere must never ship.
"""

import argparse
import datetime
import hashlib
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://kosherno.app"
LANGS = ["en", "ru", "he"]
DEFAULT_LANG = "en"
PAGES = ["home", "partners"]
# `npm run dev` in ../kosher-forms-worker, and Cloudflare's test site key that always passes.
DEV_ENDPOINT = "http://127.0.0.1:8788/contact"
DEV_SITEKEY = "1x00000000000000000000AA"
# The kosher-forms Worker refuses longer values (LIMITS in its src/index.js); the browser stops them first.
FIELD_LIMITS = {"name": 100, "organization": 160, "email": 200, "phone": 60, "place": 120, "message": 5000}
FONT_FOR_LANG = {"en": "latin", "ru": "cyr", "he": "hebrew"}

E = html.escape

ICONS = {
    "chat": '<path d="M5 5h14v10H9l-4 4z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "moon": '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    "barcode": '<path d="M4 6v12M7 6v12M10 6v12M14 6v12M16 6v12M20 6v12"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3z"/>',
    "chevron": '<path d="M6 9l6 6 6-6"/>',
    "spark": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6"/>',
    "bell": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.9 1.9 0 0 0 3.4 0"/>',
    "back": '<path d="M15 6l-6 6 6 6"/>',
    "send": '<path d="M12 19V5M5 12l7-7 7 7"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
}


def https(url):
    """Source links in the content must be https; anything else stops the build."""
    if not url.startswith("https://"):
        sys.exit(f"not an https link in the content: {url}")
    return url


def arrow(direction):
    return " ←" if direction == "rtl" else " →"


def icon(name, size=22, stroke=1.8):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{ICONS[name]}</svg>')


def words(text, start_ms=0, step_ms=70):
    """Wraps each word for the focus-in reveal (E1): the words sharpen one after another."""
    return " ".join(f'<span class="rw" style="--d:{start_ms + i * step_ms}ms">{E(w)}</span>'
                    for i, w in enumerate(text.split()))


def path_for(page, lang):
    prefix = "" if lang == DEFAULT_LANG else f"/{lang}"
    return f"{prefix}/" if page == "home" else f"{prefix}/partners/"


def asset_version():
    digest = hashlib.sha256()
    for name in ("assets/site.css", "assets/site.js"):
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()[:10]


class Builder:
    def __init__(self, dev, endpoint, sitekey):
        self.dev = dev
        self.endpoint = DEV_ENDPOINT if dev else endpoint
        self.sitekey = DEV_SITEKEY if dev else sitekey
        self.out = ROOT / ".preview" if dev else ROOT
        self.version = asset_version()
        self.all = {l: json.loads((ROOT / "content" / f"{l}.json").read_text(encoding="utf-8")) for l in LANGS}

    # ---- shared pieces -------------------------------------------------

    def head(self, c, page):
        lang = c["lang"]
        p = c[page]
        url = SITE + path_for(page, lang)
        alternates = "\n".join(
            f'<link rel="alternate" hreflang="{l}" href="{SITE}{path_for(page, l)}">' for l in LANGS)
        locales = "\n".join(
            f'<meta property="og:locale:alternate" content="{self.all[l]["locale"]}">' for l in LANGS if l != lang)
        font = FONT_FOR_LANG[lang]
        # Russian and Hebrew pages also set latin glyphs (spaces, digits, the name), so both subsets load early.
        preload = "\n".join(
            f'<link rel="preload" href="/assets/fonts/rubik-var-{f}.woff2" as="font" type="font/woff2" crossorigin>'
            for f in dict.fromkeys([font, "latin"]))
        robots = '<meta name="robots" content="noindex">\n' if self.dev else ""
        return f"""<!doctype html>
<html lang="{lang}" dir="{c['dir']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{E(p['title'])}</title>
<meta name="description" content="{E(p['description'])}">
{robots}<link rel="canonical" href="{url}">
{alternates}
<link rel="alternate" hreflang="x-default" href="{SITE}{path_for(page, DEFAULT_LANG)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="KosherGPT">
<meta property="og:locale" content="{c['locale']}">
{locales}
<meta property="og:title" content="{E(p['og_title'])}">
<meta property="og:description" content="{E(p['description'])}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/assets/og/{page}-{lang}.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{E(p['og_title'])}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#11302a">
<link rel="icon" href="/assets/icons/favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="/assets/icons/icon-96.png" sizes="96x96" type="image/png">
<link rel="apple-touch-icon" href="/assets/icons/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
{preload}
<link rel="stylesheet" href="/assets/site.css?v={self.version}">
<script>document.documentElement.classList.add('js');setTimeout(function(){{if(!window.kgReady)document.documentElement.classList.remove('js')}},3000)</script>
<script type="application/ld+json">{self.structured_data(c, page, url)}</script>
</head>"""

    def structured_data(self, c, page, url):
        org = {"@type": "Organization", "@id": f"{SITE}/#org", "name": "KosherGPT", "url": SITE + "/",
               "logo": f"{SITE}/assets/icons/icon-512.png"}
        if page == "home" and c["lang"] == "en":
            graph = [org, {"@type": "WebSite", "@id": f"{SITE}/#site", "name": "KosherGPT", "url": SITE + "/",
                           "inLanguage": c["lang"], "publisher": {"@id": f"{SITE}/#org"}}]
        elif page == "home":
            graph = [org]  # one WebSite node, on the root page; the other home pages are its translations
        else:
            graph = [org, {"@type": "FAQPage", "url": url, "inLanguage": c["lang"], "mainEntity": [
                {"@type": "Question", "name": q["q"], "acceptedAnswer": {"@type": "Answer", "text": q["a"]}}
                for q in c["partners"]["faq"]]}]
        return json.dumps({"@context": "https://schema.org", "@graph": graph},
                          ensure_ascii=False).replace("<", "\\u003c")

    def topbar(self, c, page):
        k = c["common"]
        lang = c["lang"]
        home = path_for("home", lang)
        tone = "on-dark" if page == "home" else "on-light"
        if page == "home":
            links = [("#features", k["nav_features"]), ("#ask", k["nav_try"]),
                     (path_for("partners", lang), k["nav_orgs"])]
            brand_extra = ""
        else:
            links = [("#contact", k["nav_contact"])]
            brand_extra = f'<span>{E(k["orgs_suffix"])}</span>'
        nav = "".join(f'<a href="{href}">{E(text)}</a>' for href, text in links)
        menu = "".join(
            f'<a href="{path_for(page, l)}" hreflang="{l}" lang="{l}"'
            + (' aria-current="page"' if l == lang else "")
            + f'>{E(self.all[l]["label"])}' + ('<span aria-hidden="true">✓</span>' if l == lang else "") + "</a>"
            for l in LANGS)
        hints = json.dumps({l: {"url": path_for(page, l), "text": self.all[l]["common"]["lang_hint"] + arrow(self.all[l]["dir"]),
                                "dir": self.all[l]["dir"]} for l in LANGS if l != lang}, ensure_ascii=False)
        return f"""<body>
<a class="skip" href="#main">{E(k['skip'])}</a>
<div class="langhint" id="langhint" hidden data-page-lang="{lang}" data-alternates="{E(hints, quote=True)}"></div>
<div class="topbar {tone}"><div class="bar"><div class="bar-inner">
<a class="brand" href="{home}"><img src="/assets/icons/icon-96.png" width="38" height="38" alt=""><b>KosherGPT</b>{brand_extra}</a>
<nav class="nav" aria-label="{E(k['nav_features'])}">{nav}</nav>
<details class="lang">
<summary aria-label="{E(k['lang_button'])}">{icon('globe', 16)}<span class="lang-name">{E(c['label'])}</span><span class="lang-code">{E(c['short'])}</span>{icon('chevron', 12, 2.2)}</summary>
<div class="lang-menu">{menu}<span class="soon">{E(k['more_langs'])}</span></div>
</details>
</div></div></div>
<main id="main">"""

    def footer(self, c):
        k = c["common"]
        return f"""</main>
<footer class="footer"><div class="wrap">
<a class="brand" href="{path_for('home', c['lang'])}"><img src="/assets/icons/icon-96.png" width="26" height="26" alt=""><b>KosherGPT</b></a>
<span>{E(k['footer_beta'])}</span>
<span>{E(k['footer_note'])}</span>
</div></footer>
<script src="/assets/site.js?v={self.version}" defer></script>
</body>
</html>
"""

    def scanner(self, c, states, group_label, note, buttons_inline=False):
        first = states[0]
        data = json.dumps(states, ensure_ascii=False)
        buttons = "".join(
            f'<button type="button" data-state="{E(s["id"])}" aria-pressed="{"true" if i == 0 else "false"}">{E(s["label"])}</button>'
            for i, s in enumerate(states))
        # Every state also sits, invisible, in the result card's cell, so the card always has the
        # height of its longest state and switching never moves the page.
        sizers = "".join(
            f'<div class="result-sizer js-only" aria-hidden="true"><div class="result-head"><b>{E(s["name"])}</b><small>{E(s["code"])}</small></div>'
            f'<div class="verdict"><b>{E(s["title"])}</b><span>{E(s["note"])}</span></div></div>'
            for s in states)
        visual = f"""<div class="scanner">
<div class="viewfinder" aria-hidden="true">
<div class="pack"><b data-f="name">{E(first['name'])}</b><div><div class="bars"></div><small data-f="code">{E(first['code'])}</small></div></div>
<span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span>
<span class="beam"></span>
</div>
<div class="result" aria-live="polite">
<div class="result-head"><b data-f="name">{E(first['name'])}</b><small data-f="code">{E(first['code'])}</small></div>
<div class="verdict tone-{E(first['tone'])}"><b data-f="title">{E(first['title'])}</b><span data-f="note">{E(first['note'])}</span></div>
{sizers}
</div>
</div>"""
        controls = f"""<div class="states js-only" role="group" aria-label="{E(group_label)}">{buttons}</div>
<p class="small on-night muted">{E(note)}</p>"""
        return visual, controls, E(data, quote=True)

    def form(self, c, kind, fields_html):
        f = c["form"]
        lang = c["lang"]
        submit = f["submit_partners"] if kind == "partners" else f["submit_beta"]
        return f"""<div class="form-box">
<form class="form" data-form novalidate method="post" action="#" data-kind="{kind}" data-lang="{lang}"
 data-endpoint="{E(self.endpoint)}" data-sitekey="{E(self.sitekey)}"
 data-msg-sending="{E(f['sending'])}" data-msg-error="{E(f['error'])}" data-msg-invalid="{E(f['invalid'])}"
 data-msg-captcha="{E(f['captcha'])}" data-msg-rate="{E(f['rate'])}" data-msg-nocfg="{E(f['not_configured'])}">
<div class="trap" aria-hidden="true"><label for="{kind}-website">Website</label><input id="{kind}-website" name="website" type="text" tabindex="-1" autocomplete="off"></div>
{fields_html}
<label class="consent"><input type="checkbox" name="consent" value="yes" required> <span>{E(f['consent'])}</span></label>
<div class="captcha full-row" data-captcha></div>
<p class="check-hint full-row" hidden>{E(f['check_hint'])}</p>
<div class="form-foot"><button type="submit" class="btn btn-teal">{E(submit)}</button><p class="form-status" role="status" aria-live="polite"></p></div>
<noscript><p class="form-status full-row">{E(f['noscript'])}</p></noscript>
<p class="small muted full-row">{E(f['delivery'])}</p>
</form>
<div class="form-done" hidden tabindex="-1"><b>{E(f['success_title'])}</b><span class="muted">{E(f['success_text'])}</span></div>
</div>"""

    @staticmethod
    def field(fid, name, label, kind="text", required=False, optional_label="", full=False, placeholder="", autocomplete=""):
        opt = "" if required else f" <small>({E(optional_label)})</small>"
        req = (" required" if required else "") + f' maxlength="{FIELD_LIMITS[name]}"'
        ph = f' placeholder="{E(placeholder)}"' if placeholder else ""
        ac = f' autocomplete="{autocomplete}"' if autocomplete else ""
        cls = "field full" if full else "field"
        if kind == "textarea":
            control = f'<textarea id="{fid}" name="{name}"{ph}{req}></textarea>'
        else:
            control = f'<input id="{fid}" name="{name}" type="{kind}"{ph}{ac}{req}>'
        return f'<div class="{cls}"><label for="{fid}">{E(label)}{opt}</label>{control}</div>'

    # ---- pages ---------------------------------------------------------

    def home(self, c):
        h, f = c["home"], c["form"]
        lang = c["lang"]
        partners = path_for("partners", lang)
        features = "".join(
            f'<li><span class="icon-tile">{icon(it["icon"])}</span><div><b>{E(it["title"])}</b> '
            f'<span class="muted">{E(it["text"])}</span></div></li>' for it in h["one_items"])
        checks = "".join(f'<li><span class="num">{i}</span><span>{E(t)}</span></li>'
                         for i, t in enumerate(h["check_items"], 1))
        scan_visual, scan_controls, scan_data = self.scanner(c, h["scan_states"], h["scan_group"], h["scan_note"])
        us = ' class="us"'
        cols = "".join(f'<th scope="col"{us if i == 0 else ""}>{E(col)}</th>'
                       for i, col in enumerate(h["compare_cols"]))

        def cell(v, i):
            cls = ' class="us"' if i == 0 else ""
            if v == "yes":
                return f'<td{cls}><span class="yes" aria-hidden="true">✓</span><span class="vh">{E(h["compare_yes"])}</span></td>'
            if v == "no":
                return f'<td{cls}><span class="no" aria-hidden="true">—</span><span class="vh">{E(h["compare_no"])}</span></td>'
            klass = "yes" if i == 0 else "partial"
            return f'<td{cls}><span class="{klass}">{E(v)}</span></td>'
        rows = "".join(f'<tr><th scope="row">{E(r["label"])}</th>' + "".join(cell(v, i) for i, v in enumerate(r["cells"])) + "</tr>"
                       for r in h["compare_rows"])
        qa_html = []
        for item in h["qa"]:
            # E6: every word carries its place in the answer, so the words fade in one after another
            # and the citation chips follow the last word. The sources stay in the page for readers
            # without scripts; with scripts a chip opens them in the phone's bottom sheet.
            parts, index = [], 0
            for p in item["paras"]:
                spans = []
                for w in p["text"].split():
                    spans.append(f'<span class="sw" style="--i:{index}">{E(w)}</span>')
                    index += 1
                chips = "".join(
                    f'<button type="button" class="cite js-only" style="--i:{index}" aria-label="{E(h["ask_show"])} {n}">{n}</button>'
                    for n in p["chips"])
                parts.append("<p>" + " ".join(spans) + chips + "</p>")
            paras = "".join(parts)
            sources = ""
            if item["sources"]:
                srcs = "".join(
                    f'<div class="source"><span class="num">{s["n"]}</span><div><b>{E(s["title"])}</b>'
                    f'<span>{E(s["note"])}</span><a href="{E(https(s["href"]))}" rel="noopener" target="_blank">{E(h["ask_open"])}</a></div></div>'
                    for s in item["sources"])
                sources = f'<div class="sources"><span class="sources-title">{E(h["ask_sources"])}</span>{srcs}</div>'
            qa_html.append(f"""<article class="qa" data-qa="{E(item['id'])}">
<div class="bubble">{E(item['q'])}</div>
<div class="ai"><div class="ai-label">{icon('spark', 16)}KosherGPT</div>
<div class="dots" aria-hidden="true"><i></i><i></i><i></i></div>
<div class="ai-body">{paras}</div>{sources}</div>
</article>""")
        suggestions = "".join(
            f'<button type="button" data-ask-for="{E(item["id"])}">{E(item["q"])}</button>' for item in h["qa"])
        beta_fields = (
            self.field("beta-name", "name", f["name"], optional_label=f["optional"], autocomplete="name")
            + self.field("beta-email", "email", f["email"], kind="email", required=True, autocomplete="email")
            + self.field("beta-message", "message", f["message"], kind="textarea", optional_label=f["optional"],
                         full=True, placeholder=f["message_ph_beta"]))
        return f"""
<section class="night hero" data-tone="dark">
<div class="wrap hero-grid">
<div class="hero-text">
<h1 class="words">{words(h['h1_a'])}<br>{words(h['h1_b'], 70 * len(h['h1_a'].split()))}</h1>
<p class="lead">{E(h['lead'])}</p>
<div class="actions"><a class="btn btn-glass" href="#beta">{E(h['cta_beta'])}</a><a class="btn btn-link" href="{partners}">{E(h['cta_orgs'])}{arrow(c['dir'])}</a></div>
</div>
<div class="arch-stage" aria-hidden="true"><div class="arch-glow"></div><div class="arch"><div class="arch-inner"><div class="arch-core"></div></div></div><div class="arch-sill"></div></div>
</div>
</section>

<section class="day section" id="features" data-tone="light">
<div class="wrap split">
<div class="text">
<h2>{E(h['one_h2'])}</h2>
<p class="lead muted">{E(h['one_lead'])}</p>
<ul class="feature-list">{features}</ul>
</div>
<div class="visual"><div class="phone"><div class="screen"><img src="/assets/img/answer.webp" width="600" height="1304" alt="{E(h['one_shot_alt'])}" loading="lazy"></div></div></div>
</div>
</section>

<section class="day section" data-tone="light">
<div class="wrap split reverse">
<div class="visual"><div class="phone-pair">
<div class="phone sm"><div class="screen"><img src="/assets/img/answer.webp" width="600" height="1304" alt="{E(h['check_alt_a'])}" loading="lazy"></div></div>
<div class="phone sm"><div class="screen"><img src="/assets/img/sources.webp" width="600" height="1304" alt="{E(h['check_alt_b'])}" loading="lazy"></div></div>
</div></div>
<div class="text">
<h2>{E(h['check_h2'])}</h2>
<p class="lead muted">{E(h['check_lead'])}</p>
<ul class="num-list">{checks}</ul>
</div>
</div>
</section>

<section class="night left section" data-tone="dark">
<div class="wrap split" data-scanner data-states="{scan_data}">
<div class="visual">{scan_visual}</div>
<div class="text">
<span class="tag">{E(h['scan_tag'])}</span>
<h2>{E(h['scan_h2'])}</h2>
<p class="lead">{E(h['scan_lead'])}</p>
{scan_controls}
</div>
</div>
</section>

<section class="day section" data-tone="light">
<div class="wrap split">
<div class="text">
<h2>{E(h['shabbat_h2'])}</h2>
<p class="lead muted">{E(h['shabbat_lead'])}</p>
</div>
<div class="visual"><div class="glass-stage">
<span class="glow glow-a" aria-hidden="true"></span><span class="glow glow-b" aria-hidden="true"></span><span class="glow glow-c" aria-hidden="true"></span>
<div class="shabbat-card glass" data-tilt>
<div class="lift">
<div class="shabbat-top"><span>{E(h['shabbat_eyebrow'])}</span><span class="pill">{E(h['shabbat_city'])}</span></div>
<div class="times"><div><span>{E(h['shabbat_candles'])}</span><b>18:12</b></div><div><span>{E(h['shabbat_havdalah'])}</span><b>19:21</b></div></div>
<div class="reminder">{icon('bell', 18)}{E(h['shabbat_reminder'])}</div>
</div>
<span class="band" aria-hidden="true"></span><span class="rim" aria-hidden="true"></span>
</div>
</div></div>
</div>
</section>

<section class="day section" data-tone="light">
<div class="wrap stack">
<h2>{E(h['compare_h2'])}</h2>
<div class="table-box"><table class="compare"><thead><tr><td></td>{cols}</tr></thead><tbody>{rows}</tbody></table></div>
<p class="small muted">{E(h['compare_note'])}</p>
</div>
</section>

<section class="ask" id="ask" data-tone="light">
<div class="ask-inner">
<div class="ask-head"><h2>{E(h['ask_h2'])}</h2><p class="lead muted">{E(h['ask_lead'])}</p></div>
<div class="chat-phone" data-ask><div class="chat-screen">
<span class="chat-island" aria-hidden="true"></span>
<div class="chat-bar"><span class="chat-back" aria-hidden="true">{icon('back', 16, 2.2)}</span><img src="/assets/icons/icon-96.png" width="26" height="26" alt="">KosherGPT</div>
<div class="chat-thread" role="log" aria-live="polite" aria-label="KosherGPT" tabindex="0">
<div class="ask-empty js-only">{E(h['ask_empty'])}</div>
{''.join(qa_html)}
</div>
<div class="chat-foot">
<div class="suggest js-only">{suggestions}</div>
<div class="composer" aria-hidden="true"><span class="composer-text">{E(h['ask_placeholder'])}</span><span class="send">{icon('send', 18, 2.4)}</span></div>
</div>
<div class="sheet" hidden><div class="sheet-dim" data-close></div>
<div class="sheet-card" role="dialog" aria-modal="true" aria-labelledby="ask-sheet-title"><span class="sheet-grip" aria-hidden="true"></span>
<div class="sheet-head"><span class="sources-title" id="ask-sheet-title">{E(h['ask_sources'])}</span><button type="button" class="sheet-close" data-close aria-label="{E(h['ask_close'])}">{icon('close', 16, 2.4)}</button></div>
<div class="sheet-body"></div></div></div>
</div></div>
</div>
</section>

<section class="day section" data-tone="light">
<div class="wrap"><div class="callout">
<div class="text"><h2>{E(h['orgs_h2'])}</h2><p>{E(h['orgs_text'])}</p><a class="btn btn-glass" href="{partners}">{E(h['orgs_link'])}</a></div>
<div class="mini-arch" aria-hidden="true"><div><div></div></div></div>
</div></div>
</section>

<section class="day section" id="beta" data-tone="light">
<div class="wrap beta">
<div class="stack center"><h2>{E(h['beta_h2'])}</h2><p class="muted">{E(h['beta_lead'])}</p></div>
{self.form(c, 'beta', beta_fields)}
</div>
</section>
"""

    def partners(self, c):
        p, f = c["partners"], c["form"]
        scan_visual, scan_controls, scan_data = self.scanner(c, p["scan_states"], p["scan_group"], p["scan_note"])
        how = "".join(f'<article class="card"><span class="num">{i}</span><div><h3>{E(x["title"])}</h3><p>{E(x["text"])}</p></div></article>'
                      for i, x in enumerate(p["how"], 1))
        steps = "".join(f'<li><b>{E(s["title"])}</b><span>{E(s["text"])}</span></li>' for s in p["steps"])
        gets = "".join(f'<article class="card"><div><h3>{E(x["title"])}</h3><p>{E(x["text"])}</p></div></article>' for x in p["gets"])
        terms = "".join(f"<li>{E(t)}</li>" for t in p["terms"])
        faq = "".join(f'<div><dt>{E(q["q"])}</dt><dd>{E(q["a"])}</dd></div>' for q in p["faq"])
        fields = (
            self.field("p-name", "name", f["name"], required=True, autocomplete="name")
            + self.field("p-org", "organization", f["org"], required=True, autocomplete="organization")
            + self.field("p-email", "email", f["email"], kind="email", required=True, autocomplete="email")
            + self.field("p-phone", "phone", f["phone"], kind="tel", optional_label=f["optional"], autocomplete="tel")
            + self.field("p-place", "place", f["place"], optional_label=f["optional"], full=True, autocomplete="country-name")
            + self.field("p-message", "message", f["message"], kind="textarea", optional_label=f["optional"],
                         full=True, placeholder=f["message_ph_partners"]))
        return f"""
<section class="day hero" data-tone="light">
<div class="wrap split" data-scanner data-states="{scan_data}" style="padding-block: 40px 72px;">
<div class="text">
<h1 class="words">{words(p['h1'])}</h1>
<p class="lead muted">{E(p['lead'])}</p>
<div class="actions"><a class="btn btn-teal" href="#contact">{E(p['cta'])}</a></div>
</div>
<div class="visual stack">{scan_visual}{scan_controls}</div>
</div>
</section>

<section class="day section" data-tone="light">
<div class="wrap stack"><h2>{E(p['how_h2'])}</h2><div class="cards">{how}</div></div>
</section>

<section class="day section" data-tone="light">
<div class="wrap stack"><h2>{E(p['steps_h2'])}</h2><ol class="steps">{steps}</ol></div>
</section>

<section class="day section" data-tone="light">
<div class="wrap stack"><h2>{E(p['gets_h2'])}</h2><div class="cards">{gets}</div></div>
</section>

<section class="day section" data-tone="light">
<div class="wrap"><div class="callout"><div class="text"><h2>{E(p['terms_h2'])}</h2></div><ul class="checks">{terms}</ul></div></div>
</section>

<section class="day section" data-tone="light">
<div class="wrap stack"><h2>{E(p['faq_h2'])}</h2><dl class="faq">{faq}</dl></div>
</section>

<section class="day section" id="contact" data-tone="light">
<div class="wrap stack">
<h2>{E(p['contact_h2'])}</h2>
<p class="lead muted">{E(p['contact_lead'])}</p>
{self.form(c, 'partners', fields)}
</div>
</section>
"""

    # ---- site files ----------------------------------------------------

    def sitemap(self):
        today = datetime.date.today().isoformat()
        rows = []
        for page in PAGES:
            alts = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{SITE}{path_for(page, l)}"/>' for l in LANGS)
            alts += f'<xhtml:link rel="alternate" hreflang="x-default" href="{SITE}{path_for(page, DEFAULT_LANG)}"/>'
            for lang in LANGS:
                rows.append(f"<url><loc>{SITE}{path_for(page, lang)}</loc><lastmod>{today}</lastmod>{alts}</url>")
        return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n' + "\n".join(rows) + "\n</urlset>\n")

    def not_found(self):
        links = " · ".join(f'<a href="{path_for("home", l)}" lang="{l}">{E(self.all[l]["label"])}</a>' for l in LANGS)
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Page not found · KosherGPT</title><meta name="robots" content="noindex">
<link rel="icon" href="/assets/icons/favicon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="/assets/icons/icon-96.png" sizes="96x96" type="image/png">
<link rel="stylesheet" href="/assets/site.css?v={self.version}"></head>
<body><main class="night"><div class="wrap notfound"><h1>Page not found</h1><p class="lead">{links}</p></div></main></body></html>
"""

    def manifest(self):
        return json.dumps({
            "name": "KosherGPT", "short_name": "KosherGPT", "start_url": "/", "display": "browser",
            "background_color": "#ece4d6", "theme_color": "#11302a",
            "icons": [{"src": "/assets/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                      {"src": "/assets/icons/icon-512.png", "sizes": "512x512", "type": "image/png"}]
        }, indent=2) + "\n"

    def write(self, rel, text):
        target = self.out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print("wrote", target.relative_to(ROOT))

    def run(self):
        for lang in LANGS:
            c = self.all[lang]
            for page in PAGES:
                body = self.home(c) if page == "home" else self.partners(c)
                rel = path_for(page, lang).strip("/")
                rel = f"{rel}/index.html" if rel else "index.html"
                self.write(rel, self.head(c, page) + "\n" + self.topbar(c, page) + body + self.footer(c))
        self.write("sitemap.xml", self.sitemap())
        robots = "User-agent: *\nDisallow: /\n" if self.dev else f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n"
        self.write("robots.txt", robots)
        self.write("404.html", self.not_found())
        self.write("site.webmanifest", self.manifest())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dev", action="store_true", help="build the local preview into .preview/")
    args = parser.parse_args()
    config = json.loads((ROOT / "site.config.json").read_text(encoding="utf-8"))
    endpoint = config.get("form_endpoint", "").strip()
    sitekey = config.get("turnstile_sitekey", "").strip()
    test_key = sitekey[:2] in ("1x", "2x", "3x")  # Cloudflare's always-pass/fail test sitekeys
    local = any(h in endpoint for h in ("localhost", "127.0.0.1", "[::1]"))
    if not args.dev and not (endpoint.startswith("https://") and sitekey and not test_key and not local):
        sys.exit("site.config.json needs form_endpoint (the kosher-forms Worker, https://…/contact) and "
                 "a real turnstile_sitekey (not a test key, not localhost). See ../kosher-forms-worker/README.md. "
                 "Use --dev for the local preview.")
    Builder(args.dev, endpoint, sitekey).run()


if __name__ == "__main__":
    main()
