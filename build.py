"""Build the static site: the landing page, one page per product, and the crawler files.

Every page and file is generated from `index.template.html` and the data in `content/`,
so product facts, FAQs and structured data stay in one place.
"""
from html import escape
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
MARK_INLINE = '<img src="{p}assets/brand/lockup-horizontal.svg" width="360" height="58" alt="">'
ARROW = ('<svg class="arrow" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" '
         'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
         '<path d="M6 18 18 6M6 6h12v12"/></svg>')
LICENSE_URL = "https://www.gnu.org/licenses/agpl-3.0.html"


def load(name):
    return json.loads((CONTENT / name).read_text(encoding="utf-8"))


SITE = load("site.json")
FAQ = load("faq.json")
PRODUCTS = load("products.json")
URL = SITE["url"]
ORG_ID = URL + "#organization"


def gh(repo):
    return f"{SITE['org']}/{repo}"


def repos(product):
    return product.get("repos") or [product["repo"]]


def ld(data):
    """A JSON-LD script block; `</` is escaped so the JSON can never close the tag."""
    text = json.dumps(data, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return f'<script type="application/ld+json">\n{text}\n</script>'


def faq_ld(items, page_url):
    return {
        "@type": "FAQPage", "@id": page_url + "#faq", "url": page_url,
        "mainEntity": [{"@type": "Question", "name": i["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": i["a"]}} for i in items],
    }


def faq_html(items, heading_id):
    rows = "\n".join(
        f'          <details class="faq-item"><summary><h3>{escape(i["q"])}</h3>'
        f'<span class="expand" aria-hidden="true">+</span></summary><p>{escape(i["a"])}</p></details>'
        for i in items)
    return f'<div class="faq-list" aria-labelledby="{heading_id}">\n{rows}\n        </div>'


ORGANIZATION = {
    "@type": "Organization", "@id": ORG_ID, "name": "Space Works",
    "alternateName": ["SpaceWorks", "SpaceWorks Labs"], "url": URL,
    "logo": {"@type": "ImageObject", "url": URL + "assets/apple-touch-icon.png", "width": 180, "height": 180},
    "description": "Free, open-source, self-hosted software for makerspaces, fab labs, tool libraries and communities.",
    "sameAs": [SITE["org"], SITE["docs"], SITE["design"]],
    "founder": {"@type": "Person", "name": "Shaan Shoukath", "url": "https://github.com/Shaan-Shoukath"},
    "foundingLocation": {"@type": "Place", "name": "TinkerSpace Kochi",
                         "address": {"@type": "PostalAddress", "addressLocality": "Kochi",
                                     "addressRegion": "Kerala", "addressCountry": "IN"}},
}


def header(prefix):
    home = prefix or "#main"
    links = [("Product", f"{prefix}#workspace"), ("Apps", f"{prefix}#apps"), ("FAQ", f"{prefix}#faq"),
             ("Docs", SITE["docs"]), ("GitHub", gh(SITE["hub"]["repo"]))]
    desktop = "".join(f'\n          <a href="{h}">{t}</a>' for t, h in links)
    mobile = "".join(f'<a href="{h}">{t}</a>' for t, h in links)
    return f'''<header class="top">
    <div class="wrap bar">
      <a class="brand" href="{home}" aria-label="Space Works home">{MARK_INLINE.format(p=prefix)}</a>
      <nav class="nav" aria-label="Main">
        <div class="nav-links">{desktop}
          <a class="nav-start" href="{prefix}#install">Get started {ARROW}</a>
        </div>
        <details class="mobile-menu"><summary>Menu</summary><nav aria-label="Mobile">{mobile}<a href="{prefix}#install">Get started</a></nav></details>
      </nav>
    </div>
  </header>'''


def footer(prefix):
    hub = SITE["hub"]
    apps = "".join(f'\n        <a href="{prefix}{p["slug"]}/">{escape(p["short"])}</a>' for p in PRODUCTS)
    return f'''<footer class="colophon">
    <div class="wrap closing-inner"><div><p class="eyebrow">There’s a place for your next idea.</p><h2 id="closing-heading">Let’s get making.</h2></div><a class="btn btn-solid" href="{prefix}#install">Set up your space {ARROW}</a></div>
    <div class="wrap colophon-row">
      <a class="brand" href="{prefix or '#main'}" aria-label="Space Works home">{MARK_INLINE.format(p=prefix)}</a>
      <p class="code-text">{hub["version"]} · released {release_date()} · AGPL-3.0 · free software for shared tools</p>
      <nav aria-label="Apps">{apps}
      </nav>
      <nav aria-label="Project">
        <a href="{gh(hub["repo"])}">GitHub</a>
        <a href="{gh(hub["repo"])}/releases">Releases</a>
        <a href="{gh(hub["repo"])}/blob/main/CHANGELOG.md">Changelog</a>
        <a href="{SITE["docs"]}">Docs</a>
        <a href="{SITE["docs"]}install/one-line-install/">Self-hosting</a>
      </nav>
    </div>
  </footer>'''


def release_date():
    y, m, d = SITE["hub"]["released"].split("-")
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    return f"{int(d)} {months[int(m) - 1]} {y}"


def head(title, description, page_url, prefix, image_alt, extra=""):
    return f'''<meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(description)}">
  <link rel="canonical" href="{page_url}">
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
  <meta name="theme-color" content="#FFF4E8">
  <meta name="color-scheme" content="light">
  <link rel="icon" href="{prefix}assets/mark.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="{prefix}assets/apple-touch-icon.png">
  <link rel="preload" href="{prefix}fonts/Gilroy-Regular.woff" as="font" type="font/woff" crossorigin>
  <link rel="preload" href="{prefix}fonts/Gilroy-SemiBold.woff" as="font" type="font/woff" crossorigin>
  <link rel="alternate" type="text/plain" title="LLM summary" href="{URL}llms.txt">
  <meta property="og:site_name" content="Space Works">
  <meta property="og:locale" content="en_IN">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{page_url}">
  <meta property="og:image" content="{URL}assets/og-1200x630.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="{escape(image_alt)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(title)}">
  <meta name="twitter:description" content="{escape(description)}">
  <meta name="twitter:image" content="{URL}assets/og-1200x630.png">
  <link rel="stylesheet" href="{prefix}styles.css">{extra}'''


# ---------------------------------------------------------------- landing page

def home_ld():
    hub = SITE["hub"]
    return ld({"@context": "https://schema.org", "@graph": [
        ORGANIZATION,
        {"@type": "WebSite", "@id": URL + "#website", "url": URL, "name": "Space Works",
         "inLanguage": "en", "publisher": {"@id": ORG_ID}},
        {"@type": "WebPage", "@id": URL + "#webpage", "url": URL, "name": HOME_TITLE,
         "description": HOME_DESCRIPTION, "isPartOf": {"@id": URL + "#website"},
         "about": {"@id": URL + "#software"}, "dateModified": SITE["updated"], "inLanguage": "en"},
        {"@type": "SoftwareApplication", "@id": URL + "#software", "name": "Space Works",
         "description": hub["definition"], "url": URL,
         "applicationCategory": "BusinessApplication",
         "applicationSubCategory": "Makerspace management software",
         "operatingSystem": "Linux (Docker Compose)", "softwareVersion": hub["version"],
         "datePublished": hub["released"], "license": LICENSE_URL, "isAccessibleForFree": True,
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
         "downloadUrl": gh(hub["repo"]), "installUrl": SITE["docs"] + "install/one-line-install/",
         "softwareHelp": {"@type": "CreativeWork", "url": SITE["docs"]},
         "featureList": hub["features"], "publisher": {"@id": ORG_ID}, "author": {"@id": ORG_ID}},
        {"@type": "ItemList", "@id": URL + "#apps", "name": "Space Works standalone apps",
         "itemListElement": [{"@type": "ListItem", "position": n, "name": p["name"],
                              "url": f"{URL}{p['slug']}/"} for n, p in enumerate(PRODUCTS, 1)]},
        faq_ld(FAQ, URL),
    ]})


HOME_TITLE = "Space Works — Open-source makerspace management software"
HOME_DESCRIPTION = ("Free, open-source, self-hosted makerspace software: inventory and QR tool lending, "
                    "machines and 3D printing, events, room bookings and memberships.")


def apps_html():
    cards = []
    for p in PRODUCTS:
        status = p["status"]
        tag = "is-live" if status == "Released" else ""
        cards.append(
            f'          <a class="app-card" href="{p["slug"]}/">\n'
            f'            <span class="surface-tag {tag}">{escape(status)}</span>\n'
            f'            <h3>{escape(p["name"])}</h3>\n'
            f'            <p>{escape(p["card"])}</p>\n'
            f'            <span class="app-more">{escape(p["category"])} {ARROW}</span>\n'
            f'          </a>')
    return '<div class="apps">\n' + "\n".join(cards) + "\n        </div>"


def build_home():
    qr = ET.parse(ROOT / "assets/qr.svg").getroot()
    paths = [n.attrib["d"] for n in qr if n.tag.endswith("path") and n.get("stroke") == "#000000"]
    if len(paths) != 1:
        raise ValueError("Expected one QR foreground path")
    html = (ROOT / "index.template.html").read_text(encoding="utf-8")
    tokens = {
        "HEAD": head(HOME_TITLE, HOME_DESCRIPTION, URL, "",
                     "Space Works open-box logo on a warm cream background"),
        "JSONLD": home_ld(), "HEADER": header(""), "FOOTER": footer(""),
        "DEFINITION": escape(SITE["hub"]["definition"]),
        "APPS": apps_html(), "FAQ": faq_html(FAQ, "faq-heading"),
        "INSTALL": escape(SITE["hub"]["install"]),
        "QR_VIEWBOX": qr.attrib["viewBox"], "QR_PATH": paths[0],
    }
    for token, value in tokens.items():
        if "{{" + token + "}}" not in html:
            raise ValueError(f"Missing template token: {token}")
        html = html.replace("{{" + token + "}}", value)
    return html


# ---------------------------------------------------------------- product pages

def product_ld(p, page_url):
    is_mobile = p["slug"] == "mobile"
    apps = []
    for repo in repos(p):
        android = repo.endswith("Android")
        app = {
            "@type": "MobileApplication" if is_mobile else "SoftwareApplication",
            "@id": f"{page_url}#{repo.lower()}",
            "name": p["name"] if not is_mobile else ("Space Works for Android" if android else "Space Works for iOS"),
            "description": p["definition"], "url": page_url,
            "applicationCategory": "BusinessApplication", "applicationSubCategory": p["category"],
            "operatingSystem": ("Android 8 or later" if android else "iOS 17 or later") if is_mobile
            else "Linux (Docker Compose)",
            "license": LICENSE_URL, "isAccessibleForFree": True,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "downloadUrl": gh(repo), "featureList": [i for g in p["features"] for i in g["items"]][:12],
            "keywords": ", ".join(p["keywords"]),
            "publisher": {"@id": ORG_ID}, "author": {"@id": ORG_ID},
            "isPartOf": {"@id": URL + "#software"},
        }
        if p.get("version"):
            app["softwareVersion"] = p["version"]
        apps.append(app)
        apps.append({"@type": "SoftwareSourceCode", "@id": f"{page_url}#source-{repo.lower()}",
                     "name": repo, "codeRepository": gh(repo), "license": LICENSE_URL,
                     "programmingLanguage": p["languages"], "targetProduct": {"@id": app["@id"]},
                     "author": {"@id": ORG_ID}})
    return ld({"@context": "https://schema.org", "@graph": [
        ORGANIZATION,
        {"@type": "WebPage", "@id": page_url + "#webpage", "url": page_url, "name": p["title"],
         "description": p["description"], "isPartOf": {"@id": URL + "#website"},
         "about": {"@id": apps[0]["@id"]}, "dateModified": SITE["updated"], "inLanguage": "en",
         "breadcrumb": {"@id": page_url + "#breadcrumb"}},
        {"@type": "BreadcrumbList", "@id": page_url + "#breadcrumb", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Space Works", "item": URL},
            {"@type": "ListItem", "position": 2, "name": p["short"], "item": page_url}]},
        *apps, faq_ld(p["faqs"], page_url),
    ]})


def facts_html(p):
    rows = [("What it is", p["category"]), ("Status", p["status"] + (f" · {p['version']}" if p.get("version") else "")),
            ("For", ", ".join(p["audience"])), ("Licence", p["license"]), ("Built with", p["stack"])]
    if p["integrations"]:
        rows.append(("Works with", ", ".join(p["integrations"])))
    if p.get("relationship"):
        rows.append(("How it fits", p["relationship"]))
    source = " · ".join(f'<a href="{gh(r)}">{r}</a>' for r in repos(p))
    body = "".join(f"<div><dt>{escape(k)}</dt><dd>{escape(v)}</dd></div>" for k, v in rows)
    return f'<dl class="facts">{body}<div><dt>Source code</dt><dd>{source}</dd></div></dl>'


def install_html(p):
    if not p.get("install"):
        links = " and ".join(f'<a href="{gh(r)}">{r}</a>' for r in repos(p))
        return (f'<p class="para">Builds from source; there are no store releases yet. Follow along on {links}, '
                f'and point the app at your own <a href="../">Space Works</a> server.</p>')
    render = (f'<p class="install-alt">Prefer the cloud? <a href="{escape(p["render"])}">Deploy to Render</a> '
              f'in one click.</p>') if p.get("render") else ""
    cmd = escape(p["install"])
    return f'''<div class="terminal">
            <div class="terminal-bar"><span>On a Linux server</span><button class="copy" type="button" title="Copies the one-line command" data-copy-text="{cmd}">Copy command</button></div>
<pre class="transcript code-text"><span class="cmd">$ <code>{cmd}</code></span></pre>
          </div>
          <p class="stage-note">Run it as a user with sudo. Read the script first: <a href="{gh(p["repo"])}/blob/main/install.sh">install.sh</a>.</p>{render}'''


def build_product(p):
    page_url = f"{URL}{p['slug']}/"
    groups = "\n".join(
        f'          <article class="feature"><h3>{escape(g["heading"])}</h3><ul>'
        + "".join(f"<li>{escape(i)}</li>" for i in g["items"]) + "</ul></article>"
        for g in p["features"])
    cta = "Follow the apps" if not p.get("install") else f"Get {escape(p['short'])}"
    others = "".join(f'<a href="../{o["slug"]}/">{escape(o["short"])}</a>' for o in PRODUCTS if o is not p)
    return f'''<!doctype html>
<html lang="en">
<head>
  {head(p["title"], p["description"], page_url, "../", f"{p['name']}: {p['category']}")}
  {product_ld(p, page_url)}
</head>
<body class="subpage">
  <a class="skip-link" href="#main">Skip to content</a>

  {header("../")}

  <main id="main">
    <section class="page-hero" aria-labelledby="page-title">
      <div class="wrap">
        <nav class="crumbs" aria-label="Breadcrumb"><a href="../">Space Works</a> <span aria-hidden="true">/</span> <span aria-current="page">{escape(p["short"])}</span></nav>
        <p class="eyebrow">{escape(p["category"])}</p>
        <h1 id="page-title">{escape(p["h1"])}</h1>
        <p class="definition">{escape(p["definition"])}</p>
        <p class="para">{escape(p["summary"])}</p>
        <div class="actions"><a class="btn btn-solid" href="#install">{cta} {ARROW}</a><a class="text-link" href="{gh(repos(p)[0])}">View on GitHub {ARROW}</a></div>
      </div>
    </section>

    <section class="page-section facts-section" aria-labelledby="facts-heading">
      <div class="wrap">
        <h2 id="facts-heading" class="sr-only">At a glance</h2>
        {facts_html(p)}
      </div>
    </section>

    <section class="page-section features-section" aria-labelledby="features-heading">
      <div class="wrap">
        <div class="modules-head"><div><p class="eyebrow">What you can do</p><h2 id="features-heading">{escape(p["short"])}, feature by feature.</h2></div></div>
        <div class="features feature-groups">
{groups}
        </div>
      </div>
    </section>

    <section id="install" class="page-section install-section" aria-labelledby="install-heading">
      <div class="wrap install-grid">
        <div><p class="eyebrow">Install</p><h2 id="install-heading">Yours to run.</h2>
          <p class="para">Free and open source under {escape(p["license"])}. Your data stays in your own database.</p></div>
        <div>
          {install_html(p)}
        </div>
      </div>
    </section>

    <section id="faq" class="page-section faq-section" aria-labelledby="faq-heading">
      <div class="wrap">
        <div class="modules-head"><div><p class="eyebrow">Questions</p><h2 id="faq-heading">{escape(p["short"])}, answered.</h2></div></div>
        {faq_html(p["faqs"], "faq-heading")}
        <p class="more-apps">More from Space Works: <a href="../">the full platform</a>{others}</p>
      </div>
    </section>
  </main>

  {footer("../")}

  <script src="../site.js" defer></script>
</body>
</html>
'''


# ---------------------------------------------------------------- crawler files

def page_urls():
    return [URL] + [f"{URL}{p['slug']}/" for p in PRODUCTS]


def sitemap():
    rows = "".join(f"  <url><loc>{u}</loc><lastmod>{SITE['updated']}</lastmod></url>\n" for u in page_urls())
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + rows + "</urlset>\n")


def robots():
    return f"User-agent: *\nAllow: /\n\nSitemap: {URL}sitemap.xml\n"


def llms():
    hub = SITE["hub"]
    apps = "\n".join(f"- [{p['name']}]({URL}{p['slug']}/): {p['card']}" for p in PRODUCTS)
    faqs = "\n".join(f"- {i['q']} {i['a']}" for i in FAQ[:4])
    return f"""# Space Works

> {hub['definition']} Every project is open source under AGPL-3.0 and built by the Space Works community on GitHub (SpaceWorks-Labs).

Space Works started at TinkerSpace Kochi (TinkerHub, Kerala, India) and runs at TinkerHub Kochi and TinkerHub Calicut for more than 1,000 members. Install the main platform on a Linux server with `{hub['install']}`.

## Main platform

- [Space Works platform]({URL}): {hub['version']}, released {hub['released']}. {'; '.join(hub['features'])}.
- [Source code]({gh(hub['repo'])}): {hub['stack']}.
- [Documentation]({SITE['docs']}): install, self-hosting, configuration, staff guides and API reference.

## Standalone apps

{apps}

## Common questions

{faqs}

## Optional

- [Full product facts]({URL}llms-full.txt): every app's features, install commands and answers in one file.
- [Design system]({SITE['design']}): brand guidelines, logos, tokens and UX specs.
- [GitHub organisation]({SITE['org']}): all repositories.
"""


def llms_full():
    hub = SITE["hub"]
    out = [f"# Space Works — full product facts\n\n> {hub['definition']}\n",
           f"Website: {URL}\nSource: {SITE['org']}\nDocumentation: {SITE['docs']}\nLicence: AGPL-3.0 for every project\n"
           f"Last updated: {SITE['updated']}\n",
           f"## Space Works platform\n\nVersion {hub['version']}, released {hub['released']}. Built with {hub['stack']}.\n"
           f"Install: `{hub['install']}`\n\n" + "\n".join(f"- {f}" for f in hub["features"]) + "\n",
           "### Questions\n\n" + "\n\n".join(f"**{i['q']}**\n{i['a']}" for i in FAQ) + "\n"]
    for p in PRODUCTS:
        block = [f"## {p['name']}\n\nPage: {URL}{p['slug']}/\nSource: "
                 + ", ".join(gh(r) for r in repos(p)) + f"\nStatus: {p['status']}"
                 + (f" ({p['version']})" if p.get("version") else "")
                 + f"\nBuilt with: {p['stack']}\nLicence: {p['license']}\nFor: {', '.join(p['audience'])}\n",
                 p["definition"] + "\n\n" + p["summary"] + "\n"
                 + (f"\n{p['relationship']}\n" if p.get("relationship") else "")]
        if p.get("install"):
            block.append(f"Install: `{p['install']}`" + (f"\nDeploy to Render: {p['render']}" if p.get("render") else "") + "\n")
        for g in p["features"]:
            block.append(f"### {g['heading']}\n\n" + "\n".join(f"- {i}" for i in g["items"]) + "\n")
        block.append("### Questions\n\n" + "\n\n".join(f"**{i['q']}**\n{i['a']}" for i in p["faqs"]) + "\n")
        out.append("\n".join(block))
    return "\n".join(out)


def not_found():
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Page not found · Space Works</title>
  <meta name="robots" content="noindex">
  <link rel="icon" href="{URL}assets/mark.svg" type="image/svg+xml">
  <link rel="stylesheet" href="{URL}styles.css">
</head>
<body class="subpage">
  <main id="main" class="not-found">
    <div class="wrap">
      <p class="eyebrow">404</p>
      <h1>This shelf is empty.</h1>
      <p class="para">The page you were looking for isn’t here. Try the <a href="{URL}">Space Works home page</a>, the <a href="{SITE["docs"]}">documentation</a> or one of the apps:</p>
      <p class="more-apps">{"".join(f'<a href="{URL}{p["slug"]}/">{escape(p["short"])}</a>' for p in PRODUCTS)}</p>
    </div>
  </main>
</body>
</html>
'''


def outputs():
    """Every generated file, keyed by its path relative to the site root."""
    files = {"index.html": build_home(), "sitemap.xml": sitemap(), "robots.txt": robots(),
             "llms.txt": llms(), "llms-full.txt": llms_full(), "404.html": not_found()}
    for p in PRODUCTS:
        files[f"{p['slug']}/index.html"] = build_product(p)
    host = URL.split("/")[2]
    if not host.endswith(".github.io"):
        files["CNAME"] = host + "\n"  # GitHub Pages serves the site on this custom domain
    for name, html in files.items():
        if not name.endswith(".html"):
            continue
        if re.search(r"\{\{[^}]+\}\}", html):
            raise ValueError(f"Unresolved template token in {name}")
        base = (ROOT / name).parent
        for source in re.findall(r'(?:src|href)="((?:\.\./)*(?:assets|fonts)/[^"]+|(?:\.\./)*[a-z]+\.(?:css|js))"', html):
            if not (base / source).resolve().is_file():
                raise FileNotFoundError(f"{name}: {source}")
    return files


def build():
    """The landing page; kept for the tests and for callers of the old single-page build."""
    return build_home()


if __name__ == "__main__":
    files = outputs()
    for name, text in files.items():
        path = ROOT / name
        path.parent.mkdir(exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as output:
            output.write(text)
    print(f"Built {len(files)} files and verified local asset references.")
