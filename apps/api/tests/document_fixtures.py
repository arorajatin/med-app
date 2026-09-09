"""Small, real source files for upload tests; no medical data from real people."""

from io import BytesIO
from textwrap import wrap

from PIL import Image


def pdf_bytes(
    text: bytes = b"Lab report", *, pages: int = 1, media_box: str = "0 0 612 792"
) -> bytes:
    lines = [
        line
        for source_line in text.decode("latin-1").splitlines()
        for line in wrap(source_line, 70)
    ]
    escaped = [
        line.encode("latin-1").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
        for line in lines
    ]
    stream = (
        b"BT /F1 12 Tf 16 TL 40 700 Td "
        + b" T* ".join(b"(" + line + b") Tj" for line in escaped)
        + b" ET"
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids ["
        + b" ".join(f"{5 + index} 0 R".encode() for index in range(pages))
        + f"] /Count {pages} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
    ]
    objects.extend(
        f"<< /Type /Page /Parent 2 0 R /MediaBox [{media_box}] "
        "/Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R >>".encode()
        for _ in range(pages)
    )
    result = b"%PDF-1.4\n"
    offsets = [0]
    for index, item in enumerate(objects, 1):
        offsets.append(len(result))
        result += f"{index} 0 obj\n".encode() + item + b"\nendobj\n"
    xref = len(result)
    result += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    result += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
    result += (
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return result


def image_bytes(
    format: str = "PNG", *, size: tuple[int, int] = (20, 30), mode: str = "RGB"
) -> bytes:
    output = BytesIO()
    Image.new(mode, size, "white").save(output, format=format)
    return output.getvalue()
