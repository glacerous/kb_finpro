# Script Presentasi & Panduan Paham Semua Slide (10 Slide — Format Minggu 14)

File ini pasangan dari `docs/Presentasi_Tugas_Besar_KB.pptx`. Baca urut dari Slide 1 sampai 10 — tiap slide punya **Inti Sederhana** (biar kamu benar-benar paham alurnya) dan **Skrip Bicara** (bahasa natural untuk presentasi ~7 menit + 3 menit demo Power BI).

---

## Slide 1 — Title (Pembuka)
- **Inti sederhana:** Kenalin judul proyek (ganti pompa diesel ke pompa surya untuk petani padi di 8 kabupaten sekitar DIY) dan nama 5 anggota tim.
- **Skrip bicara:**
  > "Selamat pagi/siang Bapak/Ibu dosen dan teman-teman. Kami dari kelas SI-C akan mempresentasikan tugas besar Kecerdasan Bisnis tentang **prediksi kebutuhan irigasi harian dan kelayakan ROI pompa air tenaga surya** bagi petani padi di 8 kabupaten sekitar DIY. Intinya, kami ingin membantu petani menjawab satu pertanyaan nyata: **untung atau rugi kalau pompa diesel diganti pompa tenaga surya?**"

---

## Slide 2 — Context & Business Question (Masalah & Pertanyaan Bisnis)
- **Inti sederhana:** Padi DIY turun 14,95% karena kekeringan. Petani pakai pompa diesel, tapi Biosolar murah (`Rp 6.800/L`) cuma dijamin sampai Des 2026 — kalau naik ke Dexlite (`Rp 23.700/L`), petani makin berat. Pompa surya bebas solar, tapi modal belinya mahal.
- **Skrip bicara:**
  > "Kenapa topik ini penting? Data BPS menunjukkan produksi padi DIY tahun 2024 turun **14,95%**, paling parah di Gunungkidul, Bantul, dan Sleman. Selama ini petani mengandalkan pompa diesel, tapi Biosolar subsidi `Rp 6.800` per liter hanya dijamin sampai akhir Desember 2026, sedangkan Dexlite sudah `Rp 23.700` — hampir 3,5 kali lipat. Pompa tenaga surya bisa menghemat solar, tapi modal awalnya besar. Maka kami merumuskan 3 pertanyaan bisnis: **pertama**, di kabupaten mana dan ukuran berapa (`1`, `3`, `5 kWp`) pompa surya paling cepat balik modal — dan lebih cocok individu atau kelompok tani? **Kedua**, apakah beda kebutuhan air antar 8 kabupaten benar-benar nyata? **Ketiga**, bisakah kita memprediksi besok sawah butuh disiram atau tidak?"

---

## Slide 3 — Approach & Methodology (Alur Kerja 5 Tahap)
- **Inti sederhana:** Alur kerja kita persis materi matkul BI dari hulu ke hilir: ambil data cuaca → rapikan ke PostgreSQL → uji statistik → latih ML peramal besok → hitung Rupiah/BEP → tampilkan di Power BI.
- **Skrip bicara:**
  > "Untuk menjawabnya, kami membangun pipeline BI lengkap dalam 5 tahap. Pertama, menarik data cuaca 15 tahun per jam dari Open-Meteo dan pembanding harian dari NASA POWER. Kedua, menyimpannya ke Data Warehouse PostgreSQL skema bintang, sambil menghitung dua hal: berapa air yang sanggup disedot pompa surya tiap jam (memakai kurva lapangan studi Gowa), dan berapa air yang dibutuhkan padi hari itu (`NFR` standar FAO/KP-01). Ketiga, uji statistik ANOVA dan t-test. Keempat, melatih model ML prediksi besok (`H+1`). Kelima, simulasi untung-rugi di 192 skenario yang langsung terhubung ke Power BI."

---

## Slide 4 — Data Foundation (Data Warehouse, ETL & Validasi)
- **Inti sederhana:** Kita punya 1,05 juta baris cuaca per jam (0 data kosong) yang disusun rapi jadi Skema Bintang di PostgreSQL. Validasi ke NASA POWER membuktikan data kita akurat, sekaligus menemukan bahwa Open-Meteo lebih detail daripada NASA POWER.
- **Skrip bicara:**
  > "Ini tampilan Skema Bintang Kimball kami di PostgreSQL dan Power BI: 3 tabel dimensi — wilayah, tanggal, dan skenario — terhubung ke tabel fakta berisi lebih dari **1,05 juta baris** data cuaca per jam tanpa satu pun data kosong. Proses ETL-nya *idempotent*, artinya aman dijalankan ulang tanpa bikin data dobel. Saat kami cek silang dengan NASA POWER, korelasinya kuat (`r = 0,74 sampai 0,78`). Menariknya, rata-rata radiasi NASA POWER sama persis (`18,32`) di 8 kabupaten karena kotak peta satelitnya besar (111 km), sedangkan Open-Meteo menangkap perbedaan lokal seperti Magelang yang lebih berawan dibanding Klaten dan Gunungkidul."

---

## Slide 5 — Dashboard & Descriptive Insights (Hasil Uji Statistik)
- **Inti sederhana:** Uji statistik membuktikan (1) Gunungkidul & Klaten jauh lebih haus air daripada Magelang, dan (2) saat kemarau kebutuhan air naik 2× lipat, sinar matahari justru makin terik — pas banget untuk pompa surya!
- **Skrip bicara:**
  > "Masuk ke hasil statistik. Uji ANOVA membuktikan perbedaan kebutuhan air antar 8 kabupaten sangat signifikan (`F = 42,28`): **Gunungkidul dan Klaten butuh air 34% lebih tinggi daripada Magelang**. Lalu dari grafik kiri dan uji Welch t-test, kami menemukan **sinergi alami**: tepat saat musim kemarau ketika sawah butuh air hampir **2 kali lipat** (`4,47` vs `2,30 mm/hari`), sinar matahari justru mencapai puncaknya (`18,93 MJ/m²/hari`). Artinya tenaga surya paling melimpah tepat saat petani paling butuh air. Grafik kanan juga langsung menangkap lonjakan hari kering pada tahun El Niño 2018, 2019, dan 2023."

---

## Slide 6 — Predictive Model (ML H+1 & Optimasi Threshold)
- **Inti sederhana:** Model menebak "besok sawah perlu disiram atau tidak?" tanpa nyontek masa depan. Model sederhana (Logistic Regression) menang! Lalu kita atur kepekaannya supaya lebih baik siaga berlebih daripada telat menyiram padi.
- **Skrip bicara:**
  > "Untuk operasional harian, kami melatih model klasifikasi menebak apakah **besok (`H+1`) sawah butuh disiram**. Data dibagi urut waktu: 2011–2022 untuk belajar dan 2023–2025 (`5.808` hari) untuk ujian mandiri supaya tidak bocor. Hasilnya, **Logistic Regression** yang lebih sederhana justru menjadi model terbaik (`ROC-AUC 0,794`), mengalahkan baseline dan tipis di atas Random Forest. Karena **gagal menyiram (`False Negative`)** jauh lebih rugi daripada sekadar siaga berlebih, kami ubah ambang batasnya dari `0,50` ke `0,21` dengan rasio biaya `3:1`. Hasilnya, hari gagal irigasi turun **90%** dari `849` hari menjadi hanya **`88` hari**, dengan **Recall 97,3%**."

---

## Slide 7 — Operationalization & Power BI Integration (Live Demo 2–3 Menit)
- **Inti sederhana:** Tunjukkan langsung Power BI `kbfinpro.pbix` biar dosen lihat sistemnya benar-benar jalan, bukan cuma gambar statis!
- **Skrip bicara + klik live:**
  > "Semua angka tadi kami integrasikan ke dashboard Power BI 3 halaman (`kbfinpro.pbix`) dengan 6 rumus DAX. Mari kita lihat sekilas secara langsung:
  > 1. *(Di Page 1 `Executive ROI`)*: Saat ini terpilih `Biosolar` dan `Individu 1 ha` — BEP masih lama. Begitu kita klik **`Dexlite`** dan pindah ke **`Kelompok Tani`**, BEP langsung turun drastis ke kisaran **1,2 sampai 2,5 tahun**.
  > 2. *(Klik kanan batang `Gunungkidul` → `Drill through → Climate & Demand`)*: Kita bisa langsung melihat profil iklim khusus Gunungkidul, lalu `Ctrl + Klik` tombol panah biru untuk kembali.
  > 3. *(Pindah ke Page 3 `ML H+1 Prediction`)*: Di sini terlihat Recall `97,33%`, FN hanya `88` hari, dan garis probabilitas prediksi menempel rapat dengan data aktual sepanjang tahun."

---

## Slide 8 — Ethics, Governance & Limitations (Etika & Batasan)
- **Inti sederhana:** Tunjukkan kita jujur dan patuh aturan: tidak ada data pribadi petani yang bocor (UU PDP), dan kita terbuka soal 4 keterbatasan data/model.
- **Skrip bicara:**
  > "Dari sisi tata kelola dan etika sesuai **UU PDP No. 27/2022**, seluruh data iklim kami bersumber publik tanpa data pribadi petani (PII). Jika kelak dipakai di lapangan bersama Gapoktan, data identitas wajib dipseudonimisasi. Kami juga mencatat jujur 4 batasan: data cuaca berupa reanalisis bukan sensor BMKG langsung di sawah, label irigasi dihitung dari rumus FAO/KP-01, kurva debit pompa diekstrapolasi dari 1 studi di Gowa, dan biaya penggantian motor pompa di tahun ke-5–7 belum masuk arus kas."

---

## Slide 9 — Recommendation & ROI (Kesimpulan Bisnis & Uang)
- **Inti sederhana:** Ini klimaks presentasi! Pakai harga asli Tokopedia (`1 kWp Rp 8,5–15,5 jt`, `5 kWp Rp 35–65 jt`): (1) jangan *over-sizing* di lahan 1 ha, (2) skema **Kelompok Tani 5 kWp / 5 ha** adalah solusi paling cuan, terutama di Gunungkidul & Klaten!
- **Skrip bicara:**
  > "Terakhir, ini kesimpulan bisnis utama kami memakai harga riil marketplace Tokopedia (+15% pemasangan). Ada **dua temuan kunci**. **Pertama, hindari jebakan *over-sizing***: untuk petani individu `1 ha`, ukuran **`1 kWp`** paling rasional (`1,46–2,73` tahun pada Dexlite); memasang `5 kWp` di `1 ha` justru boros karena modal naik 4 kali tapi hemat solar cuma 2 kali. **Kedua, kekuatan skema Kelompok Tani (`5 kWp` untuk `5 ha`)**: pada skema patungan ini, **4 kabupaten** (Gunungkidul, Klaten, Bantul, Wonogiri) sudah balik modal di bawah 5 tahun **bahkan dengan Biosolar subsidi**, dan seluruh 8 kabupaten langsung sangat layak (`1,20–2,77` tahun) jika subsidi dicabut. Rekomendasi kami: Dinas memprioritaskan hibah komunal `5 kWp` di **Gunungkidul dan Klaten** sebelum batas subsidi Desember 2026, serta kelompok tani menyisihkan 15% penghematan solar untuk dana cadangan ganti pompa."

---

## Slide 10 — Closing / Q&A
- **Skrip bicara:**
  > "Sekian presentasi dari kelompok kami. Seluruh kode Python, skema SQL, bukti harga Tokopedia, dan file Power BI tersedia terbuka di repositori GitHub kami. Terima kasih, silakan jika ada pertanyaan."
