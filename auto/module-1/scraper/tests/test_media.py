import io

from PIL import Image

from scraper.media import BLOCKED_IMAGE_METADATA_TERMS, prepare_gallery_evidence, prepare_image


class _Response:
    status_code = 200

    def __init__(self, content: bytes):
        self.content = content


class _Session:
    def __init__(self, content: bytes):
        self.content = content

    def get(self, _url: str, timeout: int):
        assert timeout == 60
        return _Response(self.content)


def test_prepare_image_removes_marketplace_and_supplier_text_metadata(tmp_path):
    source = Image.new("RGB", (24, 24), "white")
    exif = Image.Exif()
    exif[270] = "Amazon Wazaro Preaureum source listing"
    raw = io.BytesIO()
    source.save(raw, format="JPEG", exif=exif)

    content, mime = prepare_image(
        "https://example.test/source.jpg",
        tmp_path / "unused-logo.png",
        add_logo=False,
        session=_Session(raw.getvalue()),
    )

    assert mime == "image/jpeg"
    with Image.open(io.BytesIO(content)) as sanitized:
        assert not sanitized.getexif()
        metadata_text = " ".join(
            str(value) for value in sanitized.info.values() if isinstance(value, (str, bytes))
        ).casefold()
    assert all(term not in metadata_text for term in BLOCKED_IMAGE_METADATA_TERMS)


def test_prepare_gallery_evidence_creates_sanitized_images_and_contact_sheet(tmp_path):
    source = Image.new("RGB", (640, 480), "navy")
    exif = Image.Exif()
    exif[270] = "Amazon source metadata"
    raw = io.BytesIO()
    source.save(raw, format="JPEG", exif=exif)
    manifest = prepare_gallery_evidence(
        ["https://example.test/one.jpg", "https://example.test/two.jpg"],
        tmp_path / "evidence",
        session=_Session(raw.getvalue()),
    )
    gallery = tmp_path / "evidence" / "gallery"
    assert [item["evidence_id"] for item in manifest["images"]] == ["gallery/001.jpg", "gallery/002.jpg"]
    assert (gallery / "contact-sheet.jpg").is_file()
    assert (gallery / "manifest.json").is_file()
    for path in (gallery / "001.jpg", gallery / "002.jpg", gallery / "contact-sheet.jpg"):
        with Image.open(path) as image:
            assert not image.getexif()
