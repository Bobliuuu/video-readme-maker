from .theme import FONT, MONO, esc


def hero_svg(title, subtitle, chips, th, w=1200, h=360):
    """Gradient title card, no external fonts, subtle animated sweep."""
    cs = [th["accent"], th["accent2"], th["accent3"]]
    fs = 68 if len(title) <= 22 else max(36, int(68 * 22 / len(title)))
    chip_svg, x = "", 70
    for i, c in enumerate(chips[:5]):
        col = cs[i % 3]
        chip_svg += f'<text x="{x}" y="290" fill="{col}">● {esc(c)}</text>'
        x += 40 + 11 * len(c)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(title)}: {esc(subtitle)}">
<defs>
<linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="{cs[0]}"/><stop offset=".55" stop-color="{cs[1]}"/><stop offset="1" stop-color="{cs[2]}"/></linearGradient>
<radialGradient id="glow"><stop offset="0" stop-color="{cs[0]}" stop-opacity=".35"/><stop offset="1" stop-color="{cs[0]}" stop-opacity="0"/></radialGradient>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{th["line"]}" stroke-width="1" opacity=".55"/></pattern>
<linearGradient id="sweep" x1="0" x2="1"><stop offset="0" stop-color="{cs[0]}" stop-opacity="0"/><stop offset=".5" stop-color="{cs[0]}" stop-opacity=".4"/><stop offset="1" stop-color="{cs[0]}" stop-opacity="0"/></linearGradient>
</defs>
<rect width="{w}" height="{h}" rx="18" fill="{th["bg"]}"/><rect width="{w}" height="{h}" rx="18" fill="url(#grid)"/>
<circle cx="{w-170}" cy="70" r="260" fill="url(#glow)"/>
<rect y="0" width="260" height="{h}" fill="url(#sweep)" opacity=".5"><animateTransform attributeName="transform" type="translate" from="-300 0" to="{w+100} 0" dur="7s" repeatCount="indefinite"/></rect>
<text x="64" y="176" font-family="{FONT}" font-weight="800" font-size="{fs}" letter-spacing="-1" fill="url(#g)">{esc(title)}</text>
<text x="70" y="232" font-family="{MONO}" font-size="26" fill="{th["text"]}">{esc(subtitle)}</text>
<g font-family="{MONO}" font-size="17">{chip_svg}</g>
<rect x="64" y="318" width="{w-128}" height="3" rx="1.5" fill="url(#g)" opacity=".8"/>
</svg>'''
