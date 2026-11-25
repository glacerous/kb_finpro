"""Generate clean, high-clarity 11-slide presentation deck (.pptx) matching MINGGU-14-LK.md.

Design: pure white canvas, charcoal typography (Segoe UI), UPNVY navy & gold accents,
plain-Indonesian takeaway headlines, explicit 8-kabupaten scope, both Web Interactive
Dashboard and Power BI Desktop showcased, and full speaker notes per slide.

Outputs: docs/Presentasi_Tugas_Besar_KB.pptx
"""

from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

OUT_PATH = Path("docs/Presentasi_Tugas_Besar_KB.pptx")
TOTAL_SLIDES = 11

# Clean Minimal Palette (pure white canvas + UPNVY navy + gold accent)
BG_CREAM = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x11, 0x18, 0x27)
MUTED = RGBColor(0x4B, 0x55, 0x63)
RULE = RGBColor(0xE5, 0xE7, 0xEB)
NAVY = RGBColor(0x1B, 0x36, 0x5D)
NAVY_LT = RGBColor(0xEF, 0xF6, 0xFF)
GOLD = RGBColor(0xF5, 0xB8, 0x00)
TEAL = RGBColor(0x0F, 0x76, 0x6E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
FONT = "Segoe UI"


def set_bg(slide, color=BG_CREAM) -> None:
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = color
    bg.line.fill.background()


def add_line(slide, left, top, width, color=RULE, thickness=0.75) -> None:
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Pt(thickness))
    line.fill.solid()
    line.fill.fore_color.rgb = color
    line.line.fill.background()


def add_box(slide, left, top, width, height, fill_color=NAVY_LT, border_color=RULE):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    box.adjustments[0] = 0.06
    box.fill.solid()
    box.fill.fore_color.rgb = fill_color
    if border_color is not None:
        box.line.color.rgb = border_color
        box.line.width = Pt(0.75)
    else:
        box.line.fill.background()
    return box


def add_text(slide, left, top, width, height, text: str, size=14, bold=False, color=INK, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = 1.18
    r = p.add_run()
    r.text = text
    r.font.name = FONT
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    return tb


def new_slide(prs: Presentation, num: int, kicker: str, headline: str, notes: str = ""):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(slide, WHITE)

    add_text(slide, 0.7, 0.38, 8.5, 0.3, kicker.upper(), size=10, bold=True, color=NAVY)
    add_text(slide, 11.4, 0.38, 1.2, 0.3, f"{num} / {TOTAL_SLIDES}", size=10, bold=False, color=MUTED, align=PP_ALIGN.RIGHT)
    add_text(slide, 0.7, 0.72, 11.9, 0.78, headline, size=22.5, bold=True, color=INK)
    add_line(slide, 0.7, 1.52, 11.9, color=RULE, thickness=0.75)

    if notes:
        slide.notes_slide.notes_text_frame.text = notes.strip()
    return slide


def add_stat_block(slide, left, top, width, number: str, label: str, detail: str, accent=NAVY):
    add_text(slide, left, top, width, 0.58, number, size=31, bold=True, color=accent)
    add_text(slide, left, top + 0.60, width, 0.30, label, size=12.5, bold=True, color=INK)
    add_text(slide, left, top + 0.90, width, 0.68, detail, size=11, color=MUTED)


def add_clean_list(slide, items: list[tuple[str, str]], left, top, width, height, size=13, gap=9):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, (head, body) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.line_spacing = 1.20
        if head:
            r0 = p.add_run()
            r0.text = head + "  "
            r0.font.name = FONT
            r0.font.size = Pt(size)
            r0.font.bold = True
            r0.font.color.rgb = INK
        r1 = p.add_run()
        r1.text = body
        r1.font.name = FONT
        r1.font.size = Pt(size)
        r1.font.color.rgb = MUTED if head else INK


def add_framed_image(slide, img_path: str, left, top, width):
    pic = slide.shapes.add_picture(img_path, Inches(left), Inches(top), width=Inches(width))
    pic.line.color.rgb = RULE
    pic.line.width = Pt(1.0)
    return pic


def add_minimal_table(slide, headers, rows, left, top, width, height, highlight_row: int | None = None, size=11.5):
    tbl_shape = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(left), Inches(top), Inches(width), Inches(height))
    tbl = tbl_shape.table
    for j, h in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = INK
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
        r = p.add_run()
        r.text = h
        r.font.name = FONT
        r.font.size = Pt(size)
        r.font.bold = True
        r.font.color.rgb = WHITE

    for i, rvals in enumerate(rows):
        is_hi = highlight_row is not None and i == highlight_row
        for j, val in enumerate(rvals):
            cell = tbl.cell(i + 1, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY_LT if is_hi else (WHITE if i % 2 == 0 else RGBColor(0xF9, 0xFA, 0xFB))
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
            r = p.add_run()
            r.text = val
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.bold = is_hi
            r.font.color.rgb = NAVY if is_hi else INK


def build_deck() -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # ---------- SLIDE 1: UPNVY ARCHITECTURAL COVER ----------
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s1, WHITE)
    s1.shapes.add_picture("docs/screenshots/upnvy_building_sketch.jpg", Inches(0), Inches(0), width=Inches(13.333), height=Inches(7.5))

    bar_top = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(13.11), Inches(0), Inches(0.223), Inches(4.15))
    bar_top.fill.solid()
    bar_top.fill.fore_color.rgb = GOLD
    bar_top.line.fill.background()
    bar_bot = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(13.11), Inches(4.15), Inches(0.223), Inches(3.35))
    bar_bot.fill.solid()
    bar_bot.fill.fore_color.rgb = NAVY
    bar_bot.line.fill.background()

    add_text(
        s1, 0.55, 0.45, 5.2, 0.75,
        'UNIVERSITAS PEMBANGUNAN NASIONAL\n"VETERAN" YOGYAKARTA',
        size=13.5, bold=True, color=NAVY,
    )
    add_text(
        s1, 6.85, 1.72, 5.85, 2.0,
        "Prediksi Kebutuhan Irigasi Harian\n& Kelayakan ROI Pompa Air\nTenaga Surya (8 Kabupaten)",
        size=28, bold=True, color=NAVY,
    )
    add_line(s1, 6.85, 3.88, 0.85, color=GOLD, thickness=3.0)
    add_text(
        s1, 6.85, 4.14, 5.85, 0.78,
        "Tugas Besar Kecerdasan Bisnis (Kelas SI-C)\nStudi Petani Padi: 4 Kab. DIY & 4 Kab. Jawa Tengah Selatan (2011-2025)",
        size=12.5, color=MUTED,
    )
    add_text(
        s1, 6.85, 5.02, 5.85, 1.25,
        "Muhammad Barkah Ramadhan (124240004)\n"
        "Azzaky Raihan Ramdhani (124240018)  |  Syahrul Alfiansyah (124240005)\n"
        "Muhammad Ariel Saputra (124240010)  |  Ahmad Ridwan Alhadi (124240027)",
        size=10.5, color=INK,
    )
    add_text(s1, 0.55, 6.85, 3.0, 0.35, "u p n y k . a c . i d", size=11, bold=True, color=NAVY)
    tb_m = add_text(
        s1, 8.6, 6.62, 4.15, 0.65,
        "Widya Mwat Yasa\nProgram Studi Sistem Informasi, 2026",
        size=11.5, bold=True, color=NAVY, align=PP_ALIGN.RIGHT,
    )
    for p in tb_m.text_frame.paragraphs:
        for r in p.runs:
            r.font.italic = True
    s1.notes_slide.notes_text_frame.text = (
        "Selamat pagi/siang Bapak/Ibu dosen dan teman-teman. Kami dari kelas SI-C akan mempresentasikan "
        "proyek Kecerdasan Bisnis tentang kelayakan ganti pompa diesel ke pompa air tenaga surya untuk "
        "petani padi di 8 kabupaten (4 DIY dan 4 Jateng Selatan), lengkap dengan prediksi irigasi besok, "
        "peta web interaktif, dan dashboard Power BI."
    )

    # ---------- SLIDE 2: KONTEKS, 8 KABUPATEN & MASALAH BISNIS ----------
    s2 = new_slide(
        prs, 2, "Konteks, Wilayah Studi & Masalah Bisnis",
        "Padi DIY turun 15%; petani diesel hadapi risiko biaya solar melonjak 3,5x",
        notes=(
            "Latar belakang kami berangkat dari 2 masalah nyata. Pertama, data BPS menunjukkan produksi padi "
            "DIY 2024 turun 14,95% akibat kekeringan El Nino. Kedua, petani bergantung pada pompa diesel, "
            "padahal jaminan harga Biosolar subsidi Rp 6.800/L baru dipastikan pemerintah hingga 31 Desember "
            "2026 (ANTARA News & Jawa Pos), sementara harga nonsubsidi Dexlite sudah Rp 23.700/L (3,5 kali lipat). "
            "Studi ini mencakup 8 kabupaten: 4 kabupaten DIY (Gunungkidul, Bantul, Sleman, Kulon Progo) dan "
            "4 kabupaten Jateng Selatan (Klaten, Wonogiri, Purworejo, Kab. Magelang)."
        ),
    )

    facts = [
        ("-14,95%", "Produksi Padi DIY 2024 Turun", "Dampak kemarau El Nino; terparah di Gunungkidul, Bantul, Sleman (BPS)."),
        ("Rp 6.800/L", "Biosolar Subsidi (s.d. 31 Des 2026)", "Jaminan harga murah pemerintah (ESDM & Pertamina) baru pasti hingga akhir 2026."),
        ("Rp 23.700/L", "Dexlite Non-Subsidi (3,5x Lipat)", "Biaya riil jika petani tanpa subsidi / kuota habis (CNBC Indonesia, Nov 2026)."),
    ]
    for idx, (num, lbl, det) in enumerate(facts):
        y = 1.92 + idx * 1.72
        add_text(s2, 0.7, y, 2.45, 0.65, num, size=27, bold=True, color=NAVY)
        add_text(s2, 3.22, y + 0.04, 3.05, 0.34, lbl, size=12.5, bold=True, color=INK)
        add_text(s2, 3.22, y + 0.38, 3.05, 0.72, det, size=11, color=MUTED)
        if idx < 2:
            add_line(s2, 0.7, y + 1.36, 5.55, color=RULE, thickness=0.75)

    # Right column: Explicit 8 kabupaten + news proof + 3 business questions
    add_text(s2, 6.7, 1.76, 5.9, 0.28, "CAKUPAN WILAYAH STUDI (8 KABUPATEN)", size=10, bold=True, color=NAVY)
    add_box(s2, 6.7, 2.06, 5.9, 0.92, fill_color=NAVY_LT, border_color=RULE)
    add_clean_list(
        s2,
        [
            ("DIY (4 Kab.):", "Gunungkidul, Bantul, Sleman, Kulon Progo"),
            ("Jateng Selatan (4 Kab.):", "Klaten, Wonogiri, Purworejo, Kab. Magelang"),
        ],
        left=6.88, top=2.18, width=5.55, height=0.75, size=11.5, gap=4,
    )

    add_text(s2, 6.7, 3.12, 5.9, 0.26, "BUKTI KEBIJAKAN BBM", size=10, bold=True, color=NAVY)
    crop_img = Path("docs/screenshots/news_jawapos_headline_crop.png")
    if crop_img.exists():
        add_framed_image(s2, str(crop_img), 6.7, 3.40, 5.35)
    add_text(s2, 6.7, 4.68, 5.9, 0.26, "Sumber: Jawa Pos (9 Nov 2026)  |  ANTARA News  |  CNBC Indonesia", size=9.5, color=MUTED)

    add_line(s2, 6.7, 5.02, 5.9, color=RULE, thickness=0.75)
    add_text(s2, 6.7, 5.14, 5.9, 0.26, "3 PERTANYAAN BISNIS", size=10, bold=True, color=NAVY)
    add_clean_list(
        s2,
        [
            ("01  Balik Modal:", "Paket & wilayah mana paling cepat balik modal (Individu 1 ha vs Kelompok 5 ha)?"),
            ("02  Beda Wilayah:", "Apakah perbedaan kebutuhan air antar 8 kabupaten & antar musim signifikan?"),
            ("03  Prediksi Besok:", "Bisakah memprediksi jadwal siram H+1 agar petani tidak sampai gagal siram?"),
        ],
        left=6.7, top=5.44, width=5.9, height=1.7, size=11.5, gap=6,
    )

    # ---------- SLIDE 3: ALUR PIPELINE & CARA HITUNG BALIK MODAL ----------
    s3 = new_slide(
        prs, 3, "Pendekatan & Cara Kerja Sistem",
        "Dari 15 tahun data cuaca ke keputusan beli pompa: 5 tahap pipeline BI",
        notes=(
            "Alur kerja kami terdiri dari 5 tahap terhubung: mulai dari ambil 1,05 juta baris cuaca per jam "
            "2011-2025, simpan di PostgreSQL dan hitung kebutuhan air padi (NFR) serta volume air pompa surya, "
            "uji statistik ANOVA dan t-test, latih model prediksi siram besok (ML H+1), lalu hitung balik modal "
            "dan sajikan ke Power BI dan Web Dashboard Interaktif. Perlu ditegaskan: balik modal dihitung dari "
            "uang beli solar yang tidak jadi keluar setiap tahun dibandingkan modal beli paket pompa surya di awal."
        ),
    )
    steps = [
        ("01", "ETL & Ingestion", "Python + Open-Meteo/NASA", "Extract 1,05 jt baris cuaca per jam (2011-2025) di 8 kab., cleaning (0 null), & load idempotent."),
        ("02", "Data Warehouse", "PostgreSQL Star Schema", "Skema Bintang Kimball (3 Dimensi + 5 Fakta); hitung kebutuhan air padi (NFR) & debit pompa surya."),
        ("03", "Uji Statistik", "ANOVA & Welch t-test", "Analisis deskriptif & uji hipotesis beda kebutuhan air antar 8 kabupaten serta musim kemarau vs hujan."),
        ("04", "Predictive ML (H+1)", "Scikit-Learn + Tuning 3:1", "Prediksi perlu siram besok (temporal split 2011-22 vs 2023-25) & tekan risiko gagal siram (FN)."),
        ("05", "Prescriptive & BI", "ROI 192 Skenario + Power BI", "Simulasi balik modal (CAPEX riil) -> Dashboard Power BI (6 DAX) & Web Map Interaktif 8 kab."),
    ]
    for i, (num, title, tool, desc) in enumerate(steps):
        x = 0.7 + i * 2.42
        add_text(s3, x, 1.98, 2.15, 0.42, num, size=24, bold=True, color=NAVY)
        add_text(s3, x, 2.50, 2.15, 0.34, title, size=13.5, bold=True, color=INK)
        add_text(s3, x, 2.84, 2.15, 0.28, tool, size=10.5, bold=True, color=TEAL)
        add_line(s3, x, 3.22, 2.1, color=RULE, thickness=0.75)
        add_text(s3, x, 3.38, 2.15, 1.75, desc, size=11.5, color=MUTED)

    # Clear plain-Indonesian formula box at bottom
    add_box(s3, 0.7, 5.42, 11.9, 1.52, fill_color=NAVY_LT, border_color=RULE)
    add_text(s3, 0.95, 5.58, 11.4, 0.32, "CARA HITUNG BALIK MODAL (BEP) — BUKAN DARI JUAL PADI, TAPI DARI PENGHEMATAN SOLAR:", size=11, bold=True, color=NAVY)
    add_text(
        s3, 0.95, 5.95, 11.4, 0.85,
        "Balik Modal (Tahun)  =  Modal Beli Paket Pompa Surya (CAPEX)  /  (Uang Solar yang Dihemat per Tahun  -  Perawatan 2%/thn)\n"
        "Contoh Gunungkidul 5 kWp (5 ha, CAPEX Rp 35 jt):  Hemat ~1.265 L solar/thn -> Biosolar hemat bersih Rp 7,9 jt/thn (BEP 4,43 thn)  |  Dexlite Rp 29,3 jt/thn (BEP 1,20 thn).",
        size=11.5, bold=False, color=INK,
    )

    # ---------- SLIDE 4: FONDASI DATA & VALIDASI ----------
    s4 = new_slide(
        prs, 4, "Fondasi Data & Validasi",
        "8 tabel di PostgreSQL (6 tabel inti di Power BI); Open-Meteo tangkap cuaca lokal",
        notes=(
            "Di PostgreSQL kami menyimpan lengkap 8 tabel skema bintang Kimball (3 dimensi + 5 fakta), "
            "termasuk 1,05 juta baris cuaca per jam. Di Power BI sengaja hanya 6 tabel teragregasi yang "
            "di-import agar dashboard tetap ringan dan cepat. Validasi silang dengan satelit NASA POWER "
            "menunjukkan korelasi kuat (r = 0,74-0,78), tetapi grid NASA terlalu kasar (111 km) sehingga "
            "8 kabupaten terbaca seragam, sedangkan Open-Meteo menangkap variasi lokal nyata."
        ),
    )
    add_framed_image(s4, "docs/screenshots/pbi_model_view_star_schema.png", 0.7, 1.82, 7.45)
    add_text(s4, 0.7, 6.42, 7.45, 0.4, "Model View Power BI: 6 tabel inti (3 Dimensi + 3 Fakta); 2 tabel mentah (hourly & NASA) tetap di PostgreSQL.", size=10, color=MUTED)

    add_stat_block(s4, 8.5, 1.82, 4.1, "1,05 Juta", "Baris Cuaca Per Jam (0 Null)", "8 tabel di PostgreSQL; 6 tabel teragregasi di-import ke Power BI agar ringan.", accent=NAVY)
    add_stat_block(s4, 8.5, 3.60, 4.1, "r = 0,74-0,78", "Validasi Silang NASA POWER", "Grid NASA kasar (111 km, seragam 18,32); Open-Meteo tangkap beda lokal 17,46-18,55 MJ/m2.", accent=TEAL)
    add_stat_block(s4, 8.5, 5.38, 4.1, "Harga Riil", "CAPEX Marketplace (+15% Pasang)", "1 kWp: Rp 8,5-15,5 jt | 3 kWp: Rp 20-38 jt | 5 kWp: Rp 35-65 jt (Tokopedia).", accent=NAVY)

    # ---------- SLIDE 5: STATISTIK & SINERGI AGROKLIMAT ----------
    s5 = new_slide(
        prs, 5, "Temuan Wilayah & Sinergi Matahari",
        "Gunungkidul & Klaten paling butuh air — dan matahari justru paling terik saat kemarau",
        notes=(
            "Uji statistik ANOVA membuktikan kebutuhan air antar 8 kabupaten berbeda secara nyata (F = 42,28, "
            "p < 0,001): Gunungkidul (3,30 mm/hari) dan Klaten (3,25 mm/hari) 34% lebih haus air dibanding "
            "Kab. Magelang (2,46 mm/hari). Grafik kiri membuktikan sinergi alami: saat musim kemarau, kebutuhan "
            "air sawah naik 2 kali lipat bersamaan dengan radiasi matahari mencapai puncaknya — artinya pompa "
            "surya bekerja paling kuat justru saat petani paling butuh air."
        ),
    )
    add_framed_image(s5, "docs/screenshots/pbi_page2_climate_demand.png", 0.7, 1.85, 7.65)
    add_stat_block(s5, 8.7, 1.85, 3.9, "F = 42,28", "ANOVA 8 Kabupaten (p < 0,001)", "Gunungkidul (3,30) & Klaten (3,25) butuh air 34% lebih tinggi dari Magelang (2,46 mm/hr).", accent=NAVY)
    add_stat_block(s5, 8.7, 3.72, 3.9, "2x Lipat", "Sinergi Alami Musim Kemarau", "Kebutuhan air naik 2,30 -> 4,47 mm/hr bersamaan sinar matahari naik 17,36 -> 18,93 MJ/m2.", accent=TEAL)
    add_box(s5, 8.7, 5.52, 3.9, 1.15, fill_color=NAVY_LT, border_color=RULE)
    add_text(
        s5, 8.88, 5.66, 3.55, 0.9,
        "Artinya bagi Petani: Pompa surya justru menghasilkan air paling banyak di bulan paling kering (termasuk El Nino 2018, 2019, 2023).",
        size=11, bold=True, color=INK,
    )

    # ---------- SLIDE 6: MODEL PREDIKTIF ML H+1 ----------
    s6 = new_slide(
        prs, 6, "Prediksi Jadwal Siram Besok (ML H+1)",
        "Prediksi irigasi besok memangkas risiko gagal siram hingga 90% (Recall 97,3%)",
        notes=(
            "Kami melatih model Machine Learning untuk menjawab pertanyaan: apakah besok sawah butuh disiram? "
            "Diujikan secara jujur pada 5.808 hari data masa depan 2023-2025, Logistic Regression jadi yang "
            "terbaik (ROC-AUC 0,794). Karena lupa menyiram sawah (gagal panen) jauh lebih merugikan petani "
            "dibanding bersiaga lebih awal, ambang prediksi diturunkan ke 0,21 (rasio biaya 3:1). Hasilnya "
            "hari gagal siram turun 90% dari 849 menjadi hanya 88 hari (Recall 97,3%)."
        ),
    )
    add_stat_block(s6, 0.7, 1.80, 3.5, "0,794", "Skor ROC-AUC Terbaik", "Logistic Regression unggul atas Baseline & Random Forest (0,790) di data uji 2023-2025.", accent=NAVY)
    add_stat_block(s6, 4.75, 1.80, 3.5, "97,3%", "Daya Tangkap Hari Kering", "Dari 100 hari sawah butuh air besok, 97 hari berhasil diperingatkan sejak hari sebelumnya.", accent=TEAL)
    add_stat_block(s6, 8.8, 1.80, 3.8, "-90%", "Penurunan Gagal Siram", "Hari terlewat (False Negative) anjlok dari 849 (persistence) menjadi hanya 88 hari.", accent=NAVY)

    add_minimal_table(
        s6,
        ["Model (Uji 2023-2025, 5.808 hari)", "Akurasi", "Recall", "F1", "AUC", "Gagal Siram (FN)", "Siaga Lebih (FP)"],
        [
            ["Climatology (baseline historis)", "0,598", "0,546", "0,606", "0,651", "1.497", "839"],
            ["Persistence (tebak = hari ini)", "0,711", "0,742", "0,745", "-", "849", "828"],
            ["Logistic Regression (default t=0,50)", "0,731", "0,736", "0,757", "0,794", "871", "689"],
            ["Logistic Regression (3:1, t=0,21)  [Dipilih]", "0,601", "0,973", "0,735", "0,794", "88", "2.227"],
            ["Random Forest (default t=0,50)", "0,727", "0,733", "0,753", "0,790", "880", "704"],
        ],
        left=0.7, top=3.65, width=11.9, height=2.65, highlight_row=3, size=11.5,
    )
    add_text(
        s6, 0.7, 6.50, 11.9, 0.5,
        "Kenapa model t=0,21 dipilih?  Karena gagal menyiram sawah (risiko gagal panen) jauh lebih merugikan petani dibanding bersiaga pompa lebih awal.",
        size=11.5, bold=True, color=NAVY,
    )

    # ---------- SLIDE 7: WEB DASHBOARD INTERAKTIF (PETA 8 KABUPATEN) ----------
    s7 = new_slide(
        prs, 7, "Peta Kelayakan Interaktif (8 Kabupaten)",
        "Web Dashboard Interaktif: ranking BEP 8 kabupaten & simulasi harga BBM real-time",
        notes=(
            "Selain Power BI, kami membangun Web Dashboard Interaktif offline (docs/dashboard_interaktif.html) "
            "berbasis peta geospasial 8 kabupaten agar pengambil keputusan langsung melihat sebaran geografisnya. "
            "Di mode Kelompok Tani 5 kWp dengan Biosolar Rp 6.800/L, 4 kabupaten berwarna hijau sudah balik modal "
            "di bawah 5 tahun: Gunungkidul (4,43 thn), Klaten (4,54 thn), Bantul (4,80 thn), dan Wonogiri (4,93 thn). "
            "Saat slider harga BBM di bawah digeser ke Dexlite Rp 23.700/L, seluruh 8 kabupaten langsung hijau (< 3 thn)."
        ),
    )
    web_img = Path("docs/screenshots/web_dashboard_map_roi.png")
    if web_img.exists():
        add_framed_image(s7, str(web_img), 0.7, 1.82, 8.25)
    add_text(s7, 0.7, 6.52, 8.25, 0.35, "Tampilan live docs/dashboard_interaktif.html (100% offline, 4 tab: Peta ROI, Iklim & Sinergi, Prediksi ML, Sumber).", size=10, color=MUTED)

    add_stat_block(s7, 9.25, 1.82, 3.4, "4 / 8 Kab.", "Layak di Biosolar (< 5 Thn)", "Gunungkidul (4,43), Klaten (4,54), Bantul (4,80), Wonogiri (4,93 thn).", accent=TEAL)
    add_stat_block(s7, 9.25, 3.65, 3.4, "8 / 8 Kab.", "Layak di Dexlite (< 3 Thn)", "Geser slider BBM ke Rp 23.700/L -> semua wilayah BEP 1,20-2,77 tahun.", accent=NAVY)
    add_box(s7, 9.25, 5.45, 3.4, 1.05, fill_color=NAVY_LT, border_color=RULE)
    add_text(
        s7, 9.42, 5.58, 3.08, 0.82,
        "Bisa di-demo langsung:\nToggle Individu vs Kelompok, 1/3/5 kWp, & geser slider harga BBM.",
        size=11, bold=True, color=INK,
    )

    # ---------- SLIDE 8: POWER BI ANALITIK & ALUR LIVE DEMO ----------
    s8 = new_slide(
        prs, 8, "Dashboard Analitik Power BI & Live Demo",
        "Power BI 3 halaman (kbfinpro.pbix) melengkapi analisis DAX & Drill-Through per wilayah",
        notes=(
            "Untuk analisis mendalam terhubung ke PostgreSQL, kami menyediakan dashboard Power BI Desktop 3 halaman "
            "dengan 6 DAX measures dan fitur Drill-Through. Alur live demo 2 menit: (1) geser slider harga BBM di "
            "Web Dashboard Interaktif, (2) di Power BI Page 1 klik kanan Gunungkidul lalu Drill-Through ke profil "
            "iklim 15 tahun di Page 2, (3) tunjukkan Confusion Matrix dan kalibrasi ML di Page 3."
        ),
    )
    add_framed_image(s8, "docs/screenshots/pbi_page1_executive_roi.png", 0.7, 1.85, 5.8)
    add_framed_image(s8, "docs/screenshots/pbi_page3_ml_prediction.png", 6.8, 1.85, 5.8)
    add_text(s8, 0.7, 5.24, 5.8, 0.3, "Power BI Page 1: Executive ROI (4 slicer + perbandingan CAPEX Low/High)", size=11, bold=True, color=MUTED)
    add_text(s8, 6.8, 5.24, 5.8, 0.3, "Power BI Page 3: ML H+1 (Recall 97,3%, Confusion Matrix, kalibrasi)", size=11, bold=True, color=MUTED)
    add_line(s8, 0.7, 5.68, 11.9, color=RULE, thickness=1.0)
    add_box(s8, 0.7, 5.84, 11.9, 1.05, fill_color=NAVY_LT, border_color=RULE)
    add_text(
        s8, 0.92, 5.98, 11.45, 0.8,
        "Alur Live Demo (2-3 Menit):   (1) Web Dashboard: geser slider Biosolar -> Dexlite & bandingkan 8 kab.   |   "
        "(2) Power BI Page 1 -> 2: klik kanan Gunungkidul -> Drill-Through iklim 15 thn   |   (3) Power BI Page 3: cek matriks ML.",
        size=12, bold=True, color=NAVY,
    )

    # ---------- SLIDE 9: REKOMENDASI KEPUTUSAN & PERBANDINGAN ROI ----------
    s9 = new_slide(
        prs, 9, "Rekomendasi Keputusan & Kelayakan ROI",
        "Kelompok Tani 5 kWp (5 ha) paling optimal; hindari beli 5 kWp untuk lahan 1 ha",
        notes=(
            "Tabel ini merangkum keputusan paling praktis bagi petani dan pemerintah. Pertama, untuk petani "
            "individu 1 ha, pilih paket kecil 1 kWp (Rp 8,5-15,5 jt); jangan beli 5 kWp karena kapasitas terbuang "
            "dan balik modal membengkak lebih dari 12 tahun (over-sizing). Kedua, untuk program pemerintah/Gapoktan, "
            "skala komunal 5 kWp (5 ha) di Gunungkidul, Klaten, Bantul, dan Wonogiri sudah layak di bawah 5 tahun "
            "bahkan pada Biosolar subsidi, dan seluruh 8 kabupaten balik modal hanya 1,2-2,8 tahun pada Dexlite."
        ),
    )
    add_minimal_table(
        s9,
        ["Skala & Wilayah (0,04 L/m3)", "Modal Awal", "Hemat/Thn (Biosolar)", "BEP Biosolar", "BEP Dexlite", "Keputusan"],
        [
            ["Individu 1 ha  |  1 kWp (Gunungkidul)", "Rp 8,5-15,5 jt", "Rp 1,6 jt/thn", "5,48 - 10,99 thn", "1,46 - 2,73 thn", "Pas untuk 1 ha"],
            ["Individu 1 ha  |  5 kWp (Gunungkidul)", "Rp 35-65 jt", "Rp 2,8 jt/thn", "12,3+ thn", "3,06 - 5,99 thn", "Hindari (Over-size)"],
            ["Kelompok 5 ha  |  5 kWp (Gunungkidul)", "Rp 35-65 jt", "Rp 7,9 jt/thn", "4,43 - 8,90 thn", "1,20 - 2,27 thn", "Prioritas #1"],
            ["Kelompok 5 ha  |  5 kWp (Klaten, Bantul, Wonogiri)", "Rp 35-65 jt", "Rp 7,1-7,7 jt/thn", "4,54 - 9,99 thn", "1,22 - 2,49 thn", "Prioritas #2-4"],
            ["Kelompok 5 ha  |  5 kWp (Kulon Progo, Purworejo, Sleman, Magelang)", "Rp 35-65 jt", "Rp 6,4-6,8 jt/thn", "5,12 - 11,20 thn", "1,37 - 2,77 thn", "Layak di Dexlite"],
        ],
        left=0.7, top=1.80, width=11.9, height=2.95, highlight_row=2, size=11,
    )
    add_clean_list(
        s9,
        [
            ("1. Dinas Pertanian & ESDM:", "Prioritaskan hibah pompa komunal 5 kWp (5 ha) di Gunungkidul, Klaten, Bantul, dan Wonogiri — sudah layak di Biosolar & siap hadapi risiko penyesuaian subsidi 2027."),
            ("2. Petani Individu & Gapoktan:", "Lahan 1 ha cukup pakai 1 kWp (hindari over-sizing); sisihkan 15% uang hemat solar untuk dana cadangan ganti motor pompa."),
            ("3. Operasional Harian:", "Gunakan peringatan ML H+1 (Recall 97,3%) sebagai pengingat jadwal pompa & padukan dengan kalender tanam KATAM."),
        ],
        left=0.7, top=4.98, width=11.9, height=2.1, size=12.5, gap=8,
    )

    # ---------- SLIDE 10: ETIKA, TATA KELOLA & BATASAN ----------
    s10 = new_slide(
        prs, 10, "Etika, Tata Kelola & Batasan",
        "Bebas data pribadi (UU PDP No. 27/2022) dengan 4 batasan metodologi yang transparan",
        notes=(
            "Seluruh data yang kami olah adalah data cuaca publik tanpa data pribadi petani (bebas PII) sesuai "
            "prinsip minimalisasi data UU PDP No. 27/2022. Kami juga mencatat jujur 4 batasan metodologi, "
            "termasuk bahwa biaya ganti motor pompa DC di tahun ke-5 sampai ke-7 belum dipotong dalam hitungan BEP."
        ),
    )
    add_text(s10, 0.7, 1.98, 5.6, 0.35, "TATA KELOLA & MODEL CARD", size=12, bold=True, color=NAVY)
    add_line(s10, 0.7, 2.38, 5.5, color=RULE, thickness=0.75)
    add_clean_list(
        s10,
        [
            ("UU PDP No. 27/2022:", "Data iklim publik tanpa PII; wajib anonimisasi jika kelak dihubungkan ke data anggota Gapoktan."),
            ("Tujuan Pakai (Intended Use):", "Alat bantu peringatan jadwal siram H+1 dengan pengawasan petani (human-in-the-loop)."),
            ("Di Luar Cakupan:", "Bukan saklar pompa otomatis tanpa manusia dan bukan untuk tanaman non-padi."),
            ("Keadilan (Fairness):", "Model murni berbasis data iklim wilayah, tanpa bias status kepemilikan lahan."),
        ],
        left=0.7, top=2.60, width=5.6, height=4.1, size=12.5, gap=12,
    )

    add_text(s10, 6.9, 1.98, 5.6, 0.35, "4 BATASAN YANG DIAKUI TERBUKA", size=12, bold=True, color=NAVY)
    add_line(s10, 6.9, 2.38, 5.6, color=RULE, thickness=0.75)
    add_clean_list(
        s10,
        [
            ("1. Data Reanalisis:", "Open-Meteo & NASA adalah data grid satelit/model, bukan sensor fisik BMKG di tiap petak sawah."),
            ("2. Label Sintetis:", "Status perlu irigasi dihitung dari rumus NFR FAO/KP-01 & asumsi jadwal tanam MT1-MT2."),
            ("3. Ekstrapolasi Pompa:", "Kurva debit dari 1 studi lapangan Gowa (cut-in 30 W/m2) diskalakan ke 3 & 5 kWp."),
            ("4. Umur Motor Pompa:", "Biaya ganti motor pompa DC (tahun ke-5-7) belum dipotong di rumus Simple Payback."),
        ],
        left=6.9, top=2.60, width=5.6, height=4.1, size=12.5, gap=12,
    )

    # ---------- SLIDE 11: CLOSING ----------
    s11 = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s11, WHITE)

    add_text(s11, 0.9, 2.0, 11.4, 0.35, "PENUTUP", size=12, bold=True, color=NAVY)
    add_text(s11, 0.9, 2.45, 11.4, 1.1, "Terima Kasih  |  Sesi Tanya Jawab", size=40, bold=True, color=INK)
    add_line(s11, 0.9, 3.75, 11.4, color=RULE, thickness=0.75)
    add_text(s11, 0.9, 4.05, 11.4, 0.4, "Kode Python, Skema PostgreSQL, Bukti Harga, Power BI & Web Dashboard Interaktif:", size=13, color=MUTED)
    add_text(s11, 0.9, 4.45, 11.4, 0.45, "https://github.com/glacerous/kb_finpro", size=18, bold=True, color=NAVY)
    add_text(s11, 0.9, 5.15, 11.4, 0.4, "8 Kabupaten Studi: Gunungkidul, Bantul, Sleman, Kulon Progo, Klaten, Wonogiri, Purworejo, Kab. Magelang", size=11.5, bold=True, color=INK)
    add_text(s11, 0.9, 6.25, 11.4, 0.5, "Atribusi Data: Open-Meteo.com (CC BY 4.0)  |  NASA POWER Project  |  FAO-56  |  BPS DIY & Jateng", size=11, color=MUTED)
    s11.notes_slide.notes_text_frame.text = (
        "Sekian presentasi dari kelompok kami. Seluruh kode Python, skema PostgreSQL, bukti harga Tokopedia, "
        "dashboard Power BI, dan Web Dashboard Interaktif 8 kabupaten tersedia di repositori GitHub kami. "
        "Silakan jika Bapak/Ibu dosen atau teman-teman ada pertanyaan."
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT_PATH)
    print(f"Generated {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build_deck()
