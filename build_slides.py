"""Generate clean, editorial 10-slide presentation deck (.pptx) matching MINGGU-14-LK.md.

Design: warm off-white canvas, charcoal typography (Segoe UI), forest-green & amber
accents (agriculture + solar), takeaway headlines, minimal text, visual pipeline,
and full Indonesian speaker notes per slide.

Outputs: docs/Presentasi_Tugas_Besar_KB.pptx
"""

from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

OUT_PATH = Path("docs/Presentasi_Tugas_Besar_KB.pptx")

# Clean Minimal Palette (pure white canvas + initial navy blue)
BG_CREAM = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x11, 0x18, 0x27)
MUTED = RGBColor(0x4B, 0x55, 0x63)
RULE = RGBColor(0xE5, 0xE7, 0xEB)
FOREST = RGBColor(0x1B, 0x36, 0x5D)    # initial navy blue
FOREST_LT = RGBColor(0xEF, 0xF6, 0xFF) # soft blue highlight
AMBER = RGBColor(0x1B, 0x36, 0x5D)     # unified single blue accent
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

    add_text(slide, 0.7, 0.4, 8.0, 0.3, kicker.upper(), size=10, bold=True, color=FOREST)
    add_text(slide, 11.4, 0.4, 1.2, 0.3, f"{num} / 10", size=10, bold=False, color=MUTED, align=PP_ALIGN.RIGHT)
    add_text(slide, 0.7, 0.74, 11.9, 0.78, headline, size=23, bold=True, color=INK)
    add_line(slide, 0.7, 1.54, 11.9, color=RULE, thickness=0.75)

    if notes:
        slide.notes_slide.notes_text_frame.text = notes.strip()
    return slide


def add_stat_block(slide, left, top, width, number: str, label: str, detail: str, accent=FOREST):
    add_text(slide, left, top, width, 0.65, number, size=34, bold=True, color=accent)
    add_text(slide, left, top + 0.68, width, 0.32, label, size=13, bold=True, color=INK)
    add_text(slide, left, top + 0.98, width, 0.55, detail, size=11.5, color=MUTED)


def add_clean_list(slide, items: list[tuple[str, str]], left, top, width, height, size=13.5, gap=10):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, (head, body) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.line_spacing = 1.22
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
    # Subtle hairline border around screenshot
    pic.line.color.rgb = RULE
    pic.line.width = Pt(1.0)
    return pic


def add_minimal_table(slide, headers, rows, left, top, width, height, highlight_row: int | None = None, size=12):
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
            cell.fill.fore_color.rgb = FOREST_LT if is_hi else (WHITE if i % 2 == 0 else BG_CREAM)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
            r = p.add_run()
            r.text = val
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.bold = is_hi
            r.font.color.rgb = FOREST if is_hi else INK


def build_deck() -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # ---------- SLIDE 1: UPNVY ARCHITECTURAL COVER (UGM-STYLE) ----------
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s1, WHITE)
    # Full-bleed 16:9 UPNVY architectural sketch fading to white on the right
    s1.shapes.add_picture("docs/screenshots/upnvy_building_sketch.jpg", Inches(0), Inches(0), width=Inches(13.333), height=Inches(7.5))

    # Far-right slim vertical 2-tone bar (gold top, navy bottom — UGM reference style)
    GOLD = RGBColor(0xF5, 0xB8, 0x00)
    bar_top = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(13.11), Inches(0), Inches(0.223), Inches(4.15))
    bar_top.fill.solid()
    bar_top.fill.fore_color.rgb = GOLD
    bar_top.line.fill.background()
    bar_bot = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(13.11), Inches(4.15), Inches(0.223), Inches(3.35))
    bar_bot.fill.solid()
    bar_bot.fill.fore_color.rgb = FOREST
    bar_bot.line.fill.background()

    # Top-left university identity
    add_text(
        s1, 0.55, 0.45, 5.2, 0.75,
        'UNIVERSITAS PEMBANGUNAN NASIONAL\n"VETERAN" YOGYAKARTA',
        size=13.5, bold=True, color=FOREST,
    )

    # Right-side Title Case headline, gold short bar, subtitle & team
    add_text(
        s1, 6.85, 1.75, 5.85, 2.0,
        "Prediksi Kebutuhan Irigasi Harian\n& Kelayakan ROI Pompa Air\nTenaga Surya (8 Kabupaten)",
        size=28, bold=True, color=FOREST,
    )
    add_line(s1, 6.85, 3.92, 0.85, color=GOLD, thickness=3.0)
    add_text(
        s1, 6.85, 4.18, 5.85, 0.75,
        "Tugas Besar Kecerdasan Bisnis (Kelas SI-C) - Studi Petani Padi\ndi DIY dan Jawa Tengah Selatan (2011-2025)",
        size=12.5, color=MUTED,
    )
    add_text(
        s1, 6.85, 5.0, 5.85, 1.25,
        "Muhammad Barkah Ramadhan (124240004)\n"
        "Azzaky Raihan Ramdhani (124240018)  |  Syahrul Alfiansyah (124240005)\n"
        "Muhammad Ariel Saputra (124240010)  |  Ahmad Ridwan Alhadi (124240027)",
        size=10.5, color=INK,
    )

    # Bottom-left domain & bottom-right UPNVY motto
    add_text(s1, 0.55, 6.85, 3.0, 0.35, "u p n y k . a c . i d", size=11, bold=True, color=FOREST)
    tb_m = add_text(
        s1, 8.6, 6.62, 4.15, 0.65,
        "Widya Mwat Yasa\nProgram Studi Sistem Informasi, 2026",
        size=11.5, bold=True, color=FOREST, align=PP_ALIGN.RIGHT,
    )
    for p in tb_m.text_frame.paragraphs:
        for r in p.runs:
            r.font.italic = True
    s1.notes_slide.notes_text_frame.text = (
        "Selamat pagi/siang Bapak/Ibu dosen dan teman-teman. Kami dari kelas SI-C akan mempresentasikan "
        "proyek Kecerdasan Bisnis tentang kelayakan ganti pompa diesel ke pompa air tenaga surya untuk "
        "petani padi di 8 kabupaten sekitar DIY, lengkap dengan prediksi irigasi harian dan dashboard Power BI."
    )

    # ---------- SLIDE 2: CONTEXT & BUSINESS QUESTION ----------
    s2 = new_slide(
        prs, 2, "Konteks & Masalah Bisnis",
        "Produksi padi DIY turun 15%, sementara biaya solar terancam naik 3,5x pasca-2026",
        notes=(
            "Latar belakangnya sederhana: produksi padi DIY tahun 2024 turun 14,95%, paling parah di Gunungkidul, "
            "Bantul, dan Sleman. Petani selama ini mengandalkan pompa diesel, tapi Biosolar subsidi Rp 6.800/L "
            "hanya dijamin sampai Desember 2026, sedangkan Dexlite Rp 23.700/L. Pompa tenaga surya bebas solar, "
            "tapi modal awalnya besar. Jadi ada 3 pertanyaan bisnis utama yang kami jawab."
        ),
    )
    add_stat_block(s2, 0.7, 1.95, 3.6, "-14,95%", "Produksi Padi DIY 2024", "Kontraksi terparah di Gunungkidul, Bantul, dan Sleman (BPS).", accent=AMBER)
    add_stat_block(s2, 4.85, 1.95, 3.6, "3,5x", "Lonjakan Harga Solar", "Biosolar subsidi Rp 6.800 (s.d. Des 2026) vs Dexlite Rp 23.700/L.", accent=AMBER)
    add_stat_block(s2, 9.0, 1.95, 3.6, "8 Kab.", "Cakupan 15 Tahun", "DIY & Jateng Selatan (2011-2025), 1,05 juta baris cuaca per jam.", accent=FOREST)

    add_line(s2, 0.7, 3.95, 11.9, color=RULE, thickness=1.0)
    add_text(s2, 0.7, 4.18, 11.9, 0.35, "TIGA PERTANYAAN BISNIS UTAMA", size=11, bold=True, color=FOREST)
    add_clean_list(
        s2,
        [
            ("01  Kelayakan ROI:", "Di kabupaten mana & kapasitas berapa (1, 3, 5 kWp) pompa surya paling cepat balik modal? Individu (1 ha) vs Kelompok Tani (5 ha)?"),
            ("02  Bukti Statistik:", "Apakah beda kebutuhan air antar 8 kabupaten & antar musim benar-benar nyata secara statistik?"),
            ("03  Prediksi H+1:", "Bisakah kita memprediksi besok sawah butuh disiram atau tidak, sambil menekan risiko gagal siram?"),
        ],
        left=0.7, top=4.62, width=11.9, height=2.3, size=14, gap=12,
    )

    # ---------- SLIDE 3: VISUAL 5-STEP PIPELINE ----------
    s3 = new_slide(
        prs, 3, "Pendekatan & Metodologi",
        "Pipeline BI end-to-end: dari API cuaca per jam hingga keputusan ROI di Power BI",
        notes=(
            "Alur kerja kami mengikuti 5 tahap standar Kecerdasan Bisnis: tarik data API idempotent, "
            "muat ke PostgreSQL skema bintang sambil hitung debit pompa Gowa dan neraca air padi NFR, "
            "uji statistik ANOVA dan t-test, latih model ML H+1 anti-leakage, lalu simulasi ROI 192 skenario "
            "dan tampilkan di Power BI."
        ),
    )
    steps = [
        ("01", "ETL Ingestion", "Python + API", "1,05 jt baris/jam Open-Meteo + 43,8 rb NASA POWER (0 null, idempotent)."),
        ("02", "Data Warehouse", "PostgreSQL Kimball", "3 Dimensi + 5 Fakta. Kurva debit Gowa (cut-in 30 W/m2) & rumus NFR padi."),
        ("03", "Uji Statistik", "SciPy", "One-Way ANOVA & Kruskal-Wallis (8 kab.), Welch t-test (Kemarau vs Hujan)."),
        ("04", "Model ML H+1", "Scikit-Learn", "Temporal split 2011-22 vs 2023-25. Baseline vs LR/RF + tuning FN:FP = 3:1."),
        ("05", "ROI & Power BI", "192 Skenario", "Simulasi CAPEX marketplace, BEP Biosolar vs Dexlite -> 3 halaman DAX."),
    ]
    for i, (num, title, tool, desc) in enumerate(steps):
        x = 0.7 + i * 2.42
        add_text(s3, x, 2.2, 2.15, 0.4, num, size=24, bold=True, color=FOREST)
        add_text(s3, x, 2.75, 2.15, 0.35, title, size=14, bold=True, color=INK)
        add_text(s3, x, 3.1, 2.15, 0.3, tool, size=11, bold=True, color=MUTED)
        add_line(s3, x, 3.5, 2.1, color=RULE, thickness=0.75)
        add_text(s3, x, 3.7, 2.15, 2.1, desc, size=11.5, color=MUTED)

    add_text(s3, 0.7, 6.35, 11.9, 0.5, "Rumus inti padi sawah:  NFR = max(0,  Kc * ET0 + P + WLR - 0.8 * Rain)  +  olah lahan 250 mm/musim di simulasi ROI.", size=12, bold=True, color=INK)

    # ---------- SLIDE 4: DATA FOUNDATION ----------
    s4 = new_slide(
        prs, 4, "Fondasi Data & Validasi",
        "Skema Bintang Kimball (0 null); Open-Meteo menangkap mikroklimat yang luput dari NASA",
        notes=(
            "Ini tampilan Model View Skema Bintang Kimball kami: 3 tabel dimensi terhubung satu-ke-banyak "
            "ke tabel fakta. Temuan menarik saat validasi silang: rata-rata radiasi NASA POWER identik 18,32 "
            "di 8 kabupaten karena grid satelitnya kasar (111 km), sedangkan Open-Meteo menangkap beda lokal "
            "nyata (Magelang 17,46 vs Klaten 18,55) dengan korelasi harian kuat r = 0,74-0,78."
        ),
    )
    add_framed_image(s4, "docs/screenshots/pbi_model_view_star_schema.png", 0.7, 1.85, 7.6)
    add_stat_block(s4, 8.65, 1.9, 3.9, "1,05 Juta", "Baris Cuaca Per Jam", "0 missing values, dimuat idempotent via PostgreSQL COPY + UPSERT.", accent=FOREST)
    add_stat_block(s4, 8.65, 3.85, 3.9, "r = 0,74-0,78", "Validasi Silang NASA", "NASA seragam 18,32 (grid 111 km); Open-Meteo tangkap variasi lokal 17,46-18,55 MJ/m2.", accent=AMBER)

    # ---------- SLIDE 5: DESCRIPTIVE & STATS ----------
    s5 = new_slide(
        prs, 5, "Statistik & Sinergi Agroklimat",
        "Gunungkidul & Klaten paling haus air - dan matahari justru paling terik saat kemarau",
        notes=(
            "ANOVA membuktikan perbedaan kebutuhan air antar 8 kabupaten sangat signifikan (F = 42,28): "
            "Gunungkidul dan Klaten 34% lebih tinggi dari Magelang. Grafik kiri membuktikan sinergi alami: "
            "saat kebutuhan air melonjak 2x di kemarau, radiasi surya justru naik ke puncaknya. Grafik kanan "
            "langsung menangkap lonjakan kekeringan El Nino 2018, 2019, dan 2023."
        ),
    )
    add_framed_image(s5, "docs/screenshots/pbi_page2_climate_demand.png", 0.7, 1.85, 7.7)
    add_stat_block(s5, 8.75, 1.85, 3.8, "F = 42,28", "ANOVA 8 Kabupaten (p < 0,001)", "Gunungkidul (3,30) & Klaten (3,25) butuh air 34% > Magelang (2,46 mm/hr).", accent=FOREST)
    add_stat_block(s5, 8.75, 3.7, 3.8, "2x Lipat", "Lonjakan Kemarau + Sinergi", "NFR naik 2,30 -> 4,47 mm/hr bersamaan radiasi naik 17,36 -> 18,93 MJ/m2.", accent=AMBER)
    add_text(s5, 8.75, 5.65, 3.8, 0.9, "Tahun El Nino (2018, 2019, 2023) terekam jelas sebagai puncak hari irigasi.", size=12, bold=True, color=INK)

    # ---------- SLIDE 6: PREDICTIVE MODEL ----------
    s6 = new_slide(
        prs, 6, "Model Prediktif ML H+1",
        "Logistic Regression unggul; tuning biaya 3:1 memangkas gagal siram sebesar 90%",
        notes=(
            "Pada 5.808 hari uji mandiri 2023-2025, Logistic Regression menjadi model terbaik (ROC-AUC 0,794), "
            "mengalahkan kedua baseline dan tipis di atas Random Forest. Karena gagal siram (FN) jauh lebih "
            "mahal dari siaga berlebih, threshold diturunkan ke 0,21 (rasio 3:1): hari gagal siram turun 90% "
            "dari 849 menjadi hanya 88 hari (Recall 97,3%)."
        ),
    )
    add_stat_block(s6, 0.7, 1.85, 3.5, "0,794", "ROC-AUC Terbaik", "Logistic Regression unggul atas baseline & Random Forest (0,790).", accent=FOREST)
    add_stat_block(s6, 4.75, 1.85, 3.5, "97,3%", "Recall Setelah Tuning", "Threshold t = 0,21 (FN:FP = 3:1) dituning murni di validasi 2021-2022.", accent=AMBER)
    add_stat_block(s6, 8.8, 1.85, 3.8, "-90%", "Penurunan Gagal Siram", "False Negative turun dari 849 (persistence) menjadi hanya 88 hari.", accent=FOREST)

    add_minimal_table(
        s6,
        ["Model (Test 2023-2025, 5.808 hari)", "Acc", "Recall", "F1", "AUC", "FN (Gagal)", "FP"],
        [
            ["Climatology (baseline)", "0,598", "0,546", "0,606", "0,651", "1.497", "839"],
            ["Persistence (baseline)", "0,711", "0,742", "0,745", "-", "849", "828"],
            ["Logistic Regression (t = 0,50)", "0,731", "0,736", "0,757", "0,794", "871", "689"],
            ["Logistic Regression (3:1, t = 0,21)  [Dipilih]", "0,601", "0,973", "0,735", "0,794", "88", "2.227"],
            ["Random Forest (t = 0,50)", "0,727", "0,733", "0,753", "0,790", "880", "704"],
        ],
        left=0.7, top=3.85, width=11.9, height=2.9, highlight_row=3, size=12,
    )

    # ---------- SLIDE 7: POWER BI LIVE DEMO ----------
    s7 = new_slide(
        prs, 7, "Operasionalisasi & Power BI",
        "Dashboard 3 halaman (kbfinpro.pbix) siap pakai dengan 6 DAX & Drill-Through",
        notes=(
            "Seluruh hasil ROI dan ML terhubung ke Power BI Desktop (mode Import). Di tahap ini lakukan "
            "live demo 2-3 menit: toggle Biosolar ke Dexlite & Individu ke Kelompok Tani di Page 1, "
            "klik kanan Gunungkidul -> Drill through ke Page 2, lalu tunjukkan kalibrasi di Page 3."
        ),
    )
    add_framed_image(s7, "docs/screenshots/pbi_page1_executive_roi.png", 0.7, 1.85, 5.8)
    add_framed_image(s7, "docs/screenshots/pbi_page3_ml_prediction.png", 6.8, 1.85, 5.8)
    add_text(s7, 0.7, 5.25, 5.8, 0.3, "Page 1: Executive ROI (4 slicer single-select + ranking BEP)", size=11, bold=True, color=MUTED)
    add_text(s7, 6.8, 5.25, 5.8, 0.3, "Page 3: ML H+1 (Recall 97,3%, Confusion Matrix, kurva kalibrasi)", size=11, bold=True, color=MUTED)
    add_line(s7, 0.7, 5.72, 11.9, color=RULE, thickness=1.0)
    add_text(
        s7, 0.7, 5.9, 11.9, 0.9,
        "Alur Live Demo:   (1) Toggle Biosolar -> Dexlite & Individu -> Kelompok Tani   ->   (2) Klik kanan Gunungkidul -> Drill through Climate & Demand   ->   (3) Cek kalibrasi model di Page 3.",
        size=13, bold=True, color=FOREST,
    )

    # ---------- SLIDE 8: ETHICS & LIMITATIONS ----------
    s8 = new_slide(
        prs, 8, "Etika, Tata Kelola & Batasan",
        "Bebas data pribadi (UU PDP No. 27/2022) dengan 4 batasan metodologi yang transparan",
        notes=(
            "Data cuaca publik tanpa PII sesuai prinsip minimalisasi data UU PDP No. 27/2022. "
            "Model Card memperjelas batas penggunaan. Kami juga mencatat jujur 4 batasan utama agar "
            "pengambil keputusan memahami asumsi di balik angka BEP."
        ),
    )
    # Left column: Governance (no box clutter)
    add_text(s8, 0.7, 2.0, 5.6, 0.35, "TATA KELOLA & MODEL CARD", size=12, bold=True, color=FOREST)
    add_line(s8, 0.7, 2.4, 5.5, color=RULE, thickness=0.75)
    add_clean_list(
        s8,
        [
            ("UU PDP No. 27/2022:", "Data iklim publik tanpa PII; wajib pseudonimisasi jika terhubung ke data Gapoktan."),
            ("Intended Use:", "Sinyal siaga irigasi harian (H+1) padi sawah dengan pengawasan manusia."),
            ("Out-of-Scope:", "Bukan otomasi saklar tanpa manusia dan bukan untuk komoditas non-padi."),
            ("Fairness:", "Dilatih pada data iklim wilayah tanpa variabel status kepemilikan lahan."),
        ],
        left=0.7, top=2.62, width=5.6, height=4.0, size=13, gap=13,
    )

    # Right column: Limitations
    add_text(s8, 6.9, 2.0, 5.6, 0.35, "4 BATASAN YANG DIAKUI TERBUKA", size=12, bold=True, color=FOREST)
    add_line(s8, 6.9, 2.4, 5.6, color=RULE, thickness=0.75)
    add_clean_list(
        s8,
        [
            ("1. Data Reanalisis:", "Open-Meteo & NASA bukan sensor stasiun fisik BMKG di tiap petak sawah."),
            ("2. Label Sintetis:", "Status irigasi dari rumus NFR FAO/KP-01 & kalender asumsi MT1-MT2."),
            ("3. Ekstrapolasi Pompa:", "Kurva debit dari 1 studi Gowa (cut-in 30 W/m2) diskalakan ke 3 & 5 kWp."),
            ("4. Umur Motor Pompa:", "Biaya ganti motor DC (tahun ke-5-7) belum dimodelkan dalam arus kas."),
        ],
        left=6.9, top=2.62, width=5.6, height=4.0, size=13, gap=13,
    )

    # ---------- SLIDE 9: RECOMMENDATION & ROI ----------
    s9 = new_slide(
        prs, 9, "Rekomendasi & Kelayakan ROI",
        "Kelompok Tani 5 kWp (5 ha) memangkas BEP ke 1,2-2,8 tahun; hindari over-sizing di 1 ha",
        notes=(
            "Memakai CAPEX riil Tokopedia (+15% pasang): 1 kWp Rp 8,5-15,5 jt dan 5 kWp Rp 35-65 jt. "
            "Dua kesimpulan besar: untuk individu 1 ha, 1 kWp paling efisien (jangan pasang 5 kWp). "
            "Untuk skala besar, Kelompok Tani 5 kWp di 5 ha membuat 4 kabupaten sudah BEP di bawah 5 tahun "
            "bahkan dengan Biosolar subsidi, dan seluruh 8 kabupaten BEP 1,20-2,77 tahun pada Dexlite."
        ),
    )
    add_minimal_table(
        s9,
        ["Skenario (0,04 L/m3)", "CAPEX Riil", "BEP Biosolar", "BEP Dexlite", "Kesimpulan"],
        [
            ["Individu 1 ha  |  1 kWp (Gunungkidul)", "Rp 8,5-15,5 jt", "5,48 - 10,99 thn", "1,46 - 2,73 thn", "Optimal untuk 1 ha"],
            ["Individu 1 ha  |  5 kWp (Gunungkidul)", "Rp 35-65 jt", "12,3+ thn", "3,06 - 5,99 thn", "Over-sizing (Hindari)"],
            ["Kelompok 5 ha  |  5 kWp (Gunungkidul)", "Rp 35-65 jt", "4,43 - 8,90 thn", "1,20 - 2,27 thn", "Prioritas #1"],
            ["Kelompok 5 ha  |  5 kWp (Klaten)", "Rp 35-65 jt", "4,54 - 9,15 thn", "1,22 - 2,32 thn", "Prioritas #2"],
            ["Kelompok 5 ha  |  5 kWp (Semua 8 Kab.)", "Rp 35-65 jt", "4,43 - 11,20 thn", "1,20 - 2,77 thn", "Semua Layak (Dexlite)"],
        ],
        left=0.7, top=1.85, width=11.9, height=2.9, highlight_row=2, size=12,
    )
    add_clean_list(
        s9,
        [
            ("1. Dinas Pertanian & ESDM:", "Prioritaskan hibah komunal 5 kWp (5 ha) ke Gunungkidul & Klaten sebelum batas subsidi Des 2026."),
            ("2. Petani & Gapoktan:", "Sisihkan 15% penghematan solar tahunan untuk dana cadangan (sinking fund) ganti motor pompa."),
            ("3. Operasional Harian:", "Pakai sinyal prediksi H+1 (Recall 97,3%) untuk jadwal pompa & verifikasi kalender ke KATAM."),
        ],
        left=0.7, top=5.05, width=11.9, height=2.0, size=13, gap=8,
    )

    # ---------- SLIDE 10: CLOSING ----------
    s10 = prs.slides.add_slide(prs.slide_layouts[6])
    set_bg(s10, WHITE)

    add_text(s10, 0.9, 2.1, 11.4, 0.35, "PENUTUP", size=12, bold=True, color=FOREST)
    add_text(s10, 0.9, 2.55, 11.4, 1.1, "Terima Kasih  |  Sesi Tanya Jawab", size=40, bold=True, color=INK)
    add_line(s10, 0.9, 3.85, 11.4, color=RULE, thickness=0.75)
    add_text(s10, 0.9, 4.15, 11.4, 0.4, "Repositori Kode, Data Olahan, Bukti Harga & Dashboard Power BI:", size=13, color=MUTED)
    add_text(s10, 0.9, 4.55, 11.4, 0.45, "https://github.com/glacerous/kb_finpro", size=18, bold=True, color=FOREST)
    add_text(s10, 0.9, 6.25, 11.4, 0.5, "Atribusi Data: Open-Meteo.com (CC BY 4.0)  |  NASA POWER Project  |  FAO-56  |  BPS DIY & Jateng", size=11, color=MUTED)
    s10.notes_slide.notes_text_frame.text = (
        "Sekian presentasi dari kelompok kami. Seluruh kode Python, skema SQL, bukti harga Tokopedia, "
        "dan file dashboard Power BI tersedia di repositori GitHub kami. Silakan jika ada pertanyaan."
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT_PATH)
    print(f"Generated {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build_deck()
