from html.parser import HTMLParser
from urllib.parse import urlparse, urlunparse


class _IframeSrcParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.src: str | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if self.src is not None or tag.lower() != "iframe":
            return

        for name, value in attrs:
            if name.lower() == "src" and value:
                self.src = value
                return


def _extract_embed_url(value: str) -> str:
    value = value.strip()
    if "<iframe" not in value.lower():
        return value

    parser = _IframeSrcParser()
    parser.feed(value)
    if not parser.src:
        raise ValueError("Video iframe must include a src attribute")

    return parser.src.strip()


def normalize_kinescope_embed_url(value: str) -> str:
    embed_url = _extract_embed_url(value)
    parsed = urlparse(embed_url)

    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Video URL is invalid") from exc

    embed_id = (
        parsed.path.removeprefix("/embed/")
        if parsed.path.startswith("/embed/")
        else ""
    )
    if (
        parsed.scheme.lower() != "https"
        or (parsed.hostname or "").lower() != "kinescope.io"
        or port is not None
        or not embed_id.strip("/")
    ):
        raise ValueError("Video URL must be a Kinescope embed URL")

    return urlunparse(
        (
            "https",
            "kinescope.io",
            parsed.path,
            "",
            parsed.query,
            "",
        )
    )


