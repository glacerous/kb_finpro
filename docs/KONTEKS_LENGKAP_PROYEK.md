# Konteks Lengkap Proyek Tugas Akhir — Kecerdasan Bisnis (BI & Analytics)

Dokumen ini merangkum **seluruh konteks dari awal sampai selesai**: alasan desain, koreksi metodologi, arsitektur Data Warehouse, seluruh angka hasil statistik/ML/ROI, rumus DAX Power BI, panduan demo, batasan laporan, serta antisipasi pertanyaan dosen.

---

## 1. Identitas & Masalah Bisnis

- **Judul:** Prediksi Ketersediaan Energi Surya dan Kebutuhan Irigasi Harian serta Kelayakan ROI Pompa Air Tenaga Surya bagi Petani Padi di DIY dan Sekitarnya (8 Kabupaten)
- **Tema Utama:** *Finding alternative/green energy sources* (pompa irigasi surya menggantikan pompa diesel). Irisan sekunder: *Reducing hunger and poverty by increasing agriculture production*.
- **Inti Keputusan Bisnis (BI):**
  1. **Investasi (ROI & BEP):** Di kabupaten mana dan kapasitas pompa berapa (`1`, `3`, `5 kWp`) pompa tenaga surya paling cepat balik modal dibanding pompa diesel (Biosolar subsidi vs Dexlite non-subsidi), dan apakah lebih layak untuk petani individu (`1 ha`) atau **kelompok tani (`1 ha/kWp`)**?
  2. **Perbedaan Wilayah & Musim (Statistik):** Apakah kebutuhan air irigasi berbeda signifikan antar 8 kabupaten dan antara musim hujan vs kemarau?
  3. **Operasional Harian (ML):** Bisakah kita memprediksi **besok sawah perlu irigasi atau tidak (`H+1`)**, dengan optimasi *threshold* karena risiko gagal menyiram (*False Negative*) lebih mahal daripada salah siaga (*False Positive*)?

### Cakupan Wilayah (8 Kabupaten, Periode 2011–2025 / 15 Tahun)
| Kabupaten | Provinsi | Latitude | Longitude |
|---|---|---:|---:|
| Kulon Progo (Wates) | DI Yogyakarta | -7.8568 | 110.1604 |
| Bantul | DI Yogyakarta | -7.8881 | 110.3288 |
| Gunungkidul (Wonosari) | DI Yogyakarta | -7.9666 | 110.6025 |
| Sleman | DI Yogyakarta | -7.7160 | 110.3556 |
| Purworejo | Jawa Tengah | -7.7131 | 110.0086 |
| Kab. Magelang (Mungkid) | Jawa Tengah | -7.5994 | 110.2206 |
| Klaten | Jawa Tengah | -7.7058 | 110.6015 |
| Wonogiri | Jawa Tengah | -7.8139 | 110.9234 |

---

## 2. Urgensi & Latar Belakang Data Nyata Indonesia

1. **Produksi padi DIY 2024 turun 14,95%**, dengan penurunan terbesar di Gunungkidul, Bantul, dan Sleman ([BPS DIY/Bantul 2024](https://bantulkab.bps.go.id/en/pressrelease/2024/11/01/1197/luas-panen-dan-produksi-padi--di-yogyakarta-2024--angka-sementara---.html)).
2. **Ketidakpastian biaya solar:** Biosolar subsidi `Rp 6.800/L` hanya dipertahankan sampai akhir Desember 2026, sedangkan harga non-subsidi Dexlite mencapai `Rp 23.700/L` (3,5× lipat) ([Katadata](https://katadata.co.id/amp/berita/energi/6ae6aa7b66234/daftar-harga-bbm-pertamina-shell-bp-dan-vivo-per-1-november), [Otodriver](https://otodriver.com/berita/2026/harga-biosolar-dan-pertalite-dipertahankan-sampai-akhir-desember-2026-harefhgj026)).
3. **Modal awal besar & hasil studi sebelumnya beragam:** Satu studi mencatat penghematan biaya irigasi bulanan pompa surya Rp 430.271 vs diesel Rp 1.403.059 ([UNU Blitar](https://jurnal.unublitar.ac.id/index.php/briliant/article/download/1022/pdf/3615)), namun studi lain menemukan BEP baru tercapai di tahun ke-20 ([Telkom University](https://openlibrarypublications.telkomuniversity.ac.id/index.php/engineering/article/download/15208/14931/29853)). Petani butuh hitungan berbasis data per wilayah sebelum berinvestasi.

---

## 3. Keputusan Desain & Koreksi Metodologi (Kenapa Proyek Dibangun Seperti Ini)

Bagian ini penting agar seluruh anggota tim paham alasan teknis di balik setiap keputusan (sering ditanyakan penguji):

1. **Khusus Padi (`24` skenario inti, bukan 5 tanaman / 120 skenario):**
   - Data produksi non-padi BPS hanya tersedia di tingkat provinsi, bukan kabupaten. Fokus ke padi membuat analisis konsisten dengan judul dan data.
   - 24 skenario inti = `8 kabupaten × 3 kapasitas (1, 3, 5 kWp)`, diperluas menjadi `192` baris di `fact_roi_simulation` dengan variasi mode lahan (`Individu 1 ha` vs `Kelompok Tani 1 ha/kWp`), harga BBM (`Biosolar` vs `Dexlite`), dan efisiensi diesel (`0,04` vs `0,06 L/m³`).
2. **Sistem Acuan: Direct-Driven DC Tanpa Baterai (`1`, `3`, `5 kWp`):**
   - `1 kWp` mengacu studi lapangan Gowa (panel `900 Wp`, pompa submersible DC `750 W`, *direct-driven* tanpa baterai, max flow `6 m³/jam` ≈ `100 L/menit`, max head `56 m`, [Abdi Insani Unram](https://abdiinsani.unram.ac.id/index.php/jurnal/article/download/800/443/6509)).
   - `3 kWp` dan `5 kWp` dimodelkan sebagai skala proporsional *direct-driven* DC tanpa baterai.
   - **Tidak memakai angka proyek Karawang (`Rp 320 juta`)** karena Karawang adalah sistem komunitas dengan baterai, inverter, VFD, motor `7,5 kW`, dan angka `Rp 320 juta` adalah alokasi anggaran program desa, bukan harga paket petani.
3. **Tidak Mengutip Permen ESDM 2/2024:**
   - Permen ESDM 2/2024 mengatur PLTS Atap *on-grid* tersambung jaringan PLN. Pompa irigasi sawah adalah sistem *off-grid* mandiri sehingga regulasi tersebut tidak relevan.
4. **Kenapa Tetap Tarik Data Per Jam (`1.051.968` baris), Bukan Harian Langsung:**
   - Pompa DC *direct-driven* menghasilkan debit air berbeda di tiap jam tergantung intensitas radiasi matahari.
   - Menggunakan **kurva debit bertahap (*piecewise linear interpolation*)** yang dikalibrasi dari titik terukur studi Gowa (bukan regresi garis lurus 2 titik yang menghasilkan intersep `+34 L/menit` di malam hari, dan bukan ambang on/off biner):
     - `0 W/m² → 0 L/menit`
     - `30 W/m² → 0 L/menit` *(asumsi cut-in rendah agar tidak membuang titik terukur 51 W/m²)*
     - `51 W/m² → 15,6 L/menit` *(mendung sore, terukur Gowa)*
     - `276 W/m² → 53,3 L/menit` *(mendung, terukur Gowa)*
     - `726 W/m² → 84,1 L/menit` *(cerah, terukur Gowa)*
     - `≥ 1000 W/m² → 100,0 L/menit` *(batas atas spesifikasi pompa `6 m³/jam`)*
   - Output air per jam (`flow_lpm × 60 / 1000` m³/jam) lalu dijumlahkan menjadi `solar_water_1kwp_m3` harian di `fact_irrigation_daily`.
5. **Rumus Neraca Air Padi (`NFR`), Bukan Sekadar `ETc`:**
   - Padi sawah membutuhkan perkolasi (`P`) dan penggantian lapisan air (`WLR`), bukan hanya `ETc` (yang hanya cocok untuk palawija):
     $$\text{NFR} = \max\left(0,\; K_c \cdot ET_0 + P + WLR - 0.8 \cdot \text{Rain}\right)$$
   - Parameter: `P = 2,0 mm/hari`, `WLR = 1,0 mm/hari`, hujan efektif `Reff = 0,8 × Rain`, label `need_irrigation = 1` jika hari berada di musim tanam dan `NFR > 1,0 mm/hari`.
   - Kalender tanam awal: **MT1 (Nov–Feb)** dan **MT2 (Mar–Jun)**, masa **Bera (Jul–Okt, `Kc = 0`)**. Koefisien FAO-56 per bulan tanam: awal `1,05` (Nov, Mar), tengah `1,20` (Des, Jan, Apr, Mei), akhir `0,90` (Feb, Jun).
   - **Penyiapan lahan (`250 mm/musim`):** dimasukkan ke simulasi ROI pada 15 hari pertama MT1 (1–15 Nov) & MT2 (1–15 Mar) sebesar `16,67 mm/hari`, namun **tidak** dicampur ke label ML harian agar model ML fokus pada fase tanam.
6. **Target ML = Prediksi `H+1` (Besok), Split Temporal Ketat (Anti-Leakage):**
   - Tidak memprediksi `ET0` hari yang sama (karena `ET0` dihitung dari rumus cuaca hari yang sama).
   - Split berdasarkan waktu: **Train `2011–2022`** (`23.200` baris), **Validasi threshold `2021–2022`** (di dalam train), **Test tidak disentuh `2023–2025`** (`5.808` baris).
   - Semua fitur lag (`1, 2, 3, 7` hari) dan rolling (`3, 7` hari) dihitung per kabupaten (`groupby('region_id')`) dan hanya memakai data `≤ hari t` (ada `assert` selisih tanggal tepat 1 hari).
7. **Konsumsi Diesel Berbasis Volume Air (`L/m³`), Bukan Angka Bensin Per Hektar:**
   - Pompa diesel petani 5,5 HP tipikal menyedot ~`25 m³/jam` dengan konsumsi ~`1,0 L/jam` → **`0,04 L/m³`** (baseline), ditambah sensitivitas **`0,06 L/m³`** (untuk *head* tinggi / mesin tua).

---

## 4. Data Warehouse & Hasil ETL (`kb_solar_irrigation`)

### Sumber Data & Validasi Silang (Stage 3 — `etl_fetch.py` & `etl_load_pg.py`)
- **Open-Meteo Archive API (sumber utama, per jam, timezone `Asia/Jakarta`):** `1.051.968` baris (`8 × 131.496`), **0 null**. Variabel: `temperature_2m` (°C), `relative_humidity_2m` (%), `precipitation` (mm), `cloud_cover` (%), `wind_speed_10m` (**km/h**), `shortwave_radiation` (W/m²), `et0_fao_evapotranspiration` (mm).
- **NASA POWER API (validasi input, harian, community `AG`, `-999 → NaN`):** `43.832` baris (`8 × 5.479`), **0 null**. Variabel: `ALLSKY_SFC_SW_DWN` (MJ/m²/day), `T2M` (°C), `RH2M` (%), `PRECTOTCORR` (mm/day), `WS2M` (**m/s**).

| Kabupaten | Null (OM / NASA) | Radiasi OM (MJ/m²/hr) | Radiasi NASA (MJ/m²/hr) | Pearson `r` |
|---|---:|---:|---:|---:|
| Kulon Progo | 0 / 0 | 18,30 | 18,32 | 0,7530 |
| Bantul | 0 / 0 | 18,35 | 18,32 | 0,7505 |
| Gunungkidul | 0 / 0 | 18,53 | 18,32 | 0,7373 |
| Sleman | 0 / 0 | 17,89 | 18,32 | 0,7559 |
| Purworejo | 0 / 0 | 17,90 | 18,32 | 0,7461 |
| Kab. Magelang | 0 / 0 | 17,46 | 18,32 | 0,7686 |
| Klaten | 0 / 0 | 18,55 | 18,32 | 0,7843 |
| Wonogiri | 0 / 0 | 18,23 | 18,32 | 0,7785 |

> **Temuan Teknis Penting:** Rata-rata radiasi NASA POWER identik (`18,32 MJ/m²/hr`) di seluruh 8 kabupaten karena resolusi grid radiasi NASA POWER kasar (`1° × 1°` ≈ 111 km), sehingga 8 kabupaten jatuh dalam 1 sel grid yang sama. Open-Meteo menangkap variasi mikroklimat lokal nyata (`Kab. Magelang 17,46` di lereng gunung lebih berawan vs `Klaten 18,55` dan `Gunungkidul 18,53`). Ini memperkuat pilihan Open-Meteo sebagai sumber utama dan NASA POWER sebagai validasi regional.

### Skema Bintang Kimball di PostgreSQL (`sql/schema.sql`)
| Tabel | Tipe | Baris | Keterangan |
|---|---|---:|---|
| `dim_region` | Dimensi | `8` | 8 kabupaten + provinsi + lat/lon |
| `dim_date` | Dimensi | `5.479` | Kalender 2011–2025 + `climate_season` + `planting_season` + `kc_paddy` |
| `dim_scenario` | Dimensi | `3` | Kapasitas `1`, `3`, `5 kWp` + `max_flow_lpm` + CAPEX low/high |
| `fact_weather_hourly` | Fakta | `1.051.968` | Data mentah Open-Meteo per jam (`region_id`, `ts`) |
| `fact_nasa_daily` | Fakta | `43.832` | Data validasi NASA POWER harian (`region_id`, `date_id`) |
| `fact_irrigation_daily` | Fakta | `43.832` | Agregasi harian + debit pompa surya `1 kWp` + `nfr_mm` + `need_irrigation` |
| `fact_ml_predictions` | Fakta | `5.808` | Prediksi out-of-sample ML `2023–2025` (LR & RF + threshold `3:1`) |
| `fact_roi_simulation` | Fakta | `192` | Simulasi ROI/BEP seluruh kombinasi wilayah, kapasitas, lahan, BBM, efisiensi |

---

## 5. Hasil Lengkap Uji Statistik (Stage 4 — `stage4_stats_ml.py`)

### Ringkasan Per Kabupaten (Hari Musim Tanam MT1 + MT2, 2011–2025)
| Kabupaten | Hari Tanam | Rata-rata NFR (mm/hr) | % Hari Butuh Irigasi | Radiasi (MJ/m²/hr) | Output Surya 1 kWp (m³/hr) | Hujan (mm/hr) |
|---|---:|---:|---:|---:|---:|---:|
| **Gunungkidul** | 3.634 | **3,30** | **60,10%** | 17,66 | 40,06 | 8,21 |
| **Klaten** | 3.634 | **3,25** | **59,33%** | 17,61 | 39,91 | 8,22 |
| Wonogiri | 3.634 | 3,03 | 54,16% | 17,16 | 39,30 | 9,12 |
| Bantul | 3.634 | 2,95 | 55,01% | 17,58 | 39,97 | 9,09 |
| Kulon Progo | 3.634 | 2,64 | 51,49% | 17,56 | 39,92 | 10,00 |
| Purworejo | 3.634 | 2,60 | 52,37% | 17,19 | 39,38 | 9,99 |
| Sleman | 3.634 | 2,59 | 51,49% | 17,13 | 39,29 | 10,05 |
| **Kab. Magelang** | 3.634 | **2,46** | **49,20%** | 16,65 | 38,64 | 10,11 |

### Uji Hipotesis
- **One-way ANOVA NFR antar 8 kabupaten (musim tanam):** `F = 42,28`, `p = 9,139e-60` (Kruskal-Wallis non-parametrik: `H = 282,68`, `p = 3,009e-57`) → **sangat signifikan** (kebutuhan air Gunungkidul 34% lebih tinggi daripada Kab. Magelang).
- **One-way ANOVA Radiasi antar 8 kabupaten (sepanjang tahun):** `F = 50,14`, `p = 1,518e-71` → **sangat signifikan**.
- **Welch t-test NFR Kemarau (`4,47 mm/hr`) vs Hujan (`2,30 mm/hr`):** `t = 56,39`, `p < 1e-300` (Mann-Whitney `p < 1e-300`).
- **Welch t-test NFR MT2 (`3,56 mm/hr`) vs MT1 (`2,13 mm/hr`):** `t = 41,82`, `p < 1e-300`.
- **Welch t-test Radiasi Kemarau (`18,93 MJ/m²/hr`) vs Hujan (`17,36 MJ/m²/hr`):** `t = 43,12`, `p < 1e-300`.
  - **Insight bisnis:** Ada **sinergi alami** — saat musim kemarau kebutuhan air sawah naik hampir **2× lipat**, pasokan radiasi surya justru **meningkat** di periode yang sama.

---

## 6. Hasil Lengkap Model ML H+1 & Optimasi Threshold (Stage 4)

- **Train (`2011–2022`):** `23.200` baris | **Test tidak disentuh (`2023–2025`):** `5.808` baris | **Rasio kelas positif (butuh irigasi):** `56,8%` (seimbang alami).

| Model | Acc | Prec | Rec | F1 | ROC-AUC | FN (Gagal Irigasi) | FP (Siaga Berlebih) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Climatology (baseline) | 0,598 | 0,682 | 0,546 | 0,606 | 0,651 | 1.497 | 839 |
| Persistence (baseline) | 0,711 | 0,747 | 0,742 | 0,745 | — | 849 | 828 |
| **Logistic Regression (`t=0,50`)** | **0,731** | **0,779** | 0,736 | **0,757** | **0,794** | 871 | 689 |
| **Logistic Regression (`FN:FP=3:1, t=0,21`)** | 0,601 | 0,590 | **0,973** | 0,735 | **0,794** | **88** | 2.227 |
| Random Forest (`t=0,50`) | 0,727 | 0,774 | 0,733 | 0,753 | 0,790 | 880 | 704 |
| Random Forest (`FN:FP=3:1, t=0,24`) | 0,610 | 0,596 | 0,967 | 0,738 | 0,790 | 109 | 2.157 |
| Random Forest (`FN:FP=5:1, t=0,15`) | 0,570 | 0,569 | 1,000 | 0,725 | 0,790 | 0 | 2.499 |

- **Model Juara:** **Logistic Regression** (lebih sederhana, *generalize* sedikit lebih baik daripada Random Forest pada sinyal meteorologi mulus: `AUC 0,794` vs `0,790`).
- **Dampak Optimasi Threshold (`FN:FP = 3:1`, `t = 0,21` dituning murni di validasi `2021–2022`):** menekan hari gagal irigasi (`FN`) sebesar **90%** (`849` di persistence → **`88`** hari, **`Recall 97,3%`**). Konfigurasi `5:1` terlalu ekstrem karena memprediksi hampir semua hari positif (`FP = 2.499`).
- **Top 10 Fitur Terpenting (Random Forest):** `rain_mm` (0,130), `nfr_mm` (0,118), `rain_roll3` (0,061), `need_irrigation` (0,049), `cloud_roll7` (0,048), `nfr_roll3` (0,045), `doy_cos` (0,045), `rain_roll7` (0,044), `rh_mean_pct` (0,041), `cloud_mean_pct` (0,039).

---

## 7. Hasil Lengkap Simulasi ROI & BEP (Stage 5 — `stage5_roi_sim.py`)

### Rincian CAPEX Riil Marketplace Indonesia (Tokopedia/Shopee, Nov 2026 + 15% Instalasi)
Bukti screenshot tersimpan di `docs/bukti_harga/tokopedia_panel_550wp_20261120.png` dan `docs/bukti_harga/tokopedia_pompa_dc_750w_mppt_20261120.png`:
- **Panel surya 550Wp Mono:** `Rp 1,75–3,50 jt/lembar` (bukti screenshot: AE Solar `Rp 1.785.000`, Lesso `Rp 1.865.900`, Jinko `Rp 2.045.000–2.926.000`).
- **Pompa Submersible DC + MPPT:** `750W` `Rp 3,43–6,35 jt` (bukti screenshot: DC 48V 750W + MPPT `Rp 3.418.000`, Gudang Panel Surya `Rp 6.235.000`); `2200W` `Rp 6,5–12 jt`; `3700W` `Rp 13–22 jt`.
- **Total CAPEX (+15% rangka, kabel PV/submersible, pemasangan) & OPEX 2%/tahun:**

| Kapasitas | Panel 550Wp | Pompa DC + MPPT | CAPEX Low | CAPEX High |
|---|---|---|---:|---:|
| **1 kWp** | 2 lembar | 750 W | **Rp 8.500.000** | **Rp 15.500.000** |
| **3 kWp** | 6 lembar | 2200 W | **Rp 20.000.000** | **Rp 38.000.000** |
| **5 kWp** | 10 lembar | 3700 W | **Rp 35.000.000** | **Rp 65.000.000** |

### Tabel BEP Kelompok Tani (`1 ha/kWp`, `0,04 L/m³`, termasuk penyiapan lahan `250 mm/musim`)
| Kabupaten | Kapasitas | Solar Coverage | BEP Low — Biosolar (`Rp 6.800`) | BEP High — Biosolar | BEP Low — Dexlite (`Rp 23.700`) | BEP High — Dexlite |
|---|---:|---:|---:|---:|---:|---:|
| **Gunungkidul** | 1 kWp | 48,70% | 5,48 thn | 10,99 thn | 1,46 thn | 2,73 thn |
| **Gunungkidul** | **5 kWp** | 48,70% | **4,43 thn** | 8,90 thn | **1,20 thn** | **2,27 thn** |
| **Klaten** | 1 kWp | 48,04% | 5,62 thn | 11,30 thn | 1,49 thn | 2,79 thn |
| **Klaten** | **5 kWp** | 48,04% | **4,54 thn** | 9,15 thn | **1,22 thn** | **2,32 thn** |
| **Bantul** | 1 kWp | 48,39% | 5,95 thn | 12,03 thn | 1,57 thn | 2,95 thn |
| **Bantul** | **5 kWp** | 48,39% | **4,80 thn** | 9,72 thn | **1,29 thn** | **2,45 thn** |
| **Wonogiri** | 1 kWp | 46,55% | 6,11 thn | 12,39 thn | 1,61 thn | 3,02 thn |
| **Wonogiri** | **5 kWp** | 46,55% | **4,93 thn** | 9,99 thn | **1,32 thn** | **2,51 thn** |
| Kulon Progo | 5 kWp | 48,63% | 5,12 thn | 10,43 thn | 1,37 thn | 2,61 thn |
| Purworejo | 5 kWp | 48,56% | 5,18 thn | 10,55 thn | 1,38 thn | 2,63 thn |
| Sleman | 5 kWp | 48,12% | 5,24 thn | 10,70 thn | 1,40 thn | 2,66 thn |
| Kab. Magelang | 5 kWp | 47,63% | 5,47 thn | 11,20 thn | 1,46 thn | 2,77 thn |

### Jebakan *Over-Sizing* Petani Individu (`1 ha`, Gunungkidul, Dexlite, `0,04 L/m³`)
| Kapasitas | Solar Coverage | Solar Dihemat/thn | BEP Low | BEP High |
|---|---:|---:|---:|---:|
| **1 kWp** | 48,70% | 253,0 L | **1,46 thn** | **2,73 thn** |
| 3 kWp | 83,24% | 432,4 L | 2,03 thn | 4,01 thn |
| 5 kWp | 98,64% | 512,4 L | 3,06 thn | 5,99 thn |

> **Kesimpulan Bisnis Utama (2 Tuas Keputusan):**
> 1. **Skala Kelompok Tani:** Untuk petani individu (`1 ha`), `1 kWp` adalah ukuran paling rasional (`3–5 kWp` mengalami *diminishing returns* dan memperpanjang BEP). Sebaliknya, pada skema patungan **Kelompok Tani (`5 kWp / 5 ha`)**, skala ekonomi CAPEX membuat BEP turun drastis hingga **4 kabupaten sudah tembus `< 5 tahun` bahkan dengan Biosolar subsidi**.
> 2. **Sensitivitas Subsidi BBM:** Begitu subsidi Biosolar dibatasi/dicabut pasca-2026 (beralih ke Dexlite `Rp 23.700/L`), **seluruh 8 kabupaten langsung sangat layak dengan BEP `1,20–2,77 tahun`**, dengan prioritas investasi utama di **Gunungkidul** dan **Klaten**.

---

## 8. Dashboard Power BI (`kbfinpro.pbix`) & Rumus DAX

- **Mode:** Import dari PostgreSQL `localhost:5432 / kb_solar_irrigation` (6 tabel: `dim_date`, `dim_region`, `dim_scenario`, `fact_irrigation_daily`, `fact_ml_predictions`, `fact_roi_simulation`; `fact_weather_hourly` sengaja tidak di-import agar ringan di RAM).
- **Relasi Model View:** Skema Bintang Kimball `1 → *` satu arah dari seluruh tabel dimensi ke tabel fakta.

### Rumus DAX (Tabel `_Measures`)
```dax
Avg BEP Low (Yr) = AVERAGE('public fact_roi_simulation'[bep_low_years])
Avg BEP High (Yr) = AVERAGE('public fact_roi_simulation'[bep_high_years])
Solar Coverage % = DIVIDE(SUM('public fact_roi_simulation'[annual_solar_m3]), SUM('public fact_roi_simulation'[annual_demand_m3]))
Annual Net Saving (Low) = SUM('public fact_roi_simulation'[annual_net_saving_low])

ML Recall (Tuned) =
VAR TP = CALCULATE(COUNTROWS('public fact_ml_predictions'), 'public fact_ml_predictions'[target_next] = 1, 'public fact_ml_predictions'[pred_lr_fn3] = 1)
VAR Pos = CALCULATE(COUNTROWS('public fact_ml_predictions'), 'public fact_ml_predictions'[target_next] = 1)
RETURN DIVIDE(TP, Pos)

ML Missed Days (FN) =
CALCULATE(
    COUNTROWS('public fact_ml_predictions'),
    'public fact_ml_predictions'[target_next] = 1,
    'public fact_ml_predictions'[pred_lr_fn3] = 0
)
```

### Isi 3 Halaman & Skrip Demo Live (3 Menit)
1. **Page 1 — `Executive ROI`:** 4 slicer *Single Select* (`fuel_scenario`, `land_mode`, `capacity_kwp`, `diesel_l_per_m3`), 4 KPI Card, Clustered Bar Chart BEP per kabupaten, dan Tabel ringkas.
   - *Demo:* klik toggle `Biosolar` → `Dexlite` lalu `Individu (1 ha)` → `Kelompok Tani (1 ha/kWp)` untuk memperlihatkan lompatan BEP secara langsung.
2. **Page 2 — `Climate & Demand` (Drill-Through `kabupaten`):** Grafik kombo `Avg nfr_mm` vs `Avg rad_mj_m2` per bulan (menunjukkan sinergi kemarau) + grafik batang `Sum need_irrigation` per tahun (menangkap lonjakan El Niño 2018, 2019, 2023).
   - *Demo:* dari Page 1, **klik kanan** batang `Gunungkidul` → **Drill through → Climate & Demand**, lalu `Ctrl + Klik` tombol panah biru `←` di kiri atas untuk kembali.
3. **Page 3 — `ML H+1 Prediction`:** 2 KPI Card (`Recall 97,33%`, `FN = 88`), Confusion Matrix (`TN=284`, `FP=2.227`, `FN=88`, `TP=3.209`, Total `5.808`), dan grafik garis kalibrasi `Avg prob_lr` vs `Avg target_next` per bulan (menempel rapat di rentang `0,35–0,85`).

---

## 9. Panduan Setup untuk Teman Kelompok

- **Ingin langsung lihat/edit dashboard tanpa install PostgreSQL:** cukup install **Power BI Desktop** (tidak perlu login Microsoft Fabric, tutup popup login) lalu buka `kbfinpro.pbix`.
- **Ingin jalankan pipeline penuh dari awal:**
  ```powershell
  pip install -r requirements.txt
  copy .env.example .env   # isi PGPASSWORD PostgreSQL lokal
  py etl_fetch.py          # ~2-3 menit (tarik 8 kabupaten ke data/raw/)
  py etl_load_pg.py        # ~45 detik (muat 1,05 juta baris ke PostgreSQL)
  py stage4_stats_ml.py    # ~15 detik (ANOVA, t-test, ML H+1)
  py stage5_roi_sim.py     # ~5 detik (simulasi ROI & muat ke PostgreSQL)
  ```
- **Riwayat Commit Git (bersih per tahap):**
  - `a2ac515` — Stage 3 ETL 8 kabupaten & skema bintang PostgreSQL
  - `b30e8f3` — Stage 4 Uji statistik & ML H+1 + threshold tuning
  - `ed5a8ea` — Stage 5 Simulasi ROI/BEP & muat tabel fakta BI
  - `93abf5c` — Track CSV hasil olahan kecil (`data/processed/*.csv`)
  - `f4124af` — Dashboard Power BI 3 halaman (`kbfinpro.pbix`)
  - `3311fe9` — Update `CAPEX_TABLE` dengan harga komponen marketplace riil
  - `7644c77` — Bukti screenshot harga Tokopedia (`docs/bukti_harga/`)
  - `1befa78` — Refresh `kbfinpro.pbix` dengan CAPEX terbaru

---

## 10. Batasan Laporan (*Limitations*) & Antisipasi Pertanyaan Dosen

### Batasan yang Wajib Ditulis Jujur di Laporan
1. **Data reanalysis:** Open-Meteo dan NASA POWER adalah data model *reanalysis*, bukan hasil ukur stasiun cuaca BMKG di sawah langsung.
2. **Label irigasi sintetis & kalender tanam:** Label `need_irrigation` dihitung dari neraca air padi FAO/KP-01 dengan asumsi kalender `MT1 (Nov–Feb)` dan `MT2 (Mar–Jun)`, bukan catatan riil petani.
3. **Ekstrapolasi kurva pompa:** Kurva debit dikalibrasi dari 1 sistem (Gowa, `900 Wp / 750 W`) dengan *cut-in* asumsi `30 W/m²`, lalu diskalakan linear ke `3` dan `5 kWp`.
4. **Cakupan CAPEX & umur komponen:** Bukti screenshot langsung mencakup komponen `1 kWp` (panel 550Wp + pompa 750W MPPT); `3` dan `5 kWp` dari komponen pasar + `15%` instalasi. Biaya penggantian pompa DC (~tahun ke-5–7) belum dimasukkan ke arus kas.

### Antisipasi Pertanyaan Dosen saat Sidang
- **T: Kenapa Logistic Regression dipakai, bukan Random Forest / XGBoost?**
  - **J:** Pada uji temporal 2023–2025, Logistic Regression mencapai `ROC-AUC 0,794` dan `F1 0,757`, unggul tipis atas Random Forest (`AUC 0,790`, `F1 0,753`). Di dunia BI, model lebih sederhana dengan performa lebih baik dan mudah dijelaskan selalu lebih dipilih.
- **T: Akurasi turun dari 73,1% jadi 60,1% setelah threshold dituning, kenapa tetap dipakai?**
  - **J:** Karena biaya kesalahan tidak simetris. Gagal menyiram padi (*False Negative*) berisiko gagal panen, sedangkan salah siaga (*False Positive*) cuma pengecekan pompa. Dengan `t = 0,21` (`FN:FP = 3:1`), hari gagal irigasi turun **90%** (`849 → 88` hari, `Recall 97,3%`).
- **T: Kenapa rata-rata radiasi NASA POWER sama persis (`18,32`) di 8 kabupaten?**
  - **J:** Resolusi grid radiasi NASA POWER adalah `1° × 1°` (~111 km), sehingga 8 kabupaten DIY–Jateng masuk 1 sel grid. Itulah alasan Open-Meteo dipakai sebagai sumber utama (menangkap beda lokal `17,46–18,55 MJ/m²/hr`) dan NASA POWER hanya untuk validasi silang regional (`r = 0,74–0,78`).
- **T: Kenapa di individu `1 ha`, pompa `5 kWp` malah lebih lama balik modalnya daripada `1 kWp`?**
  - **J:** Output `1 kWp` (~`40 m³/hari`) sudah mendekati kebutuhan harian `1 ha`. Memasang `5 kWp` di `1 ha` membuat kapasitas terbuang saat hari biasa (CAPEX 4× lipat, penghematan solar cuma 2× lipat). `5 kWp` baru optimal jika dipakai bersama kelompok tani `5 ha`.

---

## 11. Atribusi Data & Sumber Referensi

- **Open-Meteo Historical Weather API:** Weather data by [Open-Meteo.com](https://open-meteo.com/), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **NASA POWER Project:** [NASA Langley Research Center POWER](https://power.larc.nasa.gov/).
- **FAO-56 Crop Evapotranspiration:** [FAO Irrigation and Drainage Paper 56](https://www.fao.org/3/x0490E/x0490e00.htm).
- **BPS Produksi Padi 2024:** [BPS DIY](https://yogyakarta.bps.go.id/en/publication/2025/06/05/224d74125ffbaaa6e7c0f560/ringkasan-eksekutif-luas-panen-dan-produksi-padi-daerah-istimewa-yogyakarta-2024.html), [BPS Jateng](https://jateng.bps.go.id/id/pressrelease/2025/03/03/1558/luas-panen-dan-produksi-padi-2024--angka-tetap--provinsi-jawa-tengah.html).
- **Harga BBM & Kebijakan Subsidi:** [Katadata](https://katadata.co.id/amp/berita/energi/6ae6aa7b66234/daftar-harga-bbm-pertamina-shell-bp-dan-vivo-per-1-november), [Otodriver](https://otodriver.com/berita/2026/harga-biosolar-dan-pertalite-dipertahankan-sampai-akhir-desember-2026-harefhgj026).
- **Studi Lapangan Pompa Surya:** [Studi Gowa (Abdi Insani Unram)](https://abdiinsani.unram.ac.id/index.php/jurnal/article/download/800/443/6509), [UNU Blitar](https://jurnal.unublitar.ac.id/index.php/briliant/article/download/1022/pdf/3615), [Telkom University](https://openlibrarypublications.telkomuniversity.ac.id/index.php/engineering/article/download/15208/14931/29853).
