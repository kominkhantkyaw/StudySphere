"""
Certificate PDF generator with QR code for StudySphere.
Professional layout: light background, dark text and border,
completion statement, Date of Issue and Instructor/Director blocks with auto-filled values.
"""
from io import BytesIO

import qrcode
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from django.conf import settings

# Background: slightly white / off-white (warm); text and border: dark brown for readability
BACKGROUND = HexColor("#FAF8F5")
TEXT_COLOR = HexColor("#3D3429")
TEXT_ACCENT = HexColor("#5C4A3A")
BORDER_COLOR = HexColor("#4A4035")


def _draw_decorative_border(c, x, y, w, h, margin=45):
    """Double-line border in dark brown."""
    c.setStrokeColor(BORDER_COLOR)
    c.setLineWidth(1)
    c.rect(x + margin, y + margin, w - 2 * margin, h - 2 * margin)
    inset = 6
    c.rect(x + margin + inset, y + margin + inset, w - 2 * (margin + inset), h - 2 * (margin + inset))


def _draw_flourish(c, center_x, y, width=120):
    """Decorative flourish under StudySphere: horizontal line with central emblem."""
    c.setStrokeColor(BORDER_COLOR)
    c.setLineWidth(1)
    half = width / 2
    c.line(center_x - half, y, center_x - 20, y)
    c.line(center_x + 20, y, center_x + half, y)
    c.circle(center_x, y, 4)
    c.setFillColor(TEXT_ACCENT)
    c.circle(center_x, y, 2, fill=1, stroke=0)
    c.setFillColor(BACKGROUND)


def generate_certificate_pdf(
    student_name: str,
    course_title: str,
    cert_code: str,
    date_of_issue: str,
    instructor_name: str,
    director_name: str = "Study Sphere",
) -> BytesIO:
    """
    Build a one-page professional PDF certificate: light off-white background,
    dark text and border, completion statement, Date of Issue and signatures
    with auto-filled date and instructor/director names.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 50
    c.setFillColor(BACKGROUND)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(TEXT_COLOR)
    c.setStrokeColor(BORDER_COLOR)

    _draw_decorative_border(c, 0, 0, width, height, margin=45)

    # ---- Top: title lower (more gap from frame) ----
    title_top = height - margin - 85
    c.setFont("Times-Bold", 30)
    c.drawCentredString(width / 2, title_top, "Certificate of Completion")
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, title_top - 32, "StudySphere")
    _draw_flourish(c, width / 2, title_top - 60, 140)
    c.setFillColor(TEXT_COLOR)  # restore text colour after flourish (it sets BACKGROUND)

    # ---- Left side: Student, Course, Certificate ID (labels bold, values regular) ----
    left_x = margin + 28
    info_y = title_top - 118
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_x, info_y, "Student: ")
    c.setFont("Helvetica", 11)
    c.drawString(left_x + c.stringWidth("Student: ", "Helvetica-Bold", 11), info_y, student_name)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_x, info_y - 24, "Course: ")
    c.setFont("Helvetica", 11)
    c.drawString(left_x + c.stringWidth("Course: ", "Helvetica-Bold", 11), info_y - 24, course_title)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left_x, info_y - 48, "Certificate ID: ")
    c.setFont("Helvetica", 11)
    c.drawString(left_x + c.stringWidth("Certificate ID: ", "Helvetica-Bold", 11), info_y - 48, cert_code)

    # ---- Main certification text in the middle (required professional wording) ----
    mid_y = height / 2
    line_ht = 28
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, mid_y + line_ht * 1.5, "This is to certify that")
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(TEXT_ACCENT)
    c.drawCentredString(width / 2, mid_y + line_ht * 0.5, student_name)
    c.setFillColor(TEXT_COLOR)
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, mid_y - line_ht * 0.5, "has successfully completed the course")
    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(TEXT_ACCENT)
    c.drawCentredString(width / 2, mid_y - line_ht * 1.5, course_title)
    c.setFillColor(TEXT_COLOR)

    # ---- Date and signatures below the main text ----
    y = mid_y - line_ht * 1.5 - 48

    # Date of Issue — date value above line, "Date of Issue" below (same design as signatures)
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, y, date_of_issue)
    line_w = 140
    line_y = y - 16
    date_x = width / 2 - line_w / 2
    c.line(date_x, line_y, date_x + line_w, line_y)
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, line_y - 16, "Date of Issue")
    y -= 56

    # Instructor and Director — same design: name above line, role below
    col_width = (width - 2 * margin - 48) / 2
    left_cx = margin + 28 + col_width / 2
    right_cx = width - margin - 28 - col_width / 2
    line_y = y - 12
    label_y = y - 28

    # Instructor: instructor name above line, "Instructor" below
    c.setFont("Times-Italic", 11)
    c.drawCentredString(left_cx, y - 4, instructor_name)
    c.line(left_cx - line_w / 2, line_y, left_cx + line_w / 2, line_y)
    c.setFont("Helvetica", 10)
    c.drawCentredString(left_cx, label_y, "Instructor")

    # Director: director name above line, "Director" below
    c.setFont("Times-Italic", 11)
    c.drawCentredString(right_cx, y - 4, director_name)
    c.line(right_cx - line_w / 2, line_y, right_cx + line_w / 2, line_y)
    c.setFont("Helvetica", 10)
    c.drawCentredString(right_cx, label_y, "Director")

    # QR code — bottom right
    base_url = getattr(settings, "CERT_VERIFY_BASE_URL", "https://studysphere.app/verify/")
    verify_url = f"{base_url.rstrip('/')}/{cert_code}"
    qr_img = qrcode.make(verify_url)
    qr_buf = BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)
    qr_reader = ImageReader(qr_buf)
    qr_size = 88
    qr_x = width - margin - 30 - qr_size
    qr_y = margin + 28
    c.drawImage(qr_reader, qr_x, qr_y, qr_size, qr_size)
    c.setFont("Helvetica", 8)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 4, "Scan to verify")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def generate_and_upload_certificate(student, course, certificate):
    """
    Generate PDF with QR, upload to Supabase (or save locally if Supabase fails).
    Date of Issue and Instructor name are set from certificate.issued_at and course.teacher.
    Returns a public or local URL for the certificate.
    """
    import os
    from courses.utils.supabase_storage import upload_file

    cert_code = f"CERT-{certificate.id:06d}"
    student_name = student.get_full_name() or student.username
    date_of_issue = certificate.issued_at.strftime("%d.%m.%Y")
    instructor_name = course.teacher.get_full_name() or course.teacher.username
    director_name = getattr(
        settings, "CERT_DIRECTOR_NAME", "Study Sphere"
    )
    pdf_buffer = generate_certificate_pdf(
        student_name=student_name,
        course_title=course.title,
        cert_code=cert_code,
        date_of_issue=date_of_issue,
        instructor_name=instructor_name,
        director_name=director_name,
    )
    pdf_buffer.name = f"certificate_{cert_code}.pdf"

    try:
        return upload_file(pdf_buffer, prefix="certificates/issued")
    except Exception:
        # Fallback: save to MEDIA so the certificate still works without Supabase
        media_root = getattr(settings, "MEDIA_ROOT", None)
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        if media_root:
            issued_dir = os.path.join(media_root, "certificates", "issued")
            os.makedirs(issued_dir, exist_ok=True)
            path = os.path.join(issued_dir, pdf_buffer.name)
            with open(path, "wb") as f:
                f.write(pdf_buffer.getvalue())
            return f"{media_url.rstrip('/')}/certificates/issued/{pdf_buffer.name}"
        raise
