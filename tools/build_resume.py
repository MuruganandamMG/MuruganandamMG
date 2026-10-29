"""Build the GitHub visual resume. Install tools/requirements.txt first."""

import argparse
import hashlib
import json
import sys
from html import escape
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.preview' / 'vendor'))
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

DATA = json.loads((ROOT / 'resume.json').read_text(encoding='utf-8'))
FONTS = {name: TTFont(ROOT / 'tools' / 'fonts' / f'{name}.ttf')
         for name in ('Manrope', 'SpaceGrotesk')}
PALETTES = {
    'dark': dict(bg='#101C22', fg='#EDF5F1', muted='#A4B9B9', accent='#9DE0C8', line='#31454B', soft='#172B32'),
    'light': dict(bg='#FBFAF6', fg='#183138', muted='#52686C', accent='#007565', line='#CCD8D4', soft='#EFF3ED'),
}


class Card:
    def __init__(self, width, theme, title):
        self.width, self.c, self.title = width, PALETTES[theme], title
        self.parts, self.glyphs, self.bounds = [], {}, []

    def font(self, family, weight):
        f = FONTS[family]
        return f, f.getGlyphSet(location={'wght': weight})

    def measure(self, text, size, weight=450, family='Manrope'):
        font, glyphs = self.font(family, weight)
        cmap, units = font.getBestCmap(), font['head'].unitsPerEm
        return sum(glyphs[cmap[ord(char)]].width for char in text) * size / units

    def text(self, text, x, y, size=18, weight=450, color='fg', family='Manrope', align='left'):
        font, glyphs = self.font(family, weight)
        cmap, units = font.getBestCmap(), font['head'].unitsPerEm
        width = self.measure(text, size, weight, family)
        x -= width if align == 'right' else width / 2 if align == 'center' else 0
        self.bounds.append((text, x, y - size, x + width, y + size * .25))
        cursor, uses = 0, []
        for char in text:
            if ord(char) not in cmap:
                raise ValueError(f'Missing glyph: {char!r}')
            name = cmap[ord(char)]
            key = f'{family}-{weight}-{ord(char)}'
            if key not in self.glyphs:
                pen = SVGPathPen(glyphs, ntos=lambda n: f'{n:.1f}'.rstrip('0').rstrip('.') if n else '0')
                glyphs[name].draw(pen)
                self.glyphs[key] = pen.getCommands()
            uses.append(f'<use href="#{key}" x="{cursor:.2f}"/>')
            cursor += glyphs[name].width
        self.parts.append(f'<g fill="{self.c.get(color, color)}" transform="translate({x:.2f} {y:.2f}) scale({size / units:.7f} {-size / units:.7f})">{"".join(uses)}</g>')
        return width

    def paragraph(self, text, x, y, width, size=18, leading=28, color='muted', weight=450):
        words, line = text.split(), ''
        for word in words:
            test = (line + ' ' + word).strip()
            if line and self.measure(test, size, weight) > width:
                self.text(line, x, y, size, weight, color)
                y += leading
                line = word
            else:
                line = test
        if line:
            self.text(line, x, y, size, weight, color)
            y += leading
        return y

    def line(self, x1, y1, x2, y2, color='line', width=1):
        self.parts.append(f'<path d="M{x1} {y1}H{x2}" stroke="{self.c[color]}" stroke-width="{width}"/>' if y1 == y2 else f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{self.c[color]}" stroke-width="{width}"/>')

    def circle(self, x, y, radius, color='accent', cls=''):
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{self.c[color]}" class="{cls}"/>')

    def arrow(self, x, y):
        self.parts.append(f'<path d="M{x-16} {y+16}L{x} {y}M{x-15} {y}H{x}V{y+15}" stroke="{self.c["accent"]}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')

    def finish(self, height, extra_style=''):
        for text, x1, y1, x2, y2 in self.bounds:
            assert x1 >= 20 and x2 <= self.width - 20, f'Text overflow: {text} {x1}..{x2}/{self.width}'
            assert y1 >= 16 and y2 <= height - 16, f'Vertical overflow: {text}'
        defs = ''.join(f'<path id="{key}" d="{path}"/>' for key, path in self.glyphs.items())
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{height}" viewBox="0 0 {self.width} {height}" role="img" aria-labelledby="title">
<title id="title">{escape(self.title)}</title>
<defs>{defs}</defs>
<style>.current{{animation:breathe 4s ease-in-out infinite}}@keyframes breathe{{0%,100%{{opacity:.55}}50%{{opacity:1}}}}{extra_style}@media(prefers-reduced-motion:reduce){{.current,.flow-signal{{animation:none!important}}.flow-signal{{display:none}}}}</style>
<rect x=".5" y=".5" width="{self.width-1}" height="{height-1}" rx="16" fill="{self.c['bg']}" stroke="{self.c['line']}"/>
{''.join(self.parts)}
</svg>'''


def heading(card, title, mobile):
    card.text(title, 26 if mobile else 44, 58, 27 if mobile else 30, 600, family='SpaceGrotesk')


def hero(theme, mobile):
    w, p = (480, 26) if mobile else (960, 44)
    c = Card(w, theme, f'{DATA["name"]}. {DATA["role"]}. CTO at A-Zentrix. {DATA["summary"]}')
    c.text(DATA['name'], p, 76 if mobile else 92, 35 if mobile else 49, 600, family='SpaceGrotesk')
    c.text(DATA['role'], p, 113 if mobile else 135, 18 if mobile else 22, 550)
    c.text(DATA['specialty'], p, 143 if mobile else 166, 17 if mobile else 18, color='muted')
    if mobile:
        c.text('CTO at A-Zentrix', p, 194, 20, 650, 'accent')
        c.text(DATA['location'], p, 225, 16, color='muted')
        c.line(p, 252, w-p, 252)
        c.text(DATA['headline'], p, 296, 25, 550, family='SpaceGrotesk')
        end = c.paragraph(DATA['summary'], p, 331, w-p*2, size=18, leading=28)
        flow_y = end + 28
    else:
        c.line(696, 53, 696, 258)
        c.text('CTO', 738, 94, 34, 600, 'accent', family='SpaceGrotesk')
        c.text('A-Zentrix', 738, 125, 19, 600)
        c.text('Erode, India', 738, 172, 17, color='muted')
        c.text('AI & Data Science', 738, 210, 17)
        c.text('IEEE Member', 738, 240, 16, color='muted')
        c.text(DATA['headline'], p, 226, 28, 550, family='SpaceGrotesk')
        end = c.paragraph(DATA['summary'], p, 260, 602, size=18, leading=28)
        flow_y = max(end + 38, 348)
    c.line(p, flow_y-27, w-p, flow_y-27)
    points = [p + 22 + i * (w - 2*p - 44)/3 for i in range(4)]
    c.line(points[0], flow_y, points[-1], flow_y)
    for x, label in zip(points, ('Context', 'Plan', 'Build', 'Validate')):
        c.circle(x, flow_y, 4)
        # End labels align inwards so the mobile artwork keeps its reading margin.
        align = 'left' if label == 'Context' else 'right' if label == 'Validate' else 'center'
        tx = p if label == 'Context' else w-p if label == 'Validate' else x
        c.text(label, tx, flow_y+33, 16 if mobile else 17, 550, color='muted', align=align)
    c.circle(points[0], flow_y, 6, cls='flow-signal')
    distance = points[-1] - points[0]
    style = f'.flow-signal{{animation:flow 10s linear infinite}}@keyframes flow{{0%{{transform:translateX(0);opacity:0}}5%{{opacity:1}}95%{{opacity:1}}100%{{transform:translateX({distance}px);opacity:0}}}}'
    return c.finish(round(flow_y+65), style)


def experience(theme, mobile):
    w, p, x = (480, 26, 54) if mobile else (960, 44, 84)
    c = Card(w, theme, 'Experience. ' + ' '.join(f'{e["role"]} at {e["organization"]}, {e["period"]}. {e["description"]}' for e in DATA['experience']))
    heading(c, 'Experience', mobile)
    y, circles = 118, []
    for i, e in enumerate(DATA['experience']):
        circles.append(y-8)
        c.text(e['role'], x, y, 21 if mobile else 24, 600, family='SpaceGrotesk')
        c.text(e['organization'], x, y+30, 18, 600, 'accent')
        if mobile:
            c.text(e['period'], w-26, y+30, 18, 500, 'muted', align='right')
        else:
            c.text(e['period'], w-44, y, 16, 500, 'muted', align='right')
        y = c.paragraph(e['description'], x, y+64, w-x-p, 18, 28) + 32
    c.line(p+4, circles[0], p+4, circles[-1], width=1)
    for i, cy in enumerate(circles):
        c.circle(p+4, cy, 5, color='accent' if i == 0 else 'muted', cls='current' if i == 0 else '')
    return c.finish(round(y))


def work_heading(theme, mobile):
    c = Card(480 if mobile else 960, theme, 'Selected engineering work. Open a project to view its repository.')
    heading(c, 'Selected work', mobile)
    if not mobile:
        c.text('Open a panel to explore the code', 916, 55, 17, color='muted', align='right')
    return c.finish(86)


def project(theme, mobile, item):
    w, p = (480, 26) if mobile else (960, 44)
    c = Card(w, theme, f'{item["name"]}. {item["description"]} {item["details"]}. {item["stack"]}. Open repository.')
    c.arrow(w-p-2, 31)
    y = c.paragraph(item['name'], p, 65, w-2*p-40, 27 if mobile else 30, 37, 'fg', 650)
    if mobile:
        c.text(item['category'], p, y+1, 15, 550, 'accent')
        y += 40
    else:
        c.text(item['category'], p, y-2, 15, 550, 'accent')
        y += 33
    y = c.paragraph(item['description'], p, y, w-p*2, 18, 28, 'fg')
    y = c.paragraph(item['details'], p, y+9, w-p*2, 17 if not mobile else 18, 27) + 2
    c.line(p, y+2, w-p, y+2)
    y = c.paragraph(item['stack'], p, y+32, w-p*2, 16 if not mobile else 17, 26, 'accent')
    return c.finish(round(y+13))


def toolkit(theme, mobile):
    w, p = (480, 26) if mobile else (960, 44)
    c = Card(w, theme, 'Technical toolkit. ' + '. '.join(f'{label}: {value}' for label, value in DATA['skills']))
    heading(c, 'Technical toolkit', mobile)
    y = 112
    for i, (label, value) in enumerate(DATA['skills']):
        c.text(label, p, y, 18, 650, 'fg')
        if mobile:
            y = c.paragraph(value, p, y+31, w-2*p, 18, 28) + 19
        else:
            y = c.paragraph(value, 248, y, w-p-248, 18, 28) + 22
        if i != len(DATA['skills'])-1:
            c.line(p, y-10, w-p, y-10)
        y += 19
    return c.finish(round(y+1))


def credentials(theme, mobile):
    w, p = (480, 26) if mobile else (960, 44)
    e = DATA['education']
    c = Card(w, theme, 'Education and credentials. ' + '. '.join(e.values()) + '. IEEE Member. ' + '. '.join(f'{provider}: {course}' for provider, course in DATA['certifications']))
    heading(c, 'Education & credentials', mobile)
    y = c.paragraph(e['degree'], p, 120, w-2*p if mobile else 450, 23, 34, 'fg', 600)
    y = c.paragraph(e['institution'], p, y+18, w-2*p if mobile else 450, 18, 28, 'fg', 550)
    y = c.paragraph(e['location'], p, y+4, w-2*p if mobile else 450, 17, 27)
    y = c.paragraph(e['period'], p, y+12, w-2*p if mobile else 450, 17, 27)
    c.text(DATA['membership'], p, y+25, 18, 650, 'accent')
    if mobile:
        c.line(p, y+53, w-p, y+53)
        cy, cx, width = y+100, p, w-p*2
    else:
        c.line(526, 104, 526, 451)
        cy, cx, width = 120, 562, 354
    c.text('Certifications', cx, cy, 22, 600, family='SpaceGrotesk')
    cy += 42
    for provider, course in DATA['certifications']:
        c.text(provider, cx, cy, 16, 650, 'accent')
        cy = c.paragraph(course, cx, cy+28, width, 17 if not mobile else 18, 27) + 21
    return c.finish(round(max(y+65, cy+3)))


def contact(theme, mobile):
    w, p = (480, 26) if mobile else (960, 44)
    c = Card(w, theme, 'Connect with Muruganandam. AI agents, GenAI applications, healthcare ML, and practical software systems.')
    c.text('Let’s build useful systems.', p, 58, 26 if mobile else 30, 550, family='SpaceGrotesk')
    y = c.paragraph('AI agents · GenAI applications · Healthcare ML', p, 94, w-2*p, 17, 27)
    return c.finish(round(y+15))


def picture(key, alt, revision, url=None):
    def path(variant):
        return f'./assets/resume/{key}-{variant}.svg?v={revision}'
    lines = [f'<a href="{escape(url, quote=True)}">'] if url else []
    lines += ['<picture>',
        f'  <source media="(max-width: 600px) and (prefers-color-scheme: dark)" srcset="{path("mobile-dark")}" />',
        f'  <source media="(max-width: 600px)" srcset="{path("mobile-light")}" />',
        f'  <source media="(prefers-color-scheme: dark)" srcset="{path("dark")}" />',
        f'  <img src="{path("light")}" width="960" alt="{escape(alt, quote=True)}" />',
        '</picture>']
    if url:
        lines += ['</a>']
    return '\n'.join(lines)


def text_resume():
    e = DATA['education']
    out = ['<details>', '<summary>Read the résumé as text</summary>', '', f'# {DATA["name"]}', '', f'**{DATA["role"]} · {DATA["specialty"]}**', '', DATA['location'], '', DATA['summary'], '', '## Experience', '']
    for job in DATA['experience']:
        out += [f'### {job["role"]} · {job["organization"]}', '', f'**{job["period"]}**', '', job['description'], '']
    out += ['## Selected work', '']
    for item in DATA['projects']:
        out += [f'### [{item["name"]}]({item["url"]})', '', f'**{item["category"]}**', '', item['description'], '', item['details'], '', f'**Stack:** {item["stack"]}', '']
    out += ['## Technical toolkit', '']
    out += [f'- **{label}:** {value}' for label, value in DATA['skills']]
    out += ['', '## Education & membership', '', f'**{e["degree"]}**', '', e['institution'], '', e['location'], '', e['period'], '', DATA['membership'], '', '## Certifications', '']
    out += [f'- **{provider}** — {course}' for provider, course in DATA['certifications']]
    return '\n'.join(out + ['', '</details>'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Check reproducibility, bounds, and asset references without writing')
    args = parser.parse_args()
    outputs = {}
    builders = {'hero': hero, 'experience': experience, 'selected-work': work_heading,
                'toolkit': toolkit, 'credentials': credentials, 'contact': contact}
    for item in DATA['projects']:
        builders[item['id']] = lambda theme, mobile, item=item: project(theme, mobile, item)
    for key, builder in builders.items():
        for mobile in (False, True):
            for theme in PALETTES:
                variant = f'mobile-{theme}' if mobile else theme
                svg = builder(theme, mobile)
                ElementTree.fromstring(svg)
                assert '<script' not in svg and '<image' not in svg
                outputs[f'assets/resume/{key}-{variant}.svg'] = svg
    revision = hashlib.sha256(''.join(outputs.values()).encode()).hexdigest()[:10]
    blocks = [picture('hero', f'{DATA["name"]} — {DATA["role"]}, CTO at A-Zentrix. {DATA["summary"]}', revision),
              picture('experience', 'Experience: CTO at A-Zentrix; TuneEng Team Lead, 2025–2026; AI and Full-Stack Student Project Developer, 2023–Present.', revision),
              picture('selected-work', 'Selected work. Open each project panel to explore its repository.', revision)]
    for item in DATA['projects']:
        blocks.append(picture(item['id'], f'{item["name"]} — {item["description"]} {item["details"]}. {item["stack"]}. Open repository.', revision, item['url']))
    blocks += [picture('toolkit', 'Technical toolkit: Python, JavaScript, TypeScript, SQL, AI orchestration, machine learning, computer vision, web development, data, and delivery. Full list in the text résumé.', revision),
               picture('credentials', 'B.Tech AI and Data Science, Nandha Engineering College, 2024–2028 expected. IEEE Member. Certifications from LinkedIn Learning, Great Learning, SWAYAM, and IBM Cognitive Class.', revision),
               picture('contact', 'Let’s build useful systems. AI agents, GenAI applications, and healthcare ML.', revision)]
    links = f'<a href="{DATA["linkedin"]}">LinkedIn</a> · <a href="mailto:{DATA["email"]}">Email</a> · <a href="{DATA["github"]}?tab=repositories">Repositories</a>'
    activity = '\n'.join(['<details>', '<summary>GitHub activity</summary>', '', '<p align="center">',
        f'<a href="{DATA["github"]}"><img src="https://github-profile-summary-cards.vercel.app/api/cards/profile-details?username=MuruganandamMG&theme=tokyonight" width="960" alt="MuruganandamMG GitHub contribution activity" /></a>', '</p>', '', '</details>'])
    outputs['README.md'] = '<!-- Generated from resume.json by tools/build_resume.py. -->\n\n' + '\n\n'.join(blocks) + '\n\n<p align="center">' + links + '</p>\n\n' + text_resume() + '\n\n' + activity + '\n'
    assert all(item['name'] in outputs['README.md'] for item in DATA['projects'])
    assert '9789649059' not in outputs['README.md']
    assert 'prefers-reduced-motion' in outputs['assets/resume/hero-dark.svg']
    stale = []
    for relative, content in outputs.items():
        path = ROOT / relative
        if args.check:
            if not path.exists() or path.read_text(encoding='utf-8') != content:
                stale.append(relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8', newline='\n')
    assert not stale, f'Regenerate stale files: {stale}'
    print(f'{"Verified" if args.check else "Built"} {len(outputs)-1} SVGs and README; all text fits; revision {revision}.')


if __name__ == '__main__':
    main()
