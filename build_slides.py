"""Generate 10-slide presentation deck (.pptx) matching MINGGU-14-LK.md outline.

Outputs: docs/Presentasi_Tugas_Besar_KB.pptx (with Indonesian speaker notes per slide).
"""

from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

OUT_PATH = Path("docs/Presentasi_Tugas_Besar_KB.pptx")

NAVY = RGBColor(0x1B, 0x36, 0x5D)
DARK = RGBColor(0x1E, 0x29, 0x3B)
MUTED = RGBColor(0x64, 0x74, 0x8B)
ACCENT = RGBColor(0x0F, 0x76, 0x6E)
LIGHT_BG = RGBColor(0xF1, 0xF5, 0xF9)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


def new_slide(prs: Presentation, title: str, subtitle: str = "", notes: str = ""):
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank

    # Top accent bar
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
    bar.fill.solid()
    bar.fill.fore_color.rgb = NAVY
    bar.line.fill.background()

    # Title
    tb = slide.shapes.add_textbox(Inches(0.6), Inches(0.3), Inches(12.1), Inches(0.65))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = title
    r.font.name = "Calibri"
    r.font.size = Pt(26)
    r.font.bold = True
    r.font.color.rgb = NAVY

    if subtitle:
        p2 = tf.add_paragraph()
        p2.space_before = Pt(2)
        r2 = p2.add_run()
        r2.text = subtitle
        r2.font.name = "Calibri"
        r2.font.size = Pt(13)
        r2.font.color.rgb = MUTED

    if notes:
        slide.notes_slide.notes_text_frame.text = notes.strip()
    return slide


def add_bullets(slide, items: list[tuple[str, str]], left=0.6, top=1.35, width=12.1, height=5.5, font_size=16):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, (bold_part, normal_part) in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(10)
        p.line_spacing = 1.2
        if bold_part:
            r0 = p.add_run()
            r0.text = "• " + bold_part
            r0.font.name = "Calibri"
            r0.font.size = Pt(font_size)
            r0.font.bold = True
            r0.font.color.rgb = DARK
        r1 = p.add_run()
        r1.text = ("" if bold_part else "• ") + normal_part
        r1.font.name = "Calibri"
        r1.font.size = Pt(font_size)
        r1.font.color.rgb = DARK


def add_kpi_card(slide, left, top, width, height, label: str, value: str, sub: str = ""):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    box.fill.solid()
    box.fill.fore_color.rgb = LIGHT_BG
    box.line.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)

    tf = box.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    p0.alignment = PP_ALIGN.CENTER
    r0 = p0.add_run()
    r0.text = label
    r0.font.name = "Calibri"
    r0.font.size = Pt(12)
    r0.font.color.rgb = MUTED

    p1 = tf.add_paragraph()
    p1.alignment = PP_ALIGN.CENTER
    p1.space_before = Pt(4)
    r1 = p1.add_run()
    r1.text = value
    r1.font.name = "Calibri"
    r1.font.size = Pt(24)
    r1.font.bold = True
    r1.font.color.rgb = NAVY

    if sub:
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        p2.space_before = Pt(2)
        r2 = p2.add_run()
        r2.text = sub
        r2.font.name = "Calibri"
        r2.font.size = Pt(11)
        r2.font.color.rgb = ACCENT


def add_simple_table(slide, headers: list[str], rows: list[list[str]], left, top, width, height, font_size=12):
    tbl_shape = slide.shapes.add_table(len(rows) + 1, len(headers), Inches(left), Inches(top), Inches(width), Inches(height))
    tbl = tbl_shape.table
    for j, h in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        p = cell.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = h
        r.font.name = "Calibri"
        r.font.size = Pt(font_size)
        r.font.bold = True
        r.font.color.rgb = WHITE

    for i, rvals in enumerate(rows):
        for j, val in enumerate(rvals):
            cell = tbl.cell(i + 1, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = LIGHT_BG if i % 2 == 1 else WHITE
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
            r = p.add_run()
            r.text = val
            r.font.name = "Calibri"
            r.font.size = Pt(font_size)
            r.font.color.rgb = DARK


def build_deck() -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # ---------- SLIDE 1: TITLE ----------
    s1 = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()

    tb = s1.shapes.add_textbox(Inches(0.9), Inches(1.4), Inches(11.5), Inches(4.8))
    tf = tb.text_frame
    tf.word_wrap = True
    p0 = tf.paragraphs[0]
    r0 = p0.add_run()
    r0.text = "TUGAS BESAR KECERDASAN BISNIS — KELAS SI-C"
    r0.font.name = "Calibri"
    r0.font.size = Pt(14)
    r0.font.bold = True
    r0.font.color.rgb = RGBColor(0x93, 0xC5, 0xFD)

    p1 = tf.add_paragraph()
    p1.space_before = Pt(14)
    r1 = p1.add_run()
    r1.text = "Prediksi Kebutuhan Irigasi Harian & Kelayakan ROI\nPompa Air Tenaga Surya bagi Petani Padi\ndi DIY dan Sekitarnya (8 Kabupaten)"
    r1.font.name = "Calibri"
    r1.font.size = Pt(34)
    r1.font.bold = True
    r1.font.color.rgb = WHITE

    p2 = tf.add_paragraph()
    p2.space_before = Pt(28)
    r2 = p2.add_run()
    r2.text = (
        "Muhammad Barkah Ramadhan (124240004)  |  Azzaky Raihan Ramdhani (124240018)\n"
        "Syahrul Alfiansyah (124240005)  |  Muhammad Ariel Saputra (124240010)  |  Ahmad Ridwan Alhadi (124240027)\n\n"
        "Program Studi Sistem Informasi — UPN 'Veteran' Yogyakarta — November 2026"
    )
    r2.font.name = "Calibri"
    r2.font.size = Pt(14)
    r2.font.color.rgb = RGBColor(0xE2, 0xE8, 0xF0)
    s1.notes_slide.notes_text_frame.text = (
        "Selamat pagi/siang Bapak/Ibu dosen dan teman-teman. Kami dari kelas SI-C akan mempresentasikan "
        "proyek Kecerdasan Bisnis tentang kelayakan ganti pompa diesel ke pompa air tenaga surya untuk "
        "petani padi di 8 kabupaten sekitar DIY, lengkap dengan prediksi irigasi harian dan dashboard Power BI."
    )

    # ---------- SLIDE 2: CONTEXT & BUSINESS QUESTION ----------
    s2 = new_slide(
        prs,
        "2. Context & Business Question",
        "Mengapa petani padi DIY & sekitarnya butuh hitungan berbasis data sebelum beralih ke pompa surya?",
        notes=(
            "Latar belakangnya sederhana: produksi padi DIY tahun 2024 turun 14,95%, paling parah di Gunungkidul, "
            "Bantul, dan Sleman. Petani selama ini mengandalkan pompa diesel, tapi Biosolar subsidi Rp 6.800/L "
            "hanya dijamin sampai Desember 2026 — sedangkan Dexlite Rp 23.700/L, hampir 3,5 kali lipat. "
            "Pompa tenaga surya bebas solar, tapi modal awalnya besar. Jadi pertanyaan bisnis utama kami: "
            "di kabupaten mana dan ukuran berapa pompa surya paling cepat balik modal, apakah lebih cocok untuk "
            "petani individu atau kelompok tani, dan bisakah kita menebak besok sawah butuh disiram atau tidak?"
        ),
    )
    add_kpi_card(s2, 0.6, 1.35, 3.8, 1.5, "Produksi Padi DIY 2024", "-14,95%", "Terparah: Gunungkidul, Bantul, Sleman (BPS)")
    add_kpi_card(s2, 4.75, 1.35, 3.8, 1.5, "Risiko Harga Solar", "3,5x Lipat", "Biosolar Rp 6.800 vs Dexlite Rp 23.700/L")
    add_kpi_card(s2, 8.9, 1.35, 3.8, 1.5, "Cakupan Studi", "8 Kabupaten", "DIY & Jateng Selatan, 15 Tahun (2011-2025)")
    add_bullets(
        s2,
        [
            ("Pertanyaan Bisnis 1 (ROI & BEP): ", "Di kabupaten mana & kapasitas berapa (1, 3, 5 kWp) pompa surya paling cepat balik modal? Individu (1 ha) vs Kelompok Tani (1 ha/kWp)?"),
            ("Pertanyaan Bisnis 2 (Statistik): ", "Apakah kebutuhan air & radiasi matahari berbeda signifikan antar 8 kabupaten dan antara musim kemarau vs hujan?"),
            ("Pertanyaan Bisnis 3 (Prediksi H+1): ", "Bisakah kita memprediksi besok sawah butuh irigasi atau tidak, dengan meminimalkan risiko gagal menyiram?"),
        ],
        top=3.2,
    )

    # ---------- SLIDE 3: APPROACH & METHODOLOGY ----------
    s3 = new_slide(
        prs,
        "3. Approach & Methodology",
        "Pipeline Business Intelligence end-to-end (Python -> PostgreSQL Kimball -> Machine Learning -> Power BI)",
        notes=(
            "Alur kerja kami mengikuti pipeline BI dari hulu ke hilir dalam 5 tahap utama. "
            "Pertama, menarik data cuaca 15 tahun per jam dari Open-Meteo dan validasi harian dari NASA POWER. "
            "Kedua, merapikan data ke Data Warehouse PostgreSQL skema bintang, sambil menghitung debit pompa surya "
            "per jam memakai kurva lapangan Gowa dan kebutuhan air padi NFR standar FAO/KP-01. "
            "Ketiga, uji statistik ANOVA dan Welch t-test. Keempat, melatih model ML prediksi besok (H+1) "
            "dengan split waktu ketat supaya tidak bocor. Kelima, simulasi ROI/BEP 192 skenario dan visualisasi "
            "interaktif di Power BI."
        ),
    )
    add_bullets(
        s3,
        [
            ("1. ETL Ingestion (Python): ", "Tarik 1.051.968 baris per jam (Open-Meteo) + 43.832 harian (NASA POWER), 2011-2025, 0 null, idempotent."),
            ("2. Data Warehouse (PostgreSQL Kimball): ", "Skema Bintang (3 Dimensi + 5 Fakta). Hitung debit pompa DC (kurva piecewise Gowa, cut-in 30 W/m2) & neraca air padi NFR = max(0, Kc*ET0 + P + WLR - 0.8*Rain)."),
            ("3. Statistik Inferensial (SciPy): ", "One-Way ANOVA & Kruskal-Wallis (8 kabupaten), Welch t-test (Kemarau vs Hujan, MT2 vs MT1)."),
            ("4. Predictive ML H+1 (Scikit-Learn): ", "Temporal split 2011-2022 (train) vs 2023-2025 (test). Bandingkan Climatology, Persistence, Logistic Regression, Random Forest + tuning threshold FN:FP = 3:1."),
            ("5. Simulasi ROI & Power BI: ", "192 skenario (8 daerah x 3 kapasitas x 2 mode lahan x 2 harga BBM x 2 efisiensi diesel) -> Dashboard 3 halaman."),
        ],
        top=1.4,
        font_size=15,
    )

    # ---------- SLIDE 4: DATA FOUNDATION ----------
    s4 = new_slide(
        prs,
        "4. Data Foundation (DW, ETL & Validasi)",
        "Skema Bintang Kimball di PostgreSQL (kb_solar_irrigation) + validasi silang Open-Meteo vs NASA POWER",
        notes=(
            "Ini tampilan Model View Skema Bintang Kimball kami di PostgreSQL dan Power BI: 3 tabel dimensi "
            "(wilayah, tanggal, skenario) terhubung satu-ke-banyak ke tabel fakta. "
            "Temuan menarik saat validasi silang: rata-rata radiasi NASA POWER identik 18,32 di 8 kabupaten "
            "karena resolusi grid satelitnya kasar (1x1 derajat atau 111 km). Sebaliknya, Open-Meteo menangkap "
            "beda lokal nyata (Magelang 17,46 vs Klaten 18,55) dengan korelasi harian kuat r = 0,74 sampai 0,78."
        ),
    )
    s4.shapes.add_picture("docs/screenshots/pbi_model_view_star_schema.png", Inches(0.6), Inches(1.4), width=Inches(7.3))
    add_bullets(
        s4,
        [
            ("Volume Data: ", "1.051.968 baris per jam + 43.832 harian (0 missing values)."),
            ("Idempotent ETL: ", "PostgreSQL COPY + ON CONFLICT DO UPDATE (aman diulang)."),
            ("Validasi Silang: ", "Korelasi harian Open-Meteo vs NASA POWER r = 0,74-0,78."),
            ("Temuan Grid: ", "NASA POWER identik 18,32 di 8 kab. (grid 1x1 deg); Open-Meteo tangkap beda lokal (17,46-18,55 MJ/m2/hr)."),
        ],
        left=8.1,
        top=1.5,
        width=4.7,
        font_size=14,
    )

    # ---------- SLIDE 5: DASHBOARD & DESCRIPTIVE INSIGHTS ----------
    s5 = new_slide(
        prs,
        "5. Dashboard & Descriptive Insights (Statistik)",
        "Perbedaan antar 8 kabupaten sangat signifikan (ANOVA F = 42,28) dan terjadi sinergi alami di musim kemarau",
        notes=(
            "Hasil uji statistik membuktikan dua hal penting. Pertama, ANOVA menunjukkan perbedaan kebutuhan air "
            "antar 8 kabupaten sangat signifikan (F = 42,28): Gunungkidul dan Klaten butuh air 34% lebih tinggi "
            "daripada Magelang. Kedua, grafik kiri membuktikan sinergi alami: tepat saat kemarau ketika kebutuhan "
            "air sawah melonjak hampir 2 kali lipat (4,47 vs 2,30 mm/hari), radiasi matahari justru naik ke puncaknya. "
            "Grafik kanan juga langsung menangkap lonjakan hari kering pada tahun El Nino 2018, 2019, dan 2023."
        ),
    )
    s5.shapes.add_picture("docs/screenshots/pbi_page2_climate_demand.png", Inches(0.6), Inches(1.4), width=Inches(7.5))
    add_bullets(
        s5,
        [
            ("ANOVA 8 Kabupaten: ", "F = 42,28 (p = 9,14e-60). Tertinggi: Gunungkidul (3,30 mm/hr) & Klaten (3,25). Terendah: Magelang (2,46)."),
            ("Welch t-test Musim: ", "NFR Kemarau (4,47) hampir 2x Hujan (2,30 mm/hr, t = 56,39)."),
            ("Sinergi Alami: ", "Saat sawah paling butuh air di kemarau, radiasi surya justru naik (18,93 vs 17,36 MJ/m2/hr)."),
            ("Deteksi El Nino: ", "Lonjakan hari irigasi terlihat jelas di tahun kering 2018, 2019, dan 2023."),
        ],
        left=8.3,
        top=1.5,
        width=4.5,
        font_size=14,
    )

    # ---------- SLIDE 6: PREDICTIVE MODEL ----------
    s6 = new_slide(
        prs,
        "6. Predictive Model (ML H+1 & Threshold Optimization)",
        "Logistic Regression unggul atas baseline & Random Forest; tuning FN:FP = 3:1 pangkas gagal irigasi 90%",
        notes=(
            "Untuk prediksi besok perlu irigasi atau tidak (H+1), kami uji pada 5.808 hari out-of-sample 2023-2025. "
            "Hasilnya, Logistic Regression yang lebih sederhana justru menjadi model terbaik dengan ROC-AUC 0,794, "
            "mengalahkan baseline Climatology, Persistence, dan tipis di atas Random Forest. "
            "Karena gagal menyiram padi (False Negative) jauh lebih mahal daripada siaga berlebih, kami turunkan "
            "threshold ke 0,21 (rasio biaya 3:1). Hasilnya, gagal irigasi turun 90% dari 849 hari menjadi hanya "
            "88 hari, dengan Recall 97,3%."
        ),
    )
    add_simple_table(
        s6,
        ["Model / Konfigurasi", "Acc", "Recall", "F1", "ROC-AUC", "FN (Gagal)", "FP"],
        [
            ["Climatology (baseline)", "0,598", "0,546", "0,606", "0,651", "1.497", "839"],
            ["Persistence (baseline)", "0,711", "0,742", "0,745", "-", "849", "828"],
            ["Logistic Regression (t=0,50)", "0,731", "0,736", "0,757", "0,794", "871", "689"],
            ["Logistic Regression (3:1, t=0,21)", "0,601", "0,973", "0,735", "0,794", "88", "2.227"],
            ["Random Forest (t=0,50)", "0,727", "0,733", "0,753", "0,790", "880", "704"],
            ["Random Forest (3:1, t=0,24)", "0,610", "0,967", "0,738", "0,790", "109", "2.157"],
        ],
        left=0.6,
        top=1.45,
        width=12.1,
        height=3.4,
        font_size=13,
    )
    add_bullets(
        s6,
        [
            ("Anti-Leakage: ", "Train 2011-2022, tuning threshold murni di validasi 2021-2022, uji akhir di 2023-2025."),
            ("Top 5 Fitur Penggerak: ", "rain_mm (0,130), nfr_mm (0,118), rain_roll3 (0,061), need_irrigation (0,049), cloud_roll7 (0,048)."),
        ],
        top=5.2,
        font_size=14,
    )

    # ---------- SLIDE 7: OPERATIONALIZATION & POWER BI ----------
    s7 = new_slide(
        prs,
        "7. Operationalization & Power BI Integration (Live Demo)",
        "Dashboard 3 halaman (kbfinpro.pbix) dengan 6 measure DAX, 4 slicer single-select, dan Drill-Through",
        notes=(
            "Seluruh hasil simulasi ROI dan prediksi ML dimuat ke PostgreSQL dan terhubung ke Power BI Desktop "
            "(kbfinpro.pbix). Halaman 1 untuk simulasi BEP eksekutif, Halaman 2 bisa di-drill-through dari kabupaten "
            "terpilih, dan Halaman 3 menampilkan Confusion Matrix serta kurva kalibrasi probabilitas yang menempel "
            "rapat dengan kejadian aktual. (Di tahap ini lakukan live demo 2-3 menit di Power BI Desktop.)"
        ),
    )
    s7.shapes.add_picture("docs/screenshots/pbi_page1_executive_roi.png", Inches(0.6), Inches(1.4), width=Inches(6.0))
    s7.shapes.add_picture("docs/screenshots/pbi_page3_ml_prediction.png", Inches(6.75), Inches(1.4), width=Inches(6.0))
    add_bullets(
        s7,
        [
            ("Alur Demo Live: ", "Toggle Biosolar -> Dexlite & Individu -> Kelompok Tani (Page 1) -> Klik kanan Gunungkidul -> Drill through ke Climate & Demand (Page 2) -> Cek Recall 97,3% & kalibrasi (Page 3)."),
        ],
        top=5.6,
        font_size=14,
    )

    # ---------- SLIDE 8: ETHICS, GOVERNANCE & POLICY ----------
    s8 = new_slide(
        prs,
        "8. Ethics, Governance & Limitations",
        "Kepatuhan UU PDP No. 27/2022, keterbatasan metodologi secara transparan, dan Model Card",
        notes=(
            "Dari sisi tata kelola dan etika: data cuaca bersumber publik tanpa data pribadi petani (PII), "
            "sesuai prinsip minimalisasi data UU PDP No. 27/2022. Jika kelak terhubung ke data Gapoktan, identitas "
            "wajib dipseudonimisasi. Kami juga mencatat jujur 4 batasan: data cuaca berupa reanalisis bukan sensor "
            "stasiun fisik, label irigasi sintetis dari rumus FAO/KP-01, kurva debit diekstrapolasi dari 1 studi Gowa, "
            "dan biaya ganti motor pompa tahun ke-5-7 belum masuk arus kas."
        ),
    )
    add_bullets(
        s8,
        [
            ("Kepatuhan UU PDP No. 27/2022: ", "Data iklim publik tanpa PII (minimalisasi data); pseudonimisasi wajib saat integrasi data petani mitra."),
            ("Model Card (Logistic Regression v1.0): ", "Intended use: sinyal siaga irigasi H+1 padi sawah. Out-of-scope: otomasi saklar tanpa manusia / komoditas non-padi."),
            ("Fairness: ", "Dilatih pada data agroklimat wilayah tanpa variabel status kepemilikan lahan (menjamin keadilan rekomendasi)."),
            ("4 Batasan Transparan: ", "(1) Data reanalisis bukan AWS BMKG; (2) Label NFR & kalender MT1-MT2 teoritis; (3) Ekstrapolasi kurva Gowa + cut-in 30 W/m2; (4) Biaya ganti motor pompa tahun ke-5-7 belum dimodelkan."),
        ],
        top=1.45,
        font_size=15,
    )

    # ---------- SLIDE 9: RECOMMENDATION & ROI ----------
    s9 = new_slide(
        prs,
        "9. Recommendation & ROI (CAPEX Riil Marketplace)",
        "Dua tuas penentu kelayakan: Skala Kelompok Tani (5 kWp / 5 ha) dan Sensitivitas Subsidi BBM",
        notes=(
            "Ini kesimpulan bisnis terpenting kami memakai harga riil Tokopedia/Shopee (+15% pasang): "
            "1 kWp Rp 8,5-15,5 juta, 3 kWp Rp 20-38 juta, dan 5 kWp Rp 35-65 juta. "
            "Pertama, hindari jebakan over-sizing: untuk petani individu 1 ha, 1 kWp paling efisien (1,46-2,73 tahun "
            "pada Dexlite), bukan 5 kWp. Kedua, pada skema Kelompok Tani 5 kWp untuk 5 ha, 4 kabupaten (Gunungkidul, "
            "Klaten, Bantul, Wonogiri) sudah tembus BEP di bawah 5 tahun bahkan dengan Biosolar subsidi, dan seluruh "
            "8 kabupaten balik modal dalam 1,20 sampai 2,77 tahun jika subsidi dicabut."
        ),
    )
    add_simple_table(
        s9,
        ["Skenario (0,04 L/m3)", "CAPEX", "BEP Biosolar (Rp 6.800)", "BEP Dexlite (Rp 23.700)", "Keputusan"],
        [
            ["Individu 1 ha — 1 kWp (Gunungkidul)", "Rp 8,5-15,5 jt", "5,48 - 10,99 thn", "1,46 - 2,73 thn", "Optimal untuk 1 ha"],
            ["Individu 1 ha — 5 kWp (Gunungkidul)", "Rp 35-65 jt", "12,3+ thn", "3,06 - 5,99 thn", "Over-sizing (Hindari)"],
            ["Kelompok 5 ha — 5 kWp (Gunungkidul)", "Rp 35-65 jt", "4,43 - 8,90 thn", "1,20 - 2,27 thn", "Prioritas #1"],
            ["Kelompok 5 ha — 5 kWp (Klaten)", "Rp 35-65 jt", "4,54 - 9,15 thn", "1,22 - 2,32 thn", "Prioritas #2"],
            ["Kelompok 5 ha — 5 kWp (8 Kab. Range)", "Rp 35-65 jt", "4,43 - 11,20 thn", "1,20 - 2,77 thn", "Semua Layak (Dexlite)"],
        ],
        left=0.6,
        top=1.45,
        width=12.1,
        height=3.1,
        font_size=12.5,
    )
    add_bullets(
        s9,
        [
            ("Rekomendasi 1 (Dinas): ", "Prioritaskan hibah PATS ke Gunungkidul & Klaten dalam skema Kelompok Tani 5 kWp (5 ha) sebelum batas subsidi Des 2026."),
            ("Rekomendasi 2 (Gapoktan): ", "Sisihkan 15% penghematan solar tahunan sebagai dana cadangan (sinking fund) ganti motor pompa di tahun ke-5-7."),
            ("Rekomendasi 3 (Teknis): ", "Gunakan prediksi H+1 (Recall 97,3%) untuk jadwal pompa & validasi kalender tanam ke KATAM Kementan."),
        ],
        top=4.85,
        font_size=14,
    )

    # ---------- SLIDE 10: CLOSING / Q&A ----------
    s10 = prs.slides.add_slide(prs.slide_layouts[6])
    bg10 = s10.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg10.fill.solid()
    bg10.fill.fore_color.rgb = NAVY
    bg10.line.fill.background()

    tb10 = s10.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(11.3), Inches(3.2))
    tf10 = tb10.text_frame
    tf10.word_wrap = True
    p0 = tf10.paragraphs[0]
    p0.alignment = PP_ALIGN.CENTER
    r0 = p0.add_run()
    r0.text = "Terima Kasih — Sesi Tanya Jawab (Q&A)"
    r0.font.name = "Calibri"
    r0.font.size = Pt(38)
    r0.font.bold = True
    r0.font.color.rgb = WHITE

    p1 = tf10.add_paragraph()
    p1.alignment = PP_ALIGN.CENTER
    p1.space_before = Pt(20)
    r1 = p1.add_run()
    r1.text = (
        "Repositori Kode, Data Olahan, Bukti Harga & Dashboard Power BI:\n"
        "https://github.com/glacerous/kb_finpro\n\n"
        "Atribusi Data: Open-Meteo.com (CC BY 4.0) | NASA POWER Project | FAO-56 | BPS DIY & Jateng"
    )
    r1.font.name = "Calibri"
    r1.font.size = Pt(15)
    r1.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)
    s10.notes_slide.notes_text_frame.text = (
        "Sekian presentasi dari kelompok kami. Seluruh kode Python, skema SQL, bukti harga Tokopedia, "
        "dan file dashboard Power BI tersedia di repositori GitHub kami. Silakan jika ada pertanyaan."
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT_PATH)
    print(f"Generated {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build_deck()
