"""Small, real source files for upload tests; no medical data from real people."""

from io import BytesIO

from PIL import Image


def pdf_bytes(text: bytes = b"Lab report", *, pages: int = 1) -> bytes:
    escaped = text.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    stream = b"BT /F1 12 Tf 40 700 Td (" + escaped.replace(b"\n", b" ") + b") Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids ["
        + b" ".join(f"{5 + index} 0 R".encode() for index in range(pages))
        + f"] /Count {pages} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
    ]
    objects.extend(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 3 0 R >> >> /Contents 4 0 R >>"
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
