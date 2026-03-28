from __future__ import annotations

import re
import ssl
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont


SPAN_RE = re.compile(r'<span class="xuetangx-com-encrypted-font">(.*?)</span>')
DEFAULT_REF_FONT_URL = (
    "https://github.com/adobe-fonts/source-han-sans/raw/release/Variable/TTF/"
    "SourceHanSansSC-VF.ttf"
)
WINDOWS_REF_FONTS = (
    Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
    Path(r"C:\Windows\Fonts\SourceHanSansSC-VF.ttf"),
)

_REFERENCE_FONT_CACHE: dict[tuple[str, int], "ReferenceFont"] = {}


def is_cjk(cp: int) -> bool:
    return 0x4E00 <= cp <= 0x9FFF


def resolve_workdir(workdir: Path | str | None = None) -> Path:
    if workdir is None:
        path = Path(tempfile.gettempdir()) / "autoyuketang_exam_fonts"
    else:
        path = Path(workdir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def download_file(url: str, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    context = ssl._create_unverified_context()
    with urllib.request.urlopen(url, context=context) as response:
        target.write_bytes(response.read())
    return target


def resolve_reference_font(workdir: Path) -> Path:
    local_candidates = (
        workdir / "SourceHanSansSC-VF.ttf",
        workdir / "NotoSansSC-VF.ttf",
    )
    for candidate in local_candidates:
        if candidate.exists():
            return candidate

    for candidate in WINDOWS_REF_FONTS:
        if candidate.exists():
            return candidate

    target = workdir / "SourceHanSansSC-VF.ttf"
    return download_file(DEFAULT_REF_FONT_URL, target)


def font_file_name(font_url: str) -> str:
    return font_url.rstrip("/").rsplit("/", 1)[-1]


def ensure_exam_font(font_url: str, workdir: Path) -> Path:
    target = workdir / font_file_name(font_url)
    if target.exists():
        return target
    return download_file(font_url, target)


def render_bits(
    char: str,
    font: ImageFont.FreeTypeFont,
    canvas: int = 128,
    out_size: int = 64,
) -> int:
    image = Image.new("L", (canvas, canvas), 255)
    draw = ImageDraw.Draw(image)
    bbox = draw.textbbox((0, 0), char, font=font)
    if bbox is None:
        raise ValueError(f"Unable to render character: {char!r}")

    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = (canvas - width) // 2 - bbox[0]
    y = (canvas - height) // 2 - bbox[1]
    draw.text((x, y), char, fill=0, font=font)

    content_bbox = image.getbbox()
    if content_bbox is None:
        raise ValueError(f"Rendered image was blank for character: {char!r}")

    crop = image.crop(content_bbox).resize((out_size, out_size))
    binary = crop.point(lambda pixel: 0 if pixel > 200 else 255, mode="1")
    return int.from_bytes(binary.tobytes(), "big")


@dataclass
class ReferenceFont:
    path: Path
    font: ImageFont.FreeTypeFont
    bitmaps: dict[int, int]

    @classmethod
    def load(cls, path: Path, size: int = 96) -> "ReferenceFont":
        font = ImageFont.truetype(str(path), size)
        cmap = TTFont(str(path))["cmap"].getcmap(3, 1).cmap
        codepoints = sorted({cp for cp in cmap if is_cjk(cp)})
        bitmaps = {cp: render_bits(chr(cp), font) for cp in codepoints}
        return cls(path=path, font=font, bitmaps=bitmaps)


class ExamFontDecoder:
    def __init__(
        self,
        exam_font_path: Path,
        reference_font: ReferenceFont,
        size: int = 96,
    ) -> None:
        self.path = exam_font_path
        self.font = ImageFont.truetype(str(exam_font_path), size)
        self.reference_font = reference_font
        self._char_cache: dict[str, str] = {}

    def decode_char(self, char: str) -> str:
        if char in self._char_cache:
            return self._char_cache[char]

        target_bits = render_bits(char, self.font)
        best_codepoint = min(
            self.reference_font.bitmaps,
            key=lambda cp: (target_bits ^ self.reference_font.bitmaps[cp]).bit_count(),
        )
        decoded = chr(best_codepoint)
        self._char_cache[char] = decoded
        return decoded

    def decode_spans(self, text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            return "".join(self.decode_char(char) for char in match.group(1))

        return SPAN_RE.sub(replace, text)

    def mapping(self) -> dict[str, str]:
        return dict(sorted(self._char_cache.items(), key=lambda item: item[0]))


def decode_object(obj: Any, decoder: ExamFontDecoder) -> Any:
    if isinstance(obj, str):
        return decoder.decode_spans(obj) if "xuetangx-com-encrypted-font" in obj else obj
    if isinstance(obj, list):
        return [decode_object(item, decoder) for item in obj]
    if isinstance(obj, dict):
        return {key: decode_object(value, decoder) for key, value in obj.items()}
    return obj


def get_reference_font(workdir: Path, size: int = 96) -> ReferenceFont:
    path = resolve_reference_font(workdir)
    cache_key = (str(path.resolve()), size)
    if cache_key not in _REFERENCE_FONT_CACHE:
        _REFERENCE_FONT_CACHE[cache_key] = ReferenceFont.load(path, size)
    return _REFERENCE_FONT_CACHE[cache_key]


def decode_exercise_payload(
    payload: dict[str, Any],
    workdir: Path | str | None = None,
    size: int = 96,
) -> tuple[dict[str, Any], dict[str, str]]:
    font_url = payload.get("data", {}).get("font")
    if not font_url:
        raise ValueError("Exercise payload does not include a font URL")

    resolved_workdir = resolve_workdir(workdir)
    reference_font = get_reference_font(resolved_workdir, size=size)
    exam_font_path = ensure_exam_font(font_url, resolved_workdir)
    decoder = ExamFontDecoder(exam_font_path, reference_font, size=size)
    decoded = decode_object(payload, decoder)
    return decoded, decoder.mapping()
