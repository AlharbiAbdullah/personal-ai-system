"""Excalidraw scene helpers for /media → diagram.

A scene script builds a Scene, places zones, parts, tools and labelled arrows, calls
save(name), then render(out_dir, *names). render.mjs turns each saved skeleton into
out_dir/<name>.excalidraw.svg: an SVG that GitHub shows and excalidraw.com opens.

Logo keys fetch themselves into ~/.cache/rai-diagram/logos on first use:
  si:<slug>               simple-icons, brand colour        si:duckdb
  si:<slug>#RRGGBB        simple-icons, this colour         si:dbt#FF694B
  si:<slug>+#RRGGBB       brand icon on a rounded tile      si:ruff+#261230
  gh:<owner>              GitHub avatar, rounded corners    gh:rilldata
  url:<https URL>         any SVG or PNG, trimmed, square   url:https://.../logo.svg
"""

import base64
import json
import os
import re
import shutil
import subprocess
import urllib.request
import uuid
from pathlib import Path

CACHE = Path.home() / ".cache" / "rai-diagram" / "logos"
# One folder per run, so two repos or two sessions never render each other's scene.
SCENES = Path.home() / ".cache" / "rai-diagram" / "scenes" / uuid.uuid4().hex
RENDER = Path(__file__).with_name("render.mjs")
MONO, EXCALIFONT, NUNITO = 3, 5, 6

# The house style: Seattle Standard.
INK, MUTED, DASH, PART, VIOLET = "#212529", "#868e96", "#ced4da", "#495057", "#7048e8"
LOGO, NAME_FS, ARROW_FS = 72, 20, 18


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "rai-diagram"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        return resp.read()


def _square_png(src: Path, out: Path) -> None:
    """Trim the transparent margin and pad to a square, so every logo fills its box."""
    subprocess.run(
        ["magick", str(src), "-trim", "+repage", "-background", "none", "-gravity",
         "center", "-extent", "%[fx:max(w,h)]x%[fx:max(w,h)]", str(out)],
        check=True)


def fetch_logo(key: str) -> Path:
    """Fetch once into the cache. Builds in a private folder and renames into place, so
    parallel renders never read a half-written logo."""
    CACHE.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^\w.-]", "_", key)
    for suffix in (".svg", ".png"):
        hit = CACHE / f"{name}{suffix}"
        if hit.exists():
            return hit
    work = CACHE / f".tmp-{uuid.uuid4().hex}"
    work.mkdir()
    try:
        built = _build_logo(key, name, work)
        final = CACHE / built.name
        os.replace(built, final)
        return final
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _build_logo(key: str, name: str, CACHE: Path) -> Path:  # noqa: N803
    kind, _, ref = key.partition(":")
    if kind == "si":
        slug, tile = ref.split("+", 1) if "+" in ref else (ref, None)
        slug, colour = slug.split("#", 1) if "#" in slug else (slug, None)
        if colour:
            svg = _get(f"https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{slug}.svg")
            svg = svg.decode().replace("<svg ", f'<svg fill="#{colour}" ', 1)
        else:
            svg = _get(f"https://cdn.simpleicons.org/{slug}").decode()
        if tile:
            path = re.search(r'<path d="[^"]+"', svg).group(0)
            fill = re.search(r'fill="(#[0-9A-Fa-f]{6})"', svg).group(1)
            svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
                   f'<rect width="32" height="32" rx="6" fill="{tile}"/>'
                   f'<g transform="translate(4 4)" fill="{fill}">{path}/></g></svg>')
        out = CACHE / f"{name}.svg"
        out.write_text(svg)
        return out
    if kind == "gh":
        raw = CACHE / f"{name}.raw.png"
        raw.write_bytes(_get(f"https://github.com/{ref}.png?size=128"))
        out = CACHE / f"{name}.png"
        subprocess.run(
            ["magick", str(raw), "-resize", "128x128!", "(", "+clone", "-alpha", "extract",
             "-fill", "black", "-colorize", "100", "-fill", "white", "-draw",
             "roundrectangle 0,0 127,127 22,22", ")", "-alpha", "off", "-compose",
             "CopyOpacity", "-composite", str(out)], check=True)
        raw.unlink()
        return out
    if kind == "url":
        data = _get(ref)
        raw = CACHE / f"{name}.dl"  # not .raw: magick reads that as camera RAW
        raw.write_bytes(data)
        if data.lstrip()[:5] in (b"<?xml", b"<svg ") or ref.endswith(".svg"):
            png = CACHE / f"{name}.big.png"
            subprocess.run(["rsvg-convert", "-w", "512", str(raw), "-o", str(png)], check=True)
            raw.unlink()
            raw = png
        out = CACHE / f"{name}.png"
        _square_png(raw, out)
        raw.unlink()
        return out
    raise ValueError(f"unknown logo key: {key}")


class Scene:
    def __init__(self, background="#ffffff", font=NUNITO, ink=INK):
        self.els, self.files, self.n = [], {}, 0
        self.bg, self.font, self.ink = background, font, ink

    def _id(self, prefix):
        self.n += 1
        return f"{prefix}{self.n}"

    def rect(self, x, y, w, h, stroke=None, bg="transparent", sw=2, dashed=False,
             dotted=False, label=None, fs=20, color=None, align="center", valign="middle",
             ff=None):
        el = {"type": "rectangle", "id": self._id("r"), "x": x, "y": y, "width": w,
              "height": h, "strokeColor": stroke or self.ink, "backgroundColor": bg,
              "fillStyle": "solid", "strokeWidth": sw,
              "strokeStyle": "dashed" if dashed else "dotted" if dotted else "solid",
              "roughness": 0, "roundness": {"type": 3}}
        if label is not None:
            el["label"] = {"text": label, "fontSize": fs, "fontFamily": ff or self.font,
                           "strokeColor": color or self.ink, "textAlign": align,
                           "verticalAlign": valign}
        self.els.append(el)
        return el

    def text(self, x, y, w, h, s, fs=20, color=None, align="center", ff=None):
        """Text in an invisible box, so it lands centred (or aligned) where it is meant to."""
        return self.rect(x, y, w, h, stroke="transparent", label=s, fs=fs, color=color,
                         align=align, ff=ff)

    def zone(self, x, y, w, h, title, dotted=False):
        """A dashed grey zone with its title top-left. dotted=True for an environment box."""
        self.rect(x, y, w, h, stroke=PART if dotted else DASH, sw=2.5 if dotted else 2,
                  dashed=not dotted, dotted=dotted)
        if title:
            self.text(x + 18, y + 10, w - 36, 30, title, fs=18, color=MUTED, align="left")

    def part(self, x, y, w, h, label, fs=20):
        """A component box inside a zone: the architecture diagram's building block."""
        return self.rect(x, y, w, h, stroke=PART, bg="#ffffff", sw=1.5, label=label, fs=fs)

    def _file(self, key):
        path = fetch_logo(key)
        data = path.read_bytes()
        if path.suffix == ".svg":
            svg = data.decode()
            if not re.search(r"<svg[^>]*\swidth=", svg):
                svg = svg.replace("<svg ", '<svg width="256" height="256" ', 1)
            data, mime = svg.encode(), "image/svg+xml"
        else:
            mime = "image/png"
        fid = re.sub(r"\W", "_", key)
        self.files[fid] = {"id": fid, "mimeType": mime, "created": 1,
                           "dataURL": f"data:{mime};base64,{base64.b64encode(data).decode()}"}
        return fid

    def img(self, x, y, size, key):
        self.els.append({"type": "image", "id": self._id("i"), "x": x, "y": y,
                         "width": size, "height": size, "fileId": self._file(key),
                         "status": "saved", "scale": [1, 1]})

    def tool(self, cx, top, key, name, size=LOGO, w=130):
        """The tech stack's building block: a logo with its name below, centred on cx."""
        self.img(cx - size / 2, top, size, key)
        self.text(cx - w / 2, top + size + 6, w, NAME_FS * 1.4, name, fs=NAME_FS)

    def arrow(self, pts, color=None, sw=2.5, dashed=False, label=None, at=None):
        """An arrow through pts. label names the action; at=(x, y, w) places it."""
        x0, y0 = pts[0]
        self.els.append({"type": "arrow", "id": self._id("a"), "x": x0, "y": y0,
                         "points": [[px - x0, py - y0] for px, py in pts],
                         "strokeColor": color or self.ink, "strokeWidth": sw,
                         "roughness": 0, "strokeStyle": "dashed" if dashed else "solid",
                         "endArrowhead": "triangle", "roundness": None})
        if label:
            lx, ly, lw = at
            self.text(lx, ly, lw, 50, label, fs=ARROW_FS, color=color or self.ink)

    def save(self, name):
        """Write the skeleton to the scene cache; render() turns it into an SVG."""
        SCENES.mkdir(parents=True, exist_ok=True)
        path = SCENES / f"{name}.json"
        path.write_text(json.dumps(
            {"skeleton": self.els, "files": self.files, "background": self.bg}))
        return path


def render(out_dir, *names):
    """Render saved scenes to out_dir/<name>.excalidraw.svg, previews beside the scenes."""
    subprocess.run(["node", str(RENDER), str(out_dir),
                    *[str(SCENES / f"{n}.json") for n in names]], check=True)
