"""Generate formatted, factually-verified final report (.docx) for Kecerdasan Bisnis.

Outputs: docs/Laporan_Tugas_Besar_KB.docx
"""

from pathlib import Path
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Inches, Pt, RGBColor

OUT_PATH = Path("docs/Laporan_Tugas_Besar_KB.docx")
BLACK = RGBColor(0x00, 0x00, 0x00)


def set_cell_margins(cell, top=75, bottom=75, left=100, right=100) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for side, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{side}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def set_table_borders(table) -> None:
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'<w:left w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="000000"/>'
        f"</w:tblBorders>"
    )
    tblPr.append(borders)


def clean_text(text: str) -> str:
    return (
        text.replace("\u2014", " - ")
        .replace("\u2013", "-")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )


def add_p(doc: Document, text: str, bold_prefix: str | None = None, space_after: float = 6.0) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    if bold_prefix:
        r0 = p.add_run(clean_text(bold_prefix))
        r0.bold = True
        r0.font.name = "Times New Roman"
        r0.font.size = Pt(11.5)
        r0.font.color.rgb = BLACK
    r = p.add_run(clean_text(text))
    r.font.name = "Times New Roman"
    r.font.size = Pt(11.5)
    r.font.color.rgb = BLACK


def add_bullet(doc: Document, text: str, bold_prefix: str | None = None) -> None:
    p = doc.add_paragraph(style="List Bullet")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    if bold_prefix:
        r0 = p.add_run(clean_text(bold_prefix))
        r0.bold = True
        r0.font.name = "Times New Roman"
        r0.font.size = Pt(11.5)
        r0.font.color.rgb = BLACK
    r = p.add_run(clean_text(text))
    r.font.name = "Times New Roman"
    r.font.size = Pt(11.5)
    r.font.color.rgb = BLACK


def add_chapter(doc: Document, title: str, page_break: bool = True) -> None:
    if page_break:
        doc.add_page_break()
    h = doc.add_heading(clean_text(title), level=1)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h.paragraph_format.space_before = Pt(4)
    h.paragraph_format.space_after = Pt(12)
    for run in h.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = BLACK


def add_sub(doc: Document, title: str) -> None:
    h = doc.add_heading(clean_text(title), level=2)
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(5)
    h.paragraph_format.keep_with_next = True
    for run in h.runs:
        run.font.name = "Times New Roman"
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = BLACK


def add_table(doc: Document, headers: list[str], rows: list[list[str]], col_widths: list[float] | None = None) -> None:
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tbl)

    trPr = tbl.rows[0]._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))

    for j, h_text in enumerate(headers):
        cell = tbl.rows[0].cells[j]
        set_cell_margins(cell, top=80, bottom=80, left=85, right=85)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(clean_text(h_text))
        r.bold = True
        r.font.name = "Times New Roman"
        r.font.size = Pt(10)
        r.font.color.rgb = BLACK

    for i, row_vals in enumerate(rows):
        row = tbl.rows[i + 1]
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        for j, val in enumerate(row_vals):
            cell = row.cells[j]
            set_cell_margins(cell, top=60, bottom=60, left=85, right=85)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            r = p.add_run(clean_text(val))
            r.font.name = "Times New Roman"
            r.font.size = Pt(9.5)
            r.font.color.rgb = BLACK

    if col_widths:
        for row in tbl.rows:
            for j, w in enumerate(col_widths):
                row.cells[j].width = Cm(w)

    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after = Pt(4)


def add_code_box(doc: Document, code: str) -> None:
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.rows[0].cells[0]
    set_cell_margins(cell, top=90, bottom=90, left=130, right=130)
    set_table_borders(tbl)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(clean_text(code.strip()))
    r.font.name = "Consolas"
    r.font.size = Pt(9)
    r.font.color.rgb = BLACK
    sp = doc.add_paragraph()
    sp.paragraph_format.space_after = Pt(4)


def add_figure(doc: Document, img_path: str, caption: str, width_cm: float = 14.2) -> None:
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(4)
    p_img.paragraph_format.space_after = Pt(3)
    p_img.paragraph_format.keep_with_next = True
    p_img.add_run().add_picture(img_path, width=Cm(width_cm))

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(0)
    p_cap.paragraph_format.space_after = Pt(8)
    r = p_cap.add_run(clean_text(caption))
    r.italic = True
    r.font.name = "Times New Roman"
    r.font.size = Pt(9.5)
    r.font.color.rgb = BLACK


def build_doc() -> None:
    doc = Document()

    # Page setup: A4, margins 3cm top/bottom, 3.5cm left, 2.5cm right (printable width = 15cm)
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.8)
    sec.bottom_margin = Cm(2.8)
    sec.left_margin = Cm(3.2)
    sec.right_margin = Cm(2.6)

    # Normal style defaults
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11.5)
    normal.font.color.rgb = BLACK

    # ================= COVER PAGE =================
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(28)
    p.paragraph_format.space_after = Pt(14)
    r = p.add_run("TUGAS BESAR KECERDASAN BISNIS")
    r.bold = True
    r.font.size = Pt(16)
    r.font.color.rgb = BLACK

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.space_after = Pt(20)
    r = p.add_run(
        "PREDIKSI KETERSEDIAAN ENERGI SURYA DAN KEBUTUHAN IRIGASI HARIAN\n"
        "SERTA KELAYAKAN RETURN ON INVESTMENT (ROI) POMPA AIR TENAGA SURYA\n"
        "BAGI PETANI PADI DI DAERAH ISTIMEWA YOGYAKARTA DAN SEKITARNYA\n"
        "(8 KABUPATEN)"
    )
    r.bold = True
    r.font.size = Pt(13.5)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(28)
    r = p.add_run("KELAS SI-C\nDisusun Oleh:")
    r.bold = True
    r.font.size = Pt(12)

    members = [
        ("1.", "Muhammad Barkah Ramadhan", "124240004"),
        ("2.", "Azzaky Raihan Ramdhani", "124240018"),
        ("3.", "Syahrul Alfiansyah", "124240005"),
        ("4.", "Muhammad Ariel Saputra", "124240010"),
        ("5.", "Ahmad Ridwan Alhadi", "124240027"),
    ]
    mtbl = doc.add_table(rows=len(members), cols=3)
    mtbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, (no, name, nim) in enumerate(members):
        for j, val in enumerate((no, name, nim)):
            c = mtbl.rows[i].cells[j]
            set_cell_margins(c, top=40, bottom=40, left=80, right=80)
            cp = c.paragraphs[0]
            cp.alignment = WD_ALIGN_PARAGRAPH.RIGHT if j == 2 else WD_ALIGN_PARAGRAPH.LEFT
            cr = cp.add_run(val)
            cr.font.name = "Times New Roman"
            cr.font.size = Pt(11.5)
    for row in mtbl.rows:
        row.cells[0].width = Cm(1.0)
        row.cells[1].width = Cm(7.5)
        row.cells[2].width = Cm(3.0)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(110)
    p.paragraph_format.line_spacing = 1.35
    r = p.add_run(
        "PROGRAM STUDI SISTEM INFORMASI\n"
        "JURUSAN TEKNIK INFORMATIKA\n"
        "FAKULTAS TEKNIK INDUSTRI\n"
        'UNIVERSITAS PEMBANGUNAN NASIONAL "VETERAN" YOGYAKARTA\n'
        "2026"
    )
    r.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = BLACK

    # ================= DAFTAR ISI =================
    add_chapter(doc, "DAFTAR ISI", page_break=True)
    toc_items = [
        ("BAB I: PENDAHULUAN", True),
        ("    1.1 Latar Belakang", False),
        ("    1.2 Rumusan Masalah & Business Questions", False),
        ("    1.3 Tujuan Proyek", False),
        ("    1.4 Manfaat Proyek", False),
        ("    1.5 Batasan Proyek", False),
        ("BAB II: METODOLOGI PENELITIAN", True),
        ("    2.1 Pendekatan Penelitian (Design Science Research & Kimball Lifecycle)", False),
        ("    2.2 Karakteristik & Sumber Data Multi-Sumber", False),
        ("    2.3 Arsitektur Sistem & Desain Data Warehouse Skema Bintang", False),
        ("    2.4 Formulasi Neraca Air Padi (NFR) & Model Pompa Surya DC Direct-Driven", False),
        ("    2.5 Teknik Analisis Statistik Inferensial & Machine Learning H+1 Anti-Leakage", False),
        ("    2.6 Kerangka Evaluasi Tekno-Ekonomi & Desain Visualisasi Power BI", False),
        ("BAB III: PEMBAHASAN", True),
        ("    3.1 Profil Agroklimat & Wilayah Studi (8 Kabupaten DIY-Jateng)", False),
        ("    3.2 Hasil Implementasi ETL & Validasi Silang Data Warehouse", False),
        ("    3.3 Hasil Analisis Statistik Eksploratif & Inferensial", False),
        ("    3.4 Evaluasi Kinerja Model Machine Learning H+1 & Optimasi Threshold", False),
        ("    3.5 Implementasi Dashboard Interaktif Power BI (kbfinpro.pbix)", False),
        ("    3.6 Simulasi Tekno-Ekonomi ROI/BEP & Sensitivitas Lahan Serta Subsidi BBM", False),
        ("    3.7 Aspek Etika, Tata Kelola Data (UU PDP No. 27/2022), Batasan, dan Model Card", False),
        ("BAB IV: KESIMPULAN DAN REKOMENDASI", True),
        ("    4.1 Kesimpulan", False),
        ("    4.2 Rekomendasi", False),
        ("DAFTAR PUSTAKA", True),
    ]
    for label, is_bold in toc_items:
        tp = doc.add_paragraph()
        tp.paragraph_format.space_before = Pt(3 if is_bold else 0)
        tp.paragraph_format.space_after = Pt(2)
        tr = tp.add_run(clean_text(label))
        tr.bold = is_bold
        tr.font.name = "Times New Roman"
        tr.font.size = Pt(11)
        tr.font.color.rgb = BLACK

    # ================= BAB I =================
    add_chapter(doc, "BAB I: PENDAHULUAN")

    add_sub(doc, "1.1 Latar Belakang")
    add_p(
        doc,
        "Sektor pertanian merupakan pilar ketahanan pangan dan fondasi perekonomian utama di Daerah Istimewa "
        "Yogyakarta (DIY) serta wilayah Jawa Tengah bagian selatan. Namun, stabilitas produktivitas komoditas "
        "padi sawah (Oryza sativa) menghadapi tantangan struktural yang semakin berat. Berdasarkan laporan "
        "Badan Pusat Statistik (BPS) tahun 2024, produksi padi di DIY mengalami penurunan tajam sebesar "
        "14,95%, dengan kontraksi terbesar terkonsentrasi di Kabupaten Gunungkidul, Bantul, dan Sleman. "
        "Faktor pemicu utamanya adalah anomali iklim, kekeringan berkepanjangan pada musim kemarau, dan "
        "keterbatasan infrastruktur irigasi teknis pada sawah tadah hujan.",
    )
    add_p(
        doc,
        "Untuk menjaga pasokan air selama fase defisit, petani sangat bergantung pada pompa irigasi mekanis "
        "berbahan bakar diesel. Ketergantungan ini menimbulkan kerentanan biaya yang besar. Harga Biosolar "
        "bersubsidi sebesar Rp 6.800 per liter hanya dipertahankan hingga akhir Desember 2026, sedangkan "
        "harga bahan bakar nonsubsidi jenis Dexlite mencapai Rp 23.700 per liter (hampir 3,5 kali lipat). "
        "Jika subsidi bahan bakar dibatasi pasca-2026, lonjakan biaya operasional diesel akan langsung "
        "menggerus margin petani kecil.",
    )
    add_p(
        doc,
        "Pompa Air Tenaga Surya (PATS) sistem direct-driven DC tanpa baterai hadir sebagai alternatif energi "
        "hijau yang mengalirkan air pada siang hari tanpa biaya bahan bakar harian. Namun, adopsi teknologi "
        "ini terhambat oleh modal awal (Capital Expenditure / CAPEX) yang besar dan hasil studi sebelumnya "
        "yang beragam: satu studi mencatat penghematan biaya operasional bulanan pompa surya Rp 430.271 "
        "dibandingkan diesel Rp 1.403.059 (UNU Blitar), sementara studi lain menemukan titik impas "
        "(Break-Even Point / BEP) baru tercapai pada tahun ke-20 (Telkom University). Perbedaan ini "
        "menunjukkan bahwa kelayakan PATS sangat bergantung pada mikroklimat radiasi lokal, kebutuhan air "
        "musiman, kapasitas pompa, dan skala luas lahan.",
    )
    add_p(
        doc,
        "Oleh karena itu, diperlukan sistem Business Intelligence (BI) terpadu yang menggabungkan Data "
        "Warehouse historis 15 tahun (2011–2025), pengujian statistik, pemodelan prediktif Machine Learning "
        "kebutuhan irigasi harian (H+1), serta simulasi tekno-ekonomi multi-skenario agar petani, Kelompok "
        "Tani (Gapoktan), dan pemerintah daerah memiliki dasar keputusan investasi yang terukur.",
    )

    add_sub(doc, "1.2 Rumusan Masalah & Business Questions")
    add_bullet(
        doc,
        "Di kabupaten mana dan pada kapasitas pompa berapa (1, 3, atau 5 kWp) investasi PATS mencapai BEP "
        "paling cepat dibanding pompa diesel, serta bagaimana perbandingannya antara petani individu (1 ha) "
        "dan skema komunal Kelompok Tani (1 ha/kWp)?",
        "Kelayakan Investasi & Skala Ekonomi (ROI/BEP): ",
    )
    add_bullet(
        doc,
        "Apakah kebutuhan air irigasi harian (Net Field Requirement / NFR) dan radiasi matahari berbeda "
        "signifikan antar 8 kabupaten serta antara musim hujan dan kemarau? Apakah terdapat sinergi alami "
        "antara puncak radiasi dan puncak defisit air sawah?",
        "Disparitas Spasial & Musiman (Statistik): ",
    )
    add_bullet(
        doc,
        "Seberapa akurat kebutuhan irigasi besok (H+1) dapat diprediksi secara andal, dan bagaimana penalaan "
        "ambang batas probabilitas berbasis biaya (FN:FP = 3:1) menekan risiko gagal menyiram (False Negative)?",
        "Operasional Harian & Mitigasi Risiko (ML H+1): ",
    )
    add_bullet(
        doc,
        "Bagaimana dampak peralihan harga dari Biosolar subsidi (Rp 6.800/L) ke Dexlite (Rp 23.700/L) serta "
        "variasi efisiensi diesel (0,04 vs 0,06 L/m³) terhadap percepatan BEP di tiap wilayah?",
        "Sensitivitas Kebijakan BBM & Efisiensi Diesel: ",
    )

    add_sub(doc, "1.3 Tujuan Proyek")
    add_bullet(doc, "Membangun Data Warehouse Skema Bintang Kimball di PostgreSQL yang memuat 1.051.968 baris data cuaca per jam (Open-Meteo) dan 43.832 baris validasi harian (NASA POWER) periode 2011–2025.")
    add_bullet(doc, "Melakukan uji statistik inferensial (One-Way ANOVA, Kruskal-Wallis, Welch t-test, Mann-Whitney U) untuk membuktikan perbedaan wilayah, musim, dan sinergi agroklimat.")
    add_bullet(doc, "Melatih model klasifikasi ML H+1 dengan pemisahan temporal ketat anti-leakage serta optimasi cost-sensitive threshold (FN:FP = 3:1) untuk mencapai Recall di atas 97%.")
    add_bullet(doc, "Menjalankan simulasi tekno-ekonomi 192 kombinasi parameter berbasis CAPEX riil marketplace Indonesia per November 2026 dan menyajikannya dalam dashboard Power BI 3 halaman (kbfinpro.pbix).")

    add_sub(doc, "1.4 Manfaat Proyek")
    add_bullet(doc, "Menghindarkan petani dari jebakan over-sizing kapasitas pompa, memberi hitungan BEP berbasis data lokal, dan menyediakan sinyal prediksi irigasi harian (H+1).", "Bagi Petani & Gapoktan: ")
    add_bullet(doc, "Menyediakan dasar prioritas zonasi bantuan hibah PATS (Gunungkidul dan Klaten) serta mengarahkan bantuan ke skema Kelompok Tani 5 kWp yang jauh lebih efisien.", "Bagi Pemerintah Daerah (Dinas Pertanian & ESDM): ")
    add_bullet(doc, "Menyajikan implementasi utuh pipeline Kecerdasan Bisnis mulai dari ETL idempotent, pemodelan Kimball, kalibrasi fisik pompa, cost-sensitive ML, hingga visualisasi eksekutif.", "Bagi Akademisi & Praktisi SI: ")

    add_sub(doc, "1.5 Batasan Proyek")
    add_bullet(doc, "Dibatasi pada 8 kabupaten (Kulon Progo, Bantul, Gunungkidul, Sleman, Purworejo, Kab. Magelang, Klaten, Wonogiri) periode 2011–2025.", "Cakupan Wilayah & Waktu: ")
    add_bullet(doc, "Data cuaca bersumber dari model reanalisis Open-Meteo Archive API dan NASA POWER, bukan sensor stasiun cuaca fisik BMKG di setiap petak sawah.", "Sumber Data Iklim: ")
    add_bullet(doc, "Fokus pada padi sawah dengan kalender tanam asumsi MT1 (Nov–Feb), MT2 (Mar–Jun), dan Bera (Jul–Okt, Kc = 0); regulasi PLTS atap on-grid (Permen ESDM 2/2024) tidak digunakan karena PATS sawah bersifat off-grid.", "Komoditas & Regulasi: ")
    add_bullet(doc, "Sistem pompa mengacu pada tipe direct-driven DC tanpa baterai (1 kWp acuan studi Gowa; 3 & 5 kWp diskalakan proporsional). CAPEX bersumber dari harga komponen marketplace November 2026 (+15% instalasi), OPEX 2%/tahun, dan belum memasukkan biaya penggantian motor pompa di tahun ke-5–7.", "Sistem Pompa & Arus Kas: ")

    # ================= BAB II =================
    add_chapter(doc, "BAB II: METODOLOGI PENELITIAN")

    add_sub(doc, "2.1 Pendekatan Penelitian (Design Science Research & Kimball Lifecycle)")
    add_p(
        doc,
        "Proyek ini memadukan Design Science Research (DSR) untuk menghasilkan artifak sistem analitik yang "
        "dapat dieksekusi dengan kerangka kerja Kimball Dimensional Modeling untuk merancang Data Warehouse "
        "berorientasi keputusan bisnis. Alur pengerjaan terdiri dari 6 tahap: (1) Ekstraksi & validasi API "
        "(etl_fetch.py), (2) Rekayasa Data Warehouse PostgreSQL idempotent (etl_load_pg.py & sql/schema.sql), "
        "(3) Uji statistik inferensial, (4) Pemodelan ML H+1 anti-leakage & threshold tuning "
        "(stage4_stats_ml.py), (5) Simulasi ROI/BEP 192 kombinasi (stage5_roi_sim.py), dan (6) Visualisasi "
        "Power BI Desktop (kbfinpro.pbix) serta dokumentasi etika dan Model Card.",
    )

    add_sub(doc, "2.2 Karakteristik & Sumber Data Multi-Sumber")
    add_table(
        doc,
        ["No", "Sumber Data", "Parameter Kunci", "Periode / Resolusi", "Volume", "Peran"],
        [
            ["1", "Open-Meteo Archive API", "Radiasi (W/m²), suhu (°C), RH (%), hujan (mm), awan (%), angin 10m (km/h), ET0 (mm)", "2011–2025, Per Jam (Asia/Jakarta)", "1.051.968 baris", "Sumber primer (0 null)"],
            ["2", "NASA POWER API (AG)", "ALLSKY_SFC_SW_DWN (MJ/m²/hr), T2M, RH2M, PRECTOTCORR, WS2M (m/s)", "2011–2025, Harian", "43.832 baris", "Validasi silang (0 null)"],
            ["3", "Studi Lapangan Gowa", "Panel 900 Wp, pompa DC 750 W; debit 15,6 / 53,3 / 84,1 / 100 L/m", "Eksperimen lapangan", "Kurva acuan", "Kalibrasi debit pompa"],
            ["4", "FAO-56 & KP-01 PUPR", "Kc padi (1,05; 1,20; 0,90), P=2 mm/hr, WLR=1 mm/hr, olah lahan 250 mm", "Standar irigasi", "Parameter rumus", "Neraca air padi (NFR)"],
            ["5", "BPS DIY & Jateng", "Luas panen & produksi padi 2024 (-14,95% di DIY)", "Tahunan 2024", "Ringkasan kab.", "Urgensi latar belakang"],
            ["6", "Marketplace (Tokopedia)", "Panel Mono 550Wp & Pompa Submersible DC + MPPT (750W–3700W)", "November 2026", "Bukti screenshot", "CAPEX riil Low & High"],
            ["7", "Harga BBM Pertamina", "Biosolar subsidi Rp 6.800/L & Dexlite Rp 23.700/L", "Berlaku 2026", "2 skenario", "Simulasi penghematan"],
        ],
        col_widths=[0.9, 2.7, 4.3, 2.5, 2.2, 2.6],
    )

    add_sub(doc, "2.3 Arsitektur Sistem & Desain Data Warehouse Skema Bintang")
    add_p(
        doc,
        "Data Warehouse diimplementasikan pada PostgreSQL 18 (database kb_solar_irrigation) mengikuti Skema "
        "Bintang Kimball dengan relasi one-to-many (1 -> *) satu arah dari 3 tabel dimensi ke 5 tabel fakta. "
        "Pemuatan data menggunakan mekanisme PostgreSQL COPY ke tabel staging temporer diikuti INSERT ... "
        "ON CONFLICT DO UPDATE agar seluruh pipeline bersifat idempotent (aman dijalankan ulang tanpa duplikasi).",
    )
    add_table(
        doc,
        ["Nama Tabel", "Tipe", "Baris", "Kunci Utama & Atribut Inti"],
        [
            ["dim_region", "Dimensi", "8", "region_id (PK), slug, kabupaten, provinsi, latitude, longitude"],
            ["dim_date", "Dimensi", "5.479", "date_id (PK: YYYYMMDD), full_date, year, month, climate_season, planting_season, kc_paddy"],
            ["dim_scenario", "Dimensi", "3", "scenario_id (PK), capacity_kwp (1/3/5), max_flow_lpm, capex_low_idr, capex_high_idr"],
            ["fact_weather_hourly", "Fakta", "1.051.968", "(region_id, ts) PK, date_id FK, 7 variabel cuaca per jam Open-Meteo"],
            ["fact_nasa_daily", "Fakta", "43.832", "(region_id, date_id) PK, 5 variabel cuaca harian NASA POWER"],
            ["fact_irrigation_daily", "Fakta", "43.832", "(region_id, date_id) PK, ET0, hujan, radiasi MJ/m², solar_water_1kwp_m3, NFR, need_irrigation"],
            ["fact_ml_predictions", "Fakta", "5.808", "(region_id, date_id) PK, next_date, target_next, prob_lr, pred_lr_fn3, prob_rf, pred_rf_fn3"],
            ["fact_roi_simulation", "Fakta", "192", "(region_id, scenario_id, land_mode, fuel_scenario, diesel_l_per_m3) PK, BEP, ROI 10 thn"],
        ],
        col_widths=[3.4, 1.8, 2.0, 8.0],
    )
    add_figure(
        doc,
        "docs/screenshots/pbi_model_view_star_schema.png",
        "Gambar 2.1 Implementasi Model Dimensional Skema Bintang Kimball pada Model View Power BI Desktop.",
        width_cm=14.4,
    )

    add_sub(doc, "2.4 Formulasi Neraca Air Padi (NFR) & Model Pompa Surya DC Direct-Driven")
    add_p(
        doc,
        "Berbeda dengan palawija yang hanya memperhitungkan evapotranspirasi tanaman (ETc), padi sawah "
        "memerlukan lapisan air genangan sehingga kehilangan air akibat perkolasi (P) dan penggantian lapisan "
        "air (WLR) wajib diperhitungkan sesuai standar FAO-56 dan KP-01:",
    )
    add_code_box(doc, "NFR (mm/hari) = max( 0,  Kc * ET0 + P + WLR - 0.8 * Rain )")
    add_bullet(doc, "Kc awal = 1,05 (Nov, Mar); Kc tengah = 1,20 (Des, Jan, Apr, Mei); Kc akhir = 0,90 (Feb, Jun); Bera = 0,00 (Jul–Okt).", "Koefisien Tanaman Padi (Kc): ")
    add_bullet(doc, "Perkolasi P = 2,0 mm/hari, WLR = 1,0 mm/hari, hujan efektif = 0,8 × Rain, dan penyiapan lahan 250 mm/musim (16,67 mm/hari pada 15 hari awal MT1 & MT2, dihitung penuh di simulasi ROI).", "Parameter Agronomi: ")
    add_bullet(doc, "Bernilai 1 jika hari berada pada MT1/MT2 dan NFR > 1,0 mm/hari; bernilai 0 selainnya.", "Label need_irrigation: ")
    add_p(
        doc,
        "Untuk debit pompa surya per jam, digunakan interpolasi linier bertahap (piecewise linear interpolation) "
        "berdasarkan titik terukur studi Gowa dengan cut-in 30 W/m² agar tidak menghasilkan debit fiktif di malam hari:",
    )
    add_table(
        doc,
        ["Radiasi Matahari (W/m²)", "Debit 1 kWp (L/menit)", "Output 1 kWp (m³/jam)", "Keterangan"],
        [
            ["0 s.d. 30", "0,0", "0,000", "Malam / fajar (asumsi cut-in threshold)"],
            ["51", "15,6", "0,936", "Mendung sore (terukur di Gowa)"],
            ["276", "53,3", "3,198", "Berawan sedang (terukur di Gowa)"],
            ["726", "84,1", "5,046", "Cerah berawan (terukur di Gowa)"],
            [">= 1.000", "100,0", "6,000", "Batas atas spesifikasi pompa (6 m³/jam)"],
        ],
        col_widths=[3.6, 3.2, 3.2, 5.2],
    )

    add_sub(doc, "2.5 Teknik Analisis Statistik Inferensial & Machine Learning H+1 Anti-Leakage")
    add_p(
        doc,
        "Uji hipotesis memakai One-Way ANOVA & Kruskal-Wallis (komparasi 8 kabupaten) serta Welch t-test & "
        "Mann-Whitney U (Kemarau vs Hujan dan MT2 vs MT1). Pada pemodelan ML, target adalah memprediksi "
        "need_irrigation hari esok (H+1) dengan pemisahan temporal ketat: Train 2011–2022 (23.200 baris), "
        "Validasi threshold 2021–2022, dan Test out-of-sample 2023–2025 (5.808 baris). Seluruh fitur lag "
        "(t-1, t-2, t-3, t-7) dan rata-rata bergulir (3 hari dan 7 hari) dihitung terisolasi per kabupaten "
        "(groupby region_id) dengan verifikasi selisih tanggal tepat 1 hari agar bebas kebocoran data.",
    )
    add_p(
        doc,
        "Karena gagal menyiram padi (False Negative / FN) jauh lebih merugikan dibandingkan siaga berlebih "
        "(False Positive / FP), ambang batas probabilitas dituning pada validasi 2021–2022 menggunakan "
        "fungsi biaya Cost = 3 × FN + 1 × FP, menghasilkan threshold optimal t = 0,21 untuk Logistic Regression "
        "dan t = 0,24 untuk Random Forest.",
    )

    add_sub(doc, "2.6 Kerangka Evaluasi Tekno-Ekonomi & Desain Visualisasi Power BI")
    add_p(
        doc,
        "Simulasi tekno-ekonomi (192 kombinasi) menghitung volume air tahunan, cakupan surya (Solar Coverage), "
        "penghematan liter solar (pada efisiensi 0,04 dan 0,06 L/m³), penghematan bersih setelah OPEX 2%/tahun, "
        "titik impas BEP = CAPEX / Penghematan Bersih, dan ROI 10 tahun. Seluruh metrik divisualisasikan pada "
        "Power BI Desktop (kbfinpro.pbix) menggunakan 6 tabel terelasi (tanpa fact_weather_hourly agar hemat RAM) "
        "dengan ukuran DAX berikut pada tabel _Measures:",
    )
    add_code_box(
        doc,
        "Avg BEP Low (Yr) = AVERAGE('public fact_roi_simulation'[bep_low_years])\n"
        "Avg BEP High (Yr) = AVERAGE('public fact_roi_simulation'[bep_high_years])\n"
        "Solar Coverage % = DIVIDE(SUM('public fact_roi_simulation'[annual_solar_m3]),\n"
        "                          SUM('public fact_roi_simulation'[annual_demand_m3]))\n"
        "Annual Net Saving (Low) = SUM('public fact_roi_simulation'[annual_net_saving_low])\n\n"
        "ML Recall (Tuned) =\n"
        "VAR TP = CALCULATE(COUNTROWS('public fact_ml_predictions'),\n"
        "         'public fact_ml_predictions'[target_next] = 1,\n"
        "         'public fact_ml_predictions'[pred_lr_fn3] = 1)\n"
        "VAR Pos = CALCULATE(COUNTROWS('public fact_ml_predictions'),\n"
        "          'public fact_ml_predictions'[target_next] = 1)\n"
        "RETURN DIVIDE(TP, Pos)\n\n"
        "ML Missed Days (FN) = CALCULATE(COUNTROWS('public fact_ml_predictions'),\n"
        "                      'public fact_ml_predictions'[target_next] = 1,\n"
        "                      'public fact_ml_predictions'[pred_lr_fn3] = 0)",
    )

    # ================= BAB III =================
    add_chapter(doc, "BAB III: PEMBAHASAN")

    add_sub(doc, "3.1 Profil Agroklimat & Wilayah Studi (8 Kabupaten DIY–Jateng)")
    add_table(
        doc,
        ["Kabupaten", "Hari Tanam", "Mean NFR (mm/hr)", "% Butuh Irigasi", "Radiasi (MJ/m²/hr)", "Output 1 kWp (m³/hr)", "Hujan (mm/hr)"],
        [
            ["Gunungkidul", "3.634", "3,30", "60,10%", "17,66", "40,06", "8,21"],
            ["Klaten", "3.634", "3,25", "59,33%", "17,61", "39,91", "8,22"],
            ["Wonogiri", "3.634", "3,03", "54,16%", "17,16", "39,30", "9,12"],
            ["Bantul", "3.634", "2,95", "55,01%", "17,58", "39,97", "9,09"],
            ["Kulon Progo", "3.634", "2,64", "51,49%", "17,56", "39,92", "10,00"],
            ["Purworejo", "3.634", "2,60", "52,37%", "17,19", "39,38", "9,99"],
            ["Sleman", "3.634", "2,59", "51,49%", "17,13", "39,29", "10,05"],
            ["Kab. Magelang", "3.634", "2,46", "49,20%", "16,65", "38,64", "10,11"],
        ],
        col_widths=[2.7, 1.8, 2.2, 2.2, 2.2, 2.2, 1.9],
    )
    add_p(
        doc,
        "Gunungkidul dan Klaten membentuk klaster defisit air tertinggi (NFR 3,25–3,30 mm/hari, ~60% hari "
        "tanam butuh irigasi) sekaligus memiliki radiasi matahari tertinggi (>17,6 MJ/m²/hari), sehingga "
        "menjadi kandidat prioritas adopsi PATS. Sebaliknya, Kab. Magelang dan Sleman di lereng pegunungan "
        "memiliki curah hujan tertinggi (>10 mm/hari) dan radiasi terendah.",
    )

    add_sub(doc, "3.2 Hasil Implementasi ETL & Validasi Silang Data Warehouse")
    add_p(
        doc,
        "Pipeline ETL (etl_fetch.py dan etl_load_pg.py) memuat 1.051.968 baris Open-Meteo dan 43.832 baris "
        "NASA POWER ke PostgreSQL dengan 0 missing values. Indeks B-Tree pada kunci komposit (region_id, "
        "date_id) dan ts diterapkan untuk mempercepat kueri agregasi multi-tahun.",
    )
    add_table(
        doc,
        ["Kabupaten", "Null (OM / NASA)", "Radiasi Tahunan OM (MJ/m²/hr)", "Radiasi Tahunan NASA (MJ/m²/hr)", "Pearson r"],
        [
            ["Kulon Progo", "0 / 0", "18,30", "18,32", "0,7530"],
            ["Bantul", "0 / 0", "18,35", "18,32", "0,7505"],
            ["Gunungkidul", "0 / 0", "18,53", "18,32", "0,7373"],
            ["Sleman", "0 / 0", "17,89", "18,32", "0,7559"],
            ["Purworejo", "0 / 0", "17,90", "18,32", "0,7461"],
            ["Kab. Magelang", "0 / 0", "17,46", "18,32", "0,7686"],
            ["Klaten", "0 / 0", "18,55", "18,32", "0,7843"],
            ["Wonogiri", "0 / 0", "18,23", "18,32", "0,7785"],
        ],
        col_widths=[3.0, 2.5, 3.4, 3.6, 2.7],
    )
    add_p(
        doc,
        "Rata-rata radiasi NASA POWER bernilai identik (18,32 MJ/m²/hari) di seluruh 8 kabupaten karena "
        "resolusi grid radiasi satelit NASA POWER relatif kasar (1° × 1° atau ~111 km), sehingga kedelapan "
        "kabupaten di DIY dan Jawa Tengah jatuh pada satu sel grid yang sama. Sebaliknya, Open-Meteo berhasil "
        "menangkap variasi lokal nyata (17,46 s.d. 18,55 MJ/m²/hari) dengan korelasi harian kuat (r = 0,74–0,78), "
        "memvalidasi pilihan Open-Meteo sebagai sumber utama.",
        "Temuan Teknis Kritis: ",
    )

    add_sub(doc, "3.3 Hasil Analisis Statistik Eksploratif & Inferensial")
    add_table(
        doc,
        ["Uji Statistik", "Variabel Diuji", "Statistik", "p-value", "Interpretasi Bisnis"],
        [
            ["One-Way ANOVA", "NFR antar 8 kabupaten", "F = 42,28", "9,14e-60", "Sangat signifikan; Gunungkidul 34% > Magelang"],
            ["Kruskal-Wallis", "NFR antar 8 kabupaten", "H = 282,68", "3,01e-57", "Mengonfirmasi ANOVA secara non-parametrik"],
            ["One-Way ANOVA", "Radiasi antar 8 kab.", "F = 50,14", "1,52e-71", "Potensi insolasi berbeda nyata antar daerah"],
            ["Welch t-test", "NFR Kemarau vs Hujan", "t = 56,39", "< 1e-300", "Kemarau (4,47) hampir 2x Hujan (2,30 mm/hr)"],
            ["Welch t-test", "NFR MT2 vs MT1", "t = 41,82", "< 1e-300", "MT2 (3,56) jauh lebih kering dari MT1 (2,13)"],
            ["Welch t-test", "Radiasi Kemarau vs Hujan", "t = 43,12", "< 1e-300", "Radiasi Kemarau (18,93) > Hujan (17,36 MJ/m²)"],
        ],
        col_widths=[2.7, 3.0, 2.1, 2.0, 5.4],
    )
    add_p(
        doc,
        "Hasil pengujian membuktikan adanya sinergi agroklimat alami: tepat ketika kebutuhan air sawah melonjak "
        "hampir 2 kali lipat di musim kemarau, pasokan radiasi matahari juga mencapai puncaknya.",
    )

    add_sub(doc, "3.4 Evaluasi Kinerja Model Machine Learning H+1 & Optimasi Threshold")
    add_table(
        doc,
        ["Model / Konfigurasi", "Acc", "Prec", "Rec", "F1", "ROC-AUC", "FN", "FP"],
        [
            ["Climatology (baseline)", "0,598", "0,682", "0,546", "0,606", "0,651", "1.497", "839"],
            ["Persistence (baseline)", "0,711", "0,747", "0,742", "0,745", "-", "849", "828"],
            ["Logistic Regression (t=0,50)", "0,731", "0,779", "0,736", "0,757", "0,794", "871", "689"],
            ["Logistic Regression (FN:FP=3:1, t=0,21)", "0,601", "0,590", "0,973", "0,735", "0,794", "88", "2.227"],
            ["Random Forest (t=0,50)", "0,727", "0,774", "0,733", "0,753", "0,790", "880", "704"],
            ["Random Forest (FN:FP=3:1, t=0,24)", "0,610", "0,596", "0,967", "0,738", "0,790", "109", "2.157"],
            ["Random Forest (FN:FP=5:1, t=0,15)", "0,570", "0,569", "1,000", "0,725", "0,790", "0", "2.499"],
        ],
        col_widths=[5.4, 1.3, 1.3, 1.3, 1.3, 1.6, 1.4, 1.6],
    )
    add_p(
        doc,
        "Pada uji out-of-sample 2023–2025 (5.808 baris), Logistic Regression menjadi model terbaik (ROC-AUC "
        "0,794; F1 0,757), mengalahkan kedua baseline dan unggul tipis atas Random Forest (AUC 0,790). "
        "Dengan penalaan threshold t = 0,21 (FN:FP = 3:1), hari gagal irigasi (FN) dipangkas 90% dari 849 "
        "hari (persistence) menjadi hanya 88 hari (Recall 97,33%). Lima fitur terpenting (Random Forest) adalah "
        "rain_mm (0,130), nfr_mm (0,118), rain_roll3 (0,061), need_irrigation (0,049), dan cloud_roll7 (0,048).",
    )

    add_sub(doc, "3.5 Implementasi Dashboard Interaktif Power BI (kbfinpro.pbix)")
    add_p(
        doc,
        "Dashboard 3 halaman dibangun di Power BI Desktop (mode Import): Halaman 1 (Executive ROI) menyediakan "
        "4 slicer single-select, 4 KPI Card, bar chart BEP per kabupaten, dan tabel ringkas; Halaman 2 "
        "(Climate & Demand) mendukung Drill-Through per kabupaten dari Halaman 1 dan menampilkan sinergi "
        "bulanan NFR vs radiasi serta lonjakan hari kering El Niño (2018, 2019, 2023); Halaman 3 (ML H+1 "
        "Prediction) menampilkan KPI Recall 97,33%, FN 88, matriks konfusi 2×2, dan kurva kalibrasi bulanan.",
    )
    add_figure(doc, "docs/screenshots/pbi_page1_executive_roi.png", "Gambar 3.1 Halaman 1 Dashboard Power BI: Executive ROI & Kelayakan Investasi (CAPEX Riil).", width_cm=14.4)
    add_figure(doc, "docs/screenshots/pbi_page2_climate_demand.png", "Gambar 3.2 Halaman 2 Dashboard Power BI: Climate & Demand dengan Fitur Drill-Through Kabupaten.", width_cm=14.4)
    add_figure(doc, "docs/screenshots/pbi_page3_ml_prediction.png", "Gambar 3.3 Halaman 3 Dashboard Power BI: Evaluasi Model ML H+1, Matriks Konfusi, dan Kalibrasi.", width_cm=14.4)

    add_sub(doc, "3.6 Simulasi Tekno-Ekonomi ROI/BEP & Sensitivitas Lahan Serta Subsidi BBM")
    add_p(
        doc,
        "CAPEX ditetapkan dari harga komponen marketplace Indonesia per November 2026 (+15% instalasi): "
        "panel 550Wp Mono Rp 1,75–3,50 juta/lembar dan pompa submersible DC + MPPT 750W (Rp 3,42–6,24 juta), "
        "2200W (Rp 6,5–12 juta), 3700W (Rp 13–22 juta), menghasilkan total CAPEX 1 kWp Rp 8,5–15,5 juta, "
        "3 kWp Rp 20–38 juta, dan 5 kWp Rp 35–65 juta.",
    )
    add_figure(doc, "docs/bukti_harga/tokopedia_panel_550wp_20261120.png", "Gambar 3.4 Bukti Harga Pasar Panel Surya 550Wp Monocrystalline di Tokopedia (20 November 2026).", width_cm=13.5)
    add_figure(doc, "docs/bukti_harga/tokopedia_pompa_dc_750w_mppt_20261120.png", "Gambar 3.5 Bukti Harga Pasar Pompa Submersible DC 750W + Controller MPPT di Tokopedia (20 November 2026).", width_cm=13.5)

    add_table(
        doc,
        ["Kabupaten", "Kapasitas", "Solar Cov.", "BEP Low Biosolar", "BEP High Biosolar", "BEP Low Dexlite", "BEP High Dexlite"],
        [
            ["Gunungkidul", "1 kWp", "48,70%", "5,48 thn", "10,99 thn", "1,46 thn", "2,73 thn"],
            ["Gunungkidul", "5 kWp", "48,70%", "4,43 thn", "8,90 thn", "1,20 thn", "2,27 thn"],
            ["Klaten", "1 kWp", "48,04%", "5,62 thn", "11,30 thn", "1,49 thn", "2,79 thn"],
            ["Klaten", "5 kWp", "48,04%", "4,54 thn", "9,15 thn", "1,22 thn", "2,32 thn"],
            ["Bantul", "5 kWp", "48,39%", "4,80 thn", "9,72 thn", "1,29 thn", "2,45 thn"],
            ["Wonogiri", "5 kWp", "46,55%", "4,93 thn", "9,99 thn", "1,32 thn", "2,51 thn"],
            ["Kulon Progo", "5 kWp", "48,63%", "5,12 thn", "10,43 thn", "1,37 thn", "2,61 thn"],
            ["Purworejo", "5 kWp", "48,56%", "5,18 thn", "10,55 thn", "1,38 thn", "2,63 thn"],
            ["Sleman", "5 kWp", "48,12%", "5,24 thn", "10,70 thn", "1,40 thn", "2,66 thn"],
            ["Kab. Magelang", "5 kWp", "47,63%", "5,47 thn", "11,20 thn", "1,46 thn", "2,77 thn"],
        ],
        col_widths=[2.7, 1.8, 1.9, 2.2, 2.2, 2.2, 2.2],
    )
    add_p(
        doc,
        "Pada lahan petani individu 1 ha di Gunungkidul (Dexlite, 0,04 L/m³), kapasitas 1 kWp memberi BEP "
        "paling cepat (1,46–2,73 tahun), sedangkan 3 kWp (2,03–4,01 tahun) dan 5 kWp (3,06–5,99 tahun) "
        "mengalami jebakan over-sizing karena CAPEX naik >4× lipat sementara penghematan solar hanya naik "
        "2× lipat (253 L -> 512 L/tahun). Sebaliknya, pada skema Kelompok Tani (5 kWp / 5 ha), 4 kabupaten "
        "(Gunungkidul, Klaten, Bantul, Wonogiri) sudah menembus BEP < 5 tahun bahkan dengan Biosolar subsidi "
        "(4,43–4,93 tahun), dan seluruh 8 kabupaten mencapai BEP 1,20–2,77 tahun pada skenario Dexlite.",
        "Jebakan Over-Sizing & Dua Tuas Keputusan: ",
    )

    add_sub(doc, "3.7 Aspek Etika, Tata Kelola Data (UU PDP No. 27/2022), Batasan, dan Model Card")
    add_bullet(doc, "Data cuaca reanalisis bersumber publik tanpa PII (minimalisasi data sesuai UU PDP No. 27/2022). Jika sistem dikembangkan ke tahap lapangan dengan data identitas Gapoktan, wajib diterapkan pseudonimisasi dan enkripsi.", "Tata Kelola & Etika: ")
    add_bullet(doc, "(1) Data cuaca merupakan reanalisis, bukan AWS BMKG lokal; (2) Label irigasi sintetis dari neraca air FAO/KP-01 dengan kalender tanam MT1–MT2 asumsi; (3) Kurva debit diekstrapolasi dari 1 studi (Gowa) dengan cut-in 30 W/m²; (4) Biaya ganti motor pompa tahun ke-5–7 belum dimodelkan.", "Batasan Penelitian: ")
    add_bullet(doc, "Logistic Regression v1.0 (StandardScaler, t = 0,21, FN:FP = 3:1). Intended Use: sinyal pendukung keputusan siaga irigasi harian (H+1) untuk padi sawah. Out-of-Scope: otomasi saklar tanpa pengawasan manusia atau komoditas non-padi. Fairness: dilatih pada data iklim agregat tanpa variabel status kepemilikan lahan.", "Model Card Ringkas: ")

    # ================= BAB IV =================
    add_chapter(doc, "BAB IV: KESIMPULAN DAN REKOMENDASI")

    add_sub(doc, "4.1 Kesimpulan")
    add_bullet(doc, "Data Warehouse Skema Bintang PostgreSQL berhasil memuat 1.051.968 baris Open-Meteo dan 43.832 baris NASA POWER (2011–2025) tanpa nilai kosong. Open-Meteo unggul menangkap variasi radiasi tahunan lokal (17,46 s.d. 18,55 MJ/m²/hari) dibandingkan grid kasar NASA POWER yang seragam (18,32 MJ/m²/hari; Pearson r = 0,74–0,78).")
    add_bullet(doc, "Uji One-Way ANOVA membuktikan perbedaan kebutuhan air antar 8 kabupaten sangat signifikan (F = 42,28, p = 9,14e-60), dan Welch t-test membuktikan sinergi agroklimat alami: saat NFR kemarau melonjak hampir 2× lipat (4,47 vs 2,30 mm/hari), radiasi matahari juga meningkat (18,93 vs 17,36 MJ/m²/hari).")
    add_bullet(doc, "Logistic Regression menjadi model prediksi H+1 terbaik (ROC-AUC 0,794; F1 0,757) mengalahkan Climatology, Persistence, dan Random Forest. Penalaan threshold FN:FP = 3:1 (t = 0,21) memangkas hari gagal irigasi (FN) sebesar 90% (849 -> 88 hari, Recall 97,33%).")
    add_bullet(doc, "Untuk petani individu (1 ha), sistem 1 kWp adalah ukuran paling ekonomis (BEP 1,46–2,73 tahun pada Dexlite). Untuk skala besar, skema Kelompok Tani 5 kWp / 5 ha paling optimal: 4 kabupaten sudah layak (< 5 tahun) bahkan pada Biosolar subsidi (4,43–4,93 tahun), dan seluruh 8 kabupaten sangat layak (1,20–2,77 tahun) jika subsidi dicabut. Prioritas utama: Gunungkidul dan Klaten.")

    add_sub(doc, "4.2 Rekomendasi")
    add_bullet(doc, "Prioritaskan hibah PATS ke Gunungkidul dan Klaten dalam bentuk skema komunal Kelompok Tani 5 kWp (5 ha) sebagai mitigasi menjelang batas jaminan subsidi Biosolar Desember 2026.", "Bagi Dinas Pertanian & ESDM: ")
    add_bullet(doc, "Gunakan sinyal prediksi H+1 pada dashboard untuk penjadwalan pompa serta sisihkan 15% penghematan solar tahunan sebagai dana cadangan (sinking fund) peremajaan motor pompa di tahun ke-5–7.", "Bagi Petani & Gapoktan: ")
    add_bullet(doc, "Verifikasi kalender tanam ke KATAM Kementan, tambahkan validasi sensor kelembapan tanah IoT, dan perluas simulasi ke komoditas hortikultura pada masa Bera (Jul–Okt).", "Pengembangan Lanjutan: ")

    # ================= DAFTAR PUSTAKA =================
    add_chapter(doc, "DAFTAR PUSTAKA")
    refs = [
        "Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998). Crop evapotranspiration: Guidelines for computing crop water requirements (FAO Irrigation and Drainage Paper No. 56). Food and Agriculture Organization of the United Nations. https://www.fao.org/3/x0490E/x0490e00.htm",
        "Badan Pusat Statistik Provinsi D.I. Yogyakarta. (2024). Luas Panen dan Produksi Padi di D.I. Yogyakarta 2024 (Angka Sementara). Diakses 2026 dari https://bantulkab.bps.go.id/en/pressrelease/2024/11/01/1197/luas-panen-dan-produksi-padi--di-yogyakarta-2024--angka-sementara---.html",
        "Badan Pusat Statistik Provinsi Jawa Tengah. (2025). Luas Panen dan Produksi Padi 2024 (Angka Tetap) Provinsi Jawa Tengah. Diakses 2026 dari https://jateng.bps.go.id/id/pressrelease/2025/03/03/1558/luas-panen-dan-produksi-padi-2024--angka-tetap--provinsi-jawa-tengah.html",
        "Direktorat Jenderal Sumber Daya Air Kementerian PUPR. (2013). Standar Perencanaan Irigasi: Kriteria Perencanaan Bagian Jaringan Irigasi (KP-01). Kementerian Pekerjaan Umum dan Perumahan Rakyat Republik Indonesia.",
        "Jurnal Abdi Insani Universitas Mataram. Studi Pemanfaatan Pompa Air Tenaga Surya Direct-Driven DC di Kabupaten Gowa. Diakses 2026 dari https://abdiinsani.unram.ac.id/index.php/jurnal/article/download/800/443/6509",
        "Jurnal Ilmiah Briliant Universitas Nahdlatul Ulama Blitar. Analisis Biaya Operasional Pompa Irigasi Tenaga Surya dibandingkan Pompa Diesel. Diakses 2026 dari https://jurnal.unublitar.ac.id/index.php/briliant/article/download/1022/pdf/3615",
        "Katadata. (2026). Daftar Harga BBM Pertamina, Shell, BP, dan Vivo per 1 November. Diakses November 2026 dari https://katadata.co.id/amp/berita/energi/6ae6aa7b66234/daftar-harga-bbm-pertamina-shell-bp-dan-vivo-per-1-november",
        "Kimball, R., & Ross, M. (2013). The Data Warehouse Toolkit: The Definitive Guide to Dimensional Modeling (3rd ed.). John Wiley & Sons.",
        "NASA Langley Research Center. Prediction of Worldwide Energy Resources (POWER) Project — Agroclimatology Daily API. Diakses November 2026 dari https://power.larc.nasa.gov/",
        "Open-Meteo. Historical Weather API Documentation (licensed under CC BY 4.0). Diakses November 2026 dari https://open-meteo.com/en/docs/historical-weather-api",
        "Otodriver. (2026). Harga Biosolar dan Pertalite Dipertahankan Sampai Akhir Desember 2026. Diakses November 2026 dari https://otodriver.com/berita/2026/harga-biosolar-dan-pertalite-dipertahankan-sampai-akhir-desember-2026-harefhgj026",
        "Republik Indonesia. (2022). Undang-Undang Nomor 27 Tahun 2022 tentang Perlindungan Data Pribadi. Lembaran Negara Republik Indonesia Tahun 2022 Nomor 196.",
        "Telkom University Open Library Publications. Analisis Kelayakan Tekno-Ekonomi Pompa Air Tenaga Surya. Diakses 2026 dari https://openlibrarypublications.telkomuniversity.ac.id/index.php/engineering/article/download/15208/14931/29853",
    ]
    for ref in refs:
        rp = doc.add_paragraph()
        rp.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        rp.paragraph_format.left_indent = Cm(1.0)
        rp.paragraph_format.first_line_indent = Cm(-1.0)
        rp.paragraph_format.line_spacing = 1.2
        rp.paragraph_format.space_after = Pt(5)
        rr = rp.add_run(clean_text(ref))
        rr.font.name = "Times New Roman"
        rr.font.size = Pt(10.5)
        rr.font.color.rgb = BLACK

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT_PATH)
    print(f"Generated {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    build_doc()
