from __future__ import annotations

import hashlib
import html
import json
import logging
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.cookiejar import CookieJar
from io import BytesIO
from pathlib import Path
from typing import Any

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

from .models import Dialogue, DialogueIllustration


logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
ALLOWED_IMAGE_MIME_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
ALLOWED_PIL_FORMATS = {
    "JPEG": "jpg",
    "PNG": "png",
    "WEBP": "webp",
}
MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_PAYLOAD_BYTES = 64 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_IMAGE_BYTES = 60 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGES = 20
MAX_LITERATURE_CHARS = 20_000
RETRIEVAL_MARKER_PREFIXES = (
    "http://googleusercontent.com/image_collection/image_retrieval/",
    "https://googleusercontent.com/image_collection/image_retrieval/",
    "http://googleusercontent.com/image_agent_tag_",
    "https://googleusercontent.com/image_agent_tag_",
)
RETRIEVAL_PREVIEW_HOST_RE = re.compile(r"^encrypted-tbn\d+\.gstatic\.com$")
IMAGE_TAG_RE = re.compile(r"<Image\b(?P<attributes>[^>]*)>", re.IGNORECASE)
IMAGE_TAG_ATTRIBUTE_RE = re.compile(
    r'\b(?P<name>src|caption|alt)="(?P<value>[^"]*)"',
    re.IGNORECASE,
)
LITERATURE_HEADING_TITLES = (
    # Ukrainian
    "рекомендована література",
    "рекомендована література та джерела",
    "рекомендовані джерела",
    "рекомендовані джерела та література",
    "рекомендовані матеріали",
    "рекомендовані ресурси",
    "список рекомендованої літератури",
    "список літератури",
    "список джерел",
    "список використаних джерел",
    "джерела та література",
    "література та джерела",
    "використані джерела",
    "додаткова література",
    "матеріали для подальшого читання",
    "для подальшого читання",
    "бібліографія",
    "література",
    "джерела",
    # Russian
    "рекомендованная литература",
    "рекомендованная литература и источники",
    "рекомендуемая литература",
    "рекомендуемая литература и источники",
    "рекомендованные источники",
    "рекомендуемые источники",
    "рекомендованные материалы",
    "рекомендуемые материалы",
    "рекомендованные ресурсы",
    "рекомендуемые ресурсы",
    "список рекомендованной литературы",
    "список рекомендуемой литературы",
    "список литературы",
    "список источников",
    "список использованных источников",
    "источники и литература",
    "литература и источники",
    "использованные источники",
    "дополнительная литература",
    "материалы для дальнейшего чтения",
    "для дальнейшего чтения",
    "библиография",
    "литература",
    "источники",
    # English
    "recommended reading",
    "recommended literature",
    "recommended sources",
    "recommended resources",
    "recommended books",
    "suggested reading",
    "suggested literature",
    "suggested sources",
    "suggested resources",
    "further reading",
    "additional reading",
    "reading list",
    "reference list",
    "selected bibliography",
    "literature and sources",
    "sources and references",
    "books and resources",
    "works cited",
    "bibliography",
    "references",
    "sources",
)
LITERATURE_HEADING_TITLE_PATTERN = "|".join(
    re.escape(title).replace(r"\ ", r"[ \t]+")
    for title in sorted(LITERATURE_HEADING_TITLES, key=len, reverse=True)
)
LITERATURE_HEADING_RE = re.compile(
    r"^[ \t]*(?:(?P<hashes>#{1,6})[ \t]+)?"
    r"(?:(?:\d+(?:\.\d+)*)[.)]?[ \t]+)?"
    r"(?:[📚📖🔗][ \t]*)?(?:\*\*|__)?[ \t]*"
    rf"(?:{LITERATURE_HEADING_TITLE_PATTERN})"
    r"(?:[ \t]+\([^()\r\n]{1,120}\))?[ \t]*"
    r"(?::[ \t]*)?(?:\*\*|__)?[ \t]*(?::[ \t]*)?$",
    re.IGNORECASE | re.MULTILINE,
)
MARKDOWN_HEADING_RE = re.compile(
    r"^[ \t]{0,3}(?P<hashes>#{1,6})[ \t]+\S.*$",
    re.MULTILINE,
)


class GeminiIllustrationImportError(RuntimeError):
    pass


@dataclass(frozen=True)
class HttpResponse:
    body: bytes
    content_type: str
    final_url: str


@dataclass(frozen=True)
class GeminiImageAsset:
    url: str
    filename: str
    declared_type: str
    width: int
    height: int
    kind: str
    turn_index: int
    position: int
    caption: str


@dataclass(frozen=True)
class DownloadedImage:
    body: bytes
    extension: str
    digest: str


@dataclass(frozen=True)
class GeminiIllustrationImportResult:
    found: int
    imported: int
    skipped_duplicates: int
    failed: int
    literature_found: bool = False
    literature_imported: bool = False


class GeminiHttpClient:
    def __init__(self, timeout: float = 40.0, user_agent: str = DEFAULT_USER_AGENT):
        self.timeout = timeout
        self.user_agent = user_agent
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )

    def request(
        self,
        url: str,
        *,
        method: str = "GET",
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        accept: str = "*/*",
        referer: str | None = None,
        max_bytes: int,
    ) -> HttpResponse:
        request_headers = {
            "User-Agent": self.user_agent,
            "Accept": accept,
            "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        if referer:
            request_headers["Referer"] = referer
        if headers:
            request_headers.update(headers)

        request = urllib.request.Request(
            url,
            data=data,
            headers=request_headers,
            method=method,
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                declared_length = response.headers.get("Content-Length")
                if declared_length and int(declared_length) > max_bytes:
                    raise GeminiIllustrationImportError(
                        f"Remote response exceeds the {max_bytes}-byte limit."
                    )
                body = response.read(max_bytes + 1)
                if len(body) > max_bytes:
                    raise GeminiIllustrationImportError(
                        f"Remote response exceeds the {max_bytes}-byte limit."
                    )
                return HttpResponse(
                    body=body,
                    content_type=(response.headers.get_content_type() or "").lower(),
                    final_url=response.geturl(),
                )
        except GeminiIllustrationImportError:
            raise
        except Exception as exc:
            raise GeminiIllustrationImportError(
                f"Gemini request failed: {exc}"
            ) from exc

    def get_text(self, url: str, *, max_bytes: int) -> str:
        response = self.request(
            url,
            accept="text/html,application/xhtml+xml,*/*",
            max_bytes=max_bytes,
        )
        return response.body.decode("utf-8", errors="replace")

    def post_form(
        self,
        url: str,
        form: dict[str, str],
        *,
        referer: str,
        max_bytes: int,
    ) -> str:
        encoded = urllib.parse.urlencode(form).encode("utf-8") + b"&"
        parsed = urllib.parse.urlparse(url)
        origin = urllib.parse.urlunparse(
            parsed._replace(path="", params="", query="", fragment="")
        )
        response = self.request(
            url,
            method="POST",
            data=encoded,
            accept="*/*",
            referer=referer,
            max_bytes=max_bytes,
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                "Origin": origin,
                "X-Same-Domain": "1",
            },
        )
        return response.body.decode("utf-8", errors="replace")


def is_gemini_share_url(value: str) -> bool:
    parsed = urllib.parse.urlparse((value or "").strip())
    hostname = (parsed.hostname or "").lower().rstrip(".")
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme not in {"http", "https"}:
        return False
    if hostname in {"gemini.google.com", "www.gemini.google.com"}:
        return len(parts) >= 2 and parts[0] == "share"
    if hostname == "g.co":
        return len(parts) >= 3 and parts[:2] == ["gemini", "share"]
    if hostname == "share.gemini.google":
        return (
            len(parts) == 1
            and bool(re.fullmatch(r"[A-Za-z0-9_-]+", parts[0]))
        )
    return False


def _parse_direct_gemini_share_url(value: str) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(value.strip())
    hostname = (parsed.hostname or "").lower().rstrip(".")
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme not in {"http", "https"}:
        raise GeminiIllustrationImportError(
            "Only public Gemini share links can import illustrations."
        )
    if hostname in {"gemini.google.com", "www.gemini.google.com"}:
        if len(parts) < 2 or parts[0] != "share":
            raise GeminiIllustrationImportError(
                "Gemini short link redirected to an unsupported page."
            )
        share_id = parts[1]
    elif hostname == "g.co":
        if len(parts) < 3 or parts[:2] != ["gemini", "share"]:
            raise GeminiIllustrationImportError(
                "Only public Gemini share links can import illustrations."
            )
        share_id = parts[2]
    else:
        raise GeminiIllustrationImportError(
            "Gemini short link redirected to an unsupported host."
        )
    if not re.fullmatch(r"[A-Za-z0-9_-]+", share_id):
        raise GeminiIllustrationImportError("Invalid Gemini share identifier.")
    clean_url = f"https://gemini.google.com/share/{share_id}"
    return share_id, clean_url


def _parse_gemini_share_url(
    value: str,
    *,
    client: GeminiHttpClient | None = None,
) -> tuple[str, str]:
    if not is_gemini_share_url(value):
        raise GeminiIllustrationImportError(
            "Only public Gemini share links can import illustrations."
        )
    parsed = urllib.parse.urlparse(value.strip())
    hostname = (parsed.hostname or "").lower().rstrip(".")
    if hostname != "share.gemini.google":
        return _parse_direct_gemini_share_url(value)

    client = client or GeminiHttpClient()
    response = client.request(
        value.strip(),
        accept="text/html,application/xhtml+xml,*/*",
        max_bytes=MAX_PAGE_BYTES,
    )
    return _parse_direct_gemini_share_url(response.final_url)


def canonical_gemini_share_url(
    value: str,
    *,
    client: GeminiHttpClient | None = None,
) -> str:
    return _parse_gemini_share_url(value, client=client)[1]


def _extract_wiz_value(raw_html: str, key: str) -> str:
    match = re.search(rf'"{re.escape(key)}"\s*:\s*"([^"]+)"', raw_html)
    if not match:
        raise GeminiIllustrationImportError(
            f"Gemini page metadata {key} was not found."
        )
    return match.group(1)


def _parse_batchexecute_response(raw: str, rpcid: str) -> Any:
    for line in raw.splitlines():
        if not line.startswith("[["):
            continue
        try:
            rows = json.loads(line)
        except json.JSONDecodeError:
            continue
        for row in rows:
            if (
                isinstance(row, list)
                and len(row) >= 3
                and row[0] == "wrb.fr"
                and row[1] == rpcid
            ):
                return None if row[2] is None else json.loads(row[2])
    raise GeminiIllustrationImportError(
        "Gemini conversation payload was not found."
    )


def fetch_gemini_payload(
    source_url: str,
    *,
    client: GeminiHttpClient,
) -> tuple[str, str, Any]:
    share_id, clean_url = _parse_gemini_share_url(source_url, client=client)
    raw_html = client.get_text(clean_url, max_bytes=MAX_PAGE_BYTES)
    build_label = _extract_wiz_value(raw_html, "cfb2h")
    session_id = _extract_wiz_value(raw_html, "FdrFJe")
    rpcid = "ujx1Bf"
    query = urllib.parse.urlencode(
        {
            "rpcids": rpcid,
            "source-path": f"/share/{share_id}",
            "bl": build_label,
            "f.sid": session_id,
            "hl": "uk-UA",
            "_reqid": "325091",
            "rt": "c",
        }
    )
    endpoint = (
        "https://gemini.google.com/_/BardChatUi/data/batchexecute?"
        f"{query}"
    )
    request_data = json.dumps(
        [[[
            rpcid,
            json.dumps([None, share_id, [4]], separators=(",", ":")),
            None,
            "generic",
        ]]],
        separators=(",", ":"),
    )
    raw_payload = client.post_form(
        endpoint,
        {"f.req": request_data},
        referer=clean_url,
        max_bytes=MAX_PAYLOAD_BYTES,
    )
    return share_id, clean_url, _parse_batchexecute_response(raw_payload, rpcid)


def _iter_lists(value: Any):
    if isinstance(value, list):
        yield value
        for child in value:
            yield from _iter_lists(child)
    elif isinstance(value, dict):
        for child in value.values():
            yield from _iter_lists(child)


def _normalize_prompt_text(prompt: Any) -> str:
    if not isinstance(prompt, list) or not prompt or not isinstance(prompt[0], list):
        return ""
    text = " ".join(item for item in prompt[0] if isinstance(item, str))
    return re.sub(r"\s+", " ", text).strip()


def _gemini_image_host_is_allowed(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    return (
        parsed.scheme == "https"
        and (
            hostname == "googleusercontent.com"
            or hostname.endswith(".googleusercontent.com")
        )
    )


def _retrieval_preview_url_is_allowed(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    return (
        parsed.scheme == "https"
        and bool(RETRIEVAL_PREVIEW_HOST_RE.fullmatch(hostname))
        and parsed.path == "/images"
    )


def _wikimedia_raster_url_is_allowed(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    hostname = (parsed.hostname or "").lower().rstrip(".")
    suffix = Path(urllib.parse.unquote(parsed.path)).suffix.lower()
    return (
        parsed.scheme == "https"
        and hostname == "upload.wikimedia.org"
        and suffix in {".jpg", ".jpeg", ".png", ".webp"}
    )


def _download_image_host_is_allowed(value: str) -> bool:
    return (
        _gemini_image_host_is_allowed(value)
        or _retrieval_preview_url_is_allowed(value)
        or _wikimedia_raster_url_is_allowed(value)
    )


def _asset_from_record(
    record: list[Any],
    *,
    expected_kind: int,
    turn_index: int,
    position: int,
    caption: str,
) -> GeminiImageAsset | None:
    if len(record) < 16 or type(record[8]) is not int or record[8] != expected_kind:
        return None
    filename = record[2]
    url = record[3]
    declared_type = record[11]
    dimensions = record[15]
    if (
        not isinstance(filename, str)
        or not isinstance(url, str)
        or not _gemini_image_host_is_allowed(url)
        or declared_type not in ALLOWED_IMAGE_MIME_TYPES
        or not isinstance(dimensions, list)
        or len(dimensions) < 2
        or type(dimensions[0]) is not int
        or type(dimensions[1]) is not int
        or dimensions[0] <= 0
        or dimensions[1] <= 0
    ):
        return None
    return GeminiImageAsset(
        url=url,
        filename=filename,
        declared_type=declared_type,
        width=dimensions[0],
        height=dimensions[1],
        kind="uploaded" if expected_kind == 1 else "generated",
        turn_index=turn_index,
        position=position,
        caption=caption,
    )


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for child in value:
            yield from _iter_strings(child)
    elif isinstance(value, dict):
        for child in value.values():
            yield from _iter_strings(child)


def _literature_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    for match in LITERATURE_HEADING_RE.finditer(text):
        heading_level = len(match.group("hashes") or "")
        end = len(text)
        for next_heading in MARKDOWN_HEADING_RE.finditer(text, match.end()):
            next_level = len(next_heading.group("hashes"))
            if heading_level == 0 or next_level <= heading_level:
                end = next_heading.start()
                break
        block = text[match.end():end].strip()
        if block:
            blocks.append(block[:MAX_LITERATURE_CHARS].rstrip())
    return blocks


def extract_gemini_recommended_literature(payload: Any) -> str:
    root = payload[0] if isinstance(payload, list) and payload else None
    turns = root[1] if isinstance(root, list) and len(root) > 1 else None
    if not isinstance(turns, list):
        return ""

    latest = ""
    for turn in turns:
        if not isinstance(turn, list) or len(turn) < 4:
            continue
        turn_blocks: list[str] = []
        seen_blocks: set[str] = set()
        for text in _iter_strings(turn[3]):
            for block in _literature_blocks(text):
                if block not in seen_blocks:
                    turn_blocks.append(block)
                    seen_blocks.add(block)
        if turn_blocks:
            # Gemini repeats the response in raw and structured forms. The raw
            # form contains the complete block and is normally the longest one.
            latest = max(turn_blocks, key=len)
    return latest


def _inline_image_labels(value: Any) -> dict[str, str]:
    labels: dict[str, str] = {}
    for text in _iter_strings(value):
        for tag_match in IMAGE_TAG_RE.finditer(text):
            attributes = {
                match.group("name").lower(): html.unescape(match.group("value"))
                for match in IMAGE_TAG_ATTRIBUTE_RE.finditer(
                    tag_match.group("attributes")
                )
            }
            source = attributes.get("src", "").strip()
            label = (attributes.get("caption") or attributes.get("alt") or "").strip()
            if source and label:
                labels[source] = label
    return labels


def _retrieval_marker(group: list[Any]) -> list[Any] | None:
    for child in group:
        if (
            isinstance(child, list)
            and child
            and isinstance(child[0], str)
            and child[0].startswith(RETRIEVAL_MARKER_PREFIXES)
        ):
            return child
    return None


def _external_image_descriptor(
    value: Any,
) -> tuple[str, int, int, str] | None:
    if (
        not isinstance(value, list)
        or len(value) < 4
        or not isinstance(value[0], list)
        or not value[0]
        or not isinstance(value[0][0], str)
        or type(value[2]) is not int
        or type(value[3]) is not int
        or value[2] <= 0
        or value[3] <= 0
    ):
        return None
    label = (
        value[4].strip()
        if len(value) > 4 and isinstance(value[4], str)
        else ""
    )
    return value[0][0], value[2], value[3], label


def _marker_label(marker: list[Any], labels: dict[str, str]) -> str:
    marker_url = marker[0]
    marker_name = urllib.parse.urlparse(marker_url).path.lstrip("/")
    short_name = marker_name.rsplit("/", 1)[-1]
    for key in (marker_url, marker_name, short_name):
        if key in labels:
            return labels[key]
    if len(marker) > 2 and isinstance(marker[2], str):
        return marker[2].strip()
    return ""


def _retrieved_asset_from_group(
    group: list[Any],
    *,
    turn_index: int,
    position: int,
    prompt_text: str,
    inline_labels: dict[str, str],
) -> GeminiImageAsset | None:
    marker = _retrieval_marker(group)
    if marker is None:
        return None

    candidates: list[tuple[str, int, int, str]] = []
    descriptor_label = ""
    for child in group:
        descriptor = _external_image_descriptor(child)
        if descriptor is None:
            continue
        url, _width, _height, label = descriptor
        descriptor_label = descriptor_label or label
        if (
            _retrieval_preview_url_is_allowed(url)
            or _wikimedia_raster_url_is_allowed(url)
        ):
            candidates.append(descriptor)
    if not candidates:
        return None

    url, width, height, _ = max(
        candidates,
        key=lambda item: item[1] * item[2],
    )
    parsed = urllib.parse.urlparse(url)
    suffix = Path(urllib.parse.unquote(parsed.path)).suffix.lower()
    declared_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suffix, "")
    label = _marker_label(marker, inline_labels) or descriptor_label or prompt_text
    marker_digest = hashlib.sha256(marker[0].encode("utf-8")).hexdigest()[:16]
    return GeminiImageAsset(
        url=url,
        filename=f"retrieved-{marker_digest}{suffix or '.img'}",
        declared_type=declared_type,
        width=width,
        height=height,
        kind="retrieved",
        turn_index=turn_index,
        position=position,
        caption=_caption_for_asset("retrieved", turn_index, label),
    )


def _caption_for_asset(kind: str, turn_index: int, prompt_text: str) -> str:
    prefix = {
        "uploaded": "Зображення користувача",
        "retrieved": "Знайдене Gemini зображення",
    }.get(kind, "Ілюстрація Gemini")
    prefix = f"{prefix} до репліки {turn_index + 1}"
    if not prompt_text:
        return prefix
    summary = prompt_text[:300].rstrip()
    if len(prompt_text) > len(summary):
        summary = f"{summary}…"
    return f"{prefix}: {summary}"


def extract_gemini_image_assets(payload: Any) -> list[GeminiImageAsset]:
    root = payload[0] if isinstance(payload, list) and payload else None
    turns = root[1] if isinstance(root, list) and len(root) > 1 else None
    if not isinstance(turns, list):
        raise GeminiIllustrationImportError(
            "Gemini conversation turns were not found."
        )

    assets: list[GeminiImageAsset] = []
    seen_urls: set[str] = set()
    for turn_index, turn in enumerate(turns):
        if not isinstance(turn, list) or len(turn) < 4:
            continue
        prompt_text = _normalize_prompt_text(turn[2])

        uploaded: list[GeminiImageAsset] = []
        for record in _iter_lists(turn[2]):
            asset = _asset_from_record(
                record,
                expected_kind=1,
                turn_index=turn_index,
                position=len(uploaded),
                caption=_caption_for_asset("uploaded", turn_index, prompt_text),
            )
            if asset and asset.url not in seen_urls:
                uploaded.append(asset)
                seen_urls.add(asset.url)
        assets.extend(uploaded)

        generated_candidates: list[GeminiImageAsset] = []
        generated_urls: set[str] = set()
        for record in _iter_lists(turn[3]):
            asset = _asset_from_record(
                record,
                expected_kind=2,
                turn_index=turn_index,
                position=0,
                caption=_caption_for_asset("generated", turn_index, prompt_text),
            )
            if asset and asset.url not in generated_urls:
                generated_candidates.append(asset)
                generated_urls.add(asset.url)

        if generated_candidates:
            # Gemini exposes PNG/JPEG and thumbnail variants of the same generated
            # illustration. The largest declared variant is the original.
            generated = max(
                generated_candidates,
                key=lambda item: (
                    item.width * item.height,
                    item.declared_type == "image/png",
                ),
            )
            if generated.url not in seen_urls:
                assets.append(generated)
                seen_urls.add(generated.url)

        retrieved: list[GeminiImageAsset] = []
        inline_labels = _inline_image_labels(turn[3])
        for group in _iter_lists(turn[3]):
            asset = _retrieved_asset_from_group(
                group,
                turn_index=turn_index,
                position=len(retrieved),
                prompt_text=prompt_text,
                inline_labels=inline_labels,
            )
            if asset and asset.url not in seen_urls:
                retrieved.append(asset)
                seen_urls.add(asset.url)
        assets.extend(retrieved)

        if len(assets) >= MAX_IMAGES:
            return assets[:MAX_IMAGES]
    return assets


def _full_resolution_url(value: str) -> str:
    if not _gemini_image_host_is_allowed(value):
        return value
    parsed = urllib.parse.urlsplit(value)
    path = re.sub(r"=mp\d+$", "=s0", parsed.path)
    if path == parsed.path and not re.search(r"=s\d+$", path):
        path = f"{path}=s0"
    return urllib.parse.urlunsplit(parsed._replace(path=path))


def download_gemini_image(
    asset: GeminiImageAsset,
    *,
    client: GeminiHttpClient,
    source_url: str,
) -> DownloadedImage:
    download_url = _full_resolution_url(asset.url)
    if not _download_image_host_is_allowed(download_url):
        raise GeminiIllustrationImportError(
            "Gemini image is hosted on an unsupported host."
        )
    response = client.request(
        download_url,
        accept="image/*",
        referer=source_url,
        max_bytes=MAX_IMAGE_BYTES,
    )
    if not _download_image_host_is_allowed(response.final_url):
        raise GeminiIllustrationImportError(
            "Gemini image redirected to an unsupported host."
        )
    if response.content_type and response.content_type not in {
        *ALLOWED_IMAGE_MIME_TYPES,
        "application/octet-stream",
    }:
        raise GeminiIllustrationImportError(
            f"Unsupported image content type: {response.content_type}"
        )

    try:
        with Image.open(BytesIO(response.body)) as image:
            image_format = image.format
            width, height = image.size
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise GeminiIllustrationImportError(
            "Downloaded Gemini asset is not a valid image."
        ) from exc

    extension = ALLOWED_PIL_FORMATS.get(image_format or "")
    if not extension:
        raise GeminiIllustrationImportError(
            f"Unsupported downloaded image format: {image_format or 'unknown'}"
        )
    if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
        raise GeminiIllustrationImportError(
            "Downloaded Gemini image dimensions are outside the allowed range."
        )
    return DownloadedImage(
        body=response.body,
        extension=extension,
        digest=hashlib.sha256(response.body).hexdigest(),
    )


def _existing_image_digests(dialogue: Dialogue) -> set[str]:
    digests: set[str] = set()
    for illustration in dialogue.illustrations.all():
        if not illustration.image:
            continue
        try:
            digest = hashlib.sha256()
            with illustration.image.open("rb") as image_file:
                for chunk in iter(lambda: image_file.read(64 * 1024), b""):
                    digest.update(chunk)
            digests.add(digest.hexdigest())
        except (OSError, ValueError):
            logger.warning(
                "Could not hash existing illustration %s.",
                illustration.pk,
                exc_info=True,
            )
    return digests


def import_gemini_illustrations(
    dialogue: Dialogue,
    *,
    client: GeminiHttpClient | None = None,
) -> GeminiIllustrationImportResult:
    client = client or GeminiHttpClient()
    share_id, source_url, payload = fetch_gemini_payload(
        dialogue.source_url,
        client=client,
    )
    literature = extract_gemini_recommended_literature(payload)
    literature_imported = False
    if literature and not dialogue.recommended_literature.strip():
        dialogue.recommended_literature = literature
        dialogue.save(update_fields=["recommended_literature", "updated_at"])
        literature_imported = True

    assets = extract_gemini_image_assets(payload)
    existing_digests = _existing_image_digests(dialogue)
    existing_source_keys = set(
        dialogue.illustrations.exclude(source_key="").values_list(
            "source_key",
            flat=True,
        )
    )
    orders = list(dialogue.illustrations.values_list("order", flat=True))
    next_order = max(orders, default=-1) + 1
    imported = 0
    skipped_duplicates = 0
    failed = 0
    total_bytes = 0

    for asset in assets:
        source_key = (
            f"gemini:{share_id}:{asset.turn_index}:"
            f"{asset.kind}:{asset.position}"
        )
        if source_key in existing_source_keys:
            skipped_duplicates += 1
            continue
        try:
            downloaded = download_gemini_image(
                asset,
                client=client,
                source_url=source_url,
            )
            if total_bytes + len(downloaded.body) > MAX_TOTAL_IMAGE_BYTES:
                raise GeminiIllustrationImportError(
                    "Gemini illustrations exceed the total download limit."
                )
            total_bytes += len(downloaded.body)
            if downloaded.digest in existing_digests:
                skipped_duplicates += 1
                continue

            filename = (
                f"gemini-{share_id}-{asset.turn_index + 1}-"
                f"{asset.kind}-{asset.position + 1}.{downloaded.extension}"
            )
            DialogueIllustration.objects.create(
                dialogue=dialogue,
                image=ContentFile(downloaded.body, name=Path(filename).name),
                caption=asset.caption,
                order=next_order,
                source_key=source_key,
            )
            next_order += 1
            imported += 1
            existing_digests.add(downloaded.digest)
            existing_source_keys.add(source_key)
        except GeminiIllustrationImportError:
            failed += 1
            logger.warning(
                "Could not import Gemini illustration for dialogue %s.",
                dialogue.pk,
                exc_info=True,
            )

    return GeminiIllustrationImportResult(
        found=len(assets),
        imported=imported,
        skipped_duplicates=skipped_duplicates,
        failed=failed,
        literature_found=bool(literature),
        literature_imported=literature_imported,
    )
