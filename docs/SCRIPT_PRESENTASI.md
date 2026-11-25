# Script Presentasi 11 Slide — Tugas Besar Kecerdasan Bisnis (SI-C)

> **Cara pakai:** Tidak perlu dihafal mati. Cukup baca santai per poin sesuai urutan slide (~45–60 detik/slide, total ±10–12 menit termasuk live demo).
> Setiap istilah teknis & nama tool sudah langsung disertai penjelasan bahasa sederhananya.

---

## Pembagian 5 Presenter (Opsional — Bebas Ditukar)
- **Presenter 1:** Slide 1 (Cover) & Slide 2 (Konteks, 8 Kabupaten & Masalah)
- **Presenter 2:** Slide 3 (Pendekatan 5 Tahap & Rumus BEP) & Slide 4 (Fondasi Data & Validasi)
- **Presenter 3:** Slide 5 (Statistik ANOVA & t-test) & Slide 6 (Prediksi ML H+1)
- **Presenter 4:** Slide 7 (Web Dashboard Interaktif) & Slide 8 (Power BI + Live Demo)
- **Presenter 5:** Slide 9 (Rekomendasi ROI), Slide 10 (Etika & Batasan), Slide 11 (Penutup)

---

## Slide 1 — Cover
> "Selamat pagi/siang Bapak/Ibu dosen dan teman-teman. Kami dari kelas SI-C akan mempresentasikan proyek Kecerdasan Bisnis kami: **Prediksi Ketersediaan Energi Surya, Kebutuhan Irigasi Harian, serta Kelayakan ROI Pompa Air Tenaga Surya bagi Petani Padi** di **8 kabupaten** wilayah DIY dan Jawa Tengah Selatan menggunakan 15 tahun data cuaca dari 2011 sampai 2025."

---

## Slide 2 — Konteks, Wilayah Studi & Masalah Bisnis
> "Kenapa topik ini penting? Ada dua masalah nyata di lapangan:
> 1. **Pertama, kekeringan:** Data BPS mencatat produksi padi DIY tahun 2024 turun **14,95%** akibat kemarau El Nino, paling parah di Gunungkidul, Bantul, dan Sleman.
> 2. **Kedua, risiko biaya solar:** Petani selama ini pakai pompa diesel berbahan bakar solar. Nah, berdasarkan berita Jawa Pos dan ANTARA News, jaminan harga **Biosolar subsidi Rp 6.800/liter** baru dipastikan pemerintah sampai **31 Desember 2026**. Kalau petani harus beli solar nonsubsidi (**Dexlite**), harganya sudah **Rp 23.700/liter** — hampir 3,5 kali lipat!
>
> Studi kami mencakup **8 kabupaten**: 4 di DIY *(Gunungkidul, Bantul, Sleman, Kulon Progo)* dan 4 di Jateng Selatan *(Klaten, Wonogiri, Purworejo, Kab. Magelang)*. Kami menjawab 3 pertanyaan bisnis: kapan pompa surya balik modal, wilayah mana paling butuh air, dan bisakah kita memprediksi jadwal siram besok?"

---

## Slide 3 — Pendekatan 5 Tahap (Pipeline BI) & Rumus Balik Modal
> "Seluruh proyek ini kami bangun mengikuti 5 tahap materi Kecerdasan Bisnis secara *end-to-end*:
> 1. **ETL & Ingestion (Python):** Kami menarik 1,05 juta baris data cuaca per jam dari API Open-Meteo dan NASA POWER, membersihkannya sampai 0 data kosong, lalu memuatnya secara *idempotent* — artinya skrip aman dijalankan ulang tanpa bikin data dobel.
> 2. **Data Warehouse (PostgreSQL Star Schema):** Data disimpan ke **PostgreSQL** memakai **Skema Bintang Kimball** (3 tabel dimensi + 5 tabel fakta), sambil menghitung kebutuhan air sawah harian (*NFR*) dan volume air yang bisa disedot pompa surya.
> 3. **Uji Statistik (SciPy):** Memakai library Python **SciPy**, kami menjalankan uji **ANOVA** dan **Welch t-test** untuk membuktikan beda kebutuhan air antar kabupaten dan antar musim.
> 4. **Predictive Analytics / ML H+1 (Scikit-Learn):** Memakai library **Scikit-Learn**, kami melatih model Machine Learning untuk memprediksi apakah besok sawah butuh disiram.
> 5. **Prescriptive ROI & BI Visual:** Kami mensimulasikan balik modal untuk 192 skenario lalu menampilkannya di **Power BI** dan **Web Dashboard Interaktif**.
>
> **Cara hitung balik modalnya simpel:** bukan dari hasil jual padi, melainkan dari **uang beli solar yang tidak jadi keluar setiap tahun** (dikurangi biaya perawatan 2%), lalu dipakai menutup modal beli paket pompa surya di awal. Contoh di Gunungkidul: modal Rp 35 juta, hemat bersih solar Rp 7,9 juta/tahun, jadi balik modal dalam **4,43 tahun** — dan kalau harga Dexlite cuma **1,20 tahun**."

---

## Slide 4 — Fondasi Data & Validasi
> "Ini tampilan arsitektur data kami. Di **PostgreSQL**, kami menyimpan lengkap **8 tabel** (termasuk 1,05 juta baris cuaca per jam). Namun di **Power BI**, kami sengaja hanya me-load **6 tabel inti** yang sudah diringkas harian (*Import Mode*) agar dashboard tetap ringan dan cepat — ini best practice dalam BI.
>
> Untuk menjaga kualitas data, kami melakukan **validasi silang** antara Open-Meteo dan satelit **NASA POWER**. Korelasinya kuat (`r = 0,74 sampai 0,78`). Menariknya, grid satelit NASA terlalu kasar (111 km) sehingga 8 kabupaten terbaca sama rata `18,32`, sedangkan Open-Meteo menangkap perbedaan cuaca lokal secara nyata. Selain itu, harga modal awal pompa (**CAPEX**) kami ambil langsung dari harga riil marketplace Tokopedia ditambah 15% biaya pasang."

---

## Slide 5 — Temuan Wilayah & Sinergi Matahari (Statistik)
> "Masuk ke hasil uji statistik memakai **SciPy**:
> - Pertama, uji **One-Way ANOVA** — yaitu uji untuk membuktikan apakah rata-rata kebutuhan air di **8 kabupaten** memang berbeda nyata dan bukan kebetulan. Hasilnya sangat signifikan (`F = 42,28`, `p < 0,001`): **Gunungkidul** dan **Klaten** adalah dua wilayah paling haus air, 34% lebih tinggi dibanding **Kab. Magelang**.
> - Kedua, uji **Welch t-test** — yaitu uji untuk membandingkan **2 musim** (kemarau vs hujan). Hasilnya membuktikan **sinergi alami**: saat musim kemarau, kebutuhan air sawah melonjak **2 kali lipat**, dan di saat yang sama sinar matahari justru mencapai puncaknya!
>
> Artinya bagi petani: pompa surya bekerja paling kuat justru di bulan-bulan paling kering, termasuk saat kemarau panjang El Nino 2018, 2019, dan 2023."

---

## Slide 6 — Prediksi Jadwal Siram Besok (Machine Learning H+1)
> "Di tahap prediktif, kami memakai **Scikit-Learn** (library Python untuk Machine Learning) untuk menjawab satu pertanyaan: *apakah besok sawah butuh disiram?*
>
> Kami memisahkan data secara urutan waktu (**Temporal Split**): data 2011–2022 untuk melatih model, dan 2023–2025 (5.808 hari) murni untuk menguji supaya model tidak 'nyontek' masa depan. Kami membandingkan 2 baseline sederhana melawan **Logistic Regression** (model yang menghitung peluang 0–100% besok butuh air) dan **Random Forest** (model berbasis banyak pohon keputusan).
>
> Hasilnya, **Logistic Regression** paling unggul dengan skor **ROC-AUC 0,794** — artinya model cukup pintar membedakan hari butuh siram dan hari tidak butuh siram. Lalu kami turunkan ambang batas (*threshold*) ke `0,21` dengan bobot biaya 3:1. Kenapa? Karena **gagal siram (False Negative)** jauh lebih merugikan petani dibanding bersiaga pompa lebih awal. Hasilnya, hari gagal siram turun drastis **90%** dari 849 menjadi hanya **88 hari**, dengan **Recall 97,3%** (dari 100 hari kering, 97 hari berhasil diperingatkan H-1)."

---

## Slide 7 — Web Dashboard Interaktif (Peta 8 Kabupaten)
> "Agar hasil analisis mudah dipahami pengambil keputusan secara geografis, kami membangun **Web Dashboard Interaktif** (`dashboard_interaktif.html`) yang berjalan 100% offline.
>
> Di peta ini terlihat jelas seluruh **8 kabupaten**. Pada skenario **Kelompok Tani 5 kWp (5 hektar)** dengan harga **Biosolar Rp 6.800/L**, sudah ada **4 kabupaten** berwarna hijau yang balik modal di bawah 5 tahun: **Gunungkidul (4,43 thn), Klaten (4,54 thn), Bantul (4,80 thn), dan Wonogiri (4,93 thn)**. Dan kalau slider harga BBM di bawah digeser ke **Dexlite Rp 23.700/L**, seluruh **8 kabupaten** langsung hijau dan balik modal kurang dari 3 tahun."

---

## Slide 8 — Dashboard Analitik Power BI & Live Demo
> "Selain peta web, kami membangun **Dashboard Power BI 3 halaman** (`kbfinpro.pbix`) dengan **6 rumus DAX** (rumus dinamis di Power BI, mirip rumus Excel, untuk menghitung rata-rata BEP, penghematan, dan Recall secara otomatis saat filter diklik) serta fitur **Drill-Through** (klik kanan 1 kabupaten untuk langsung masuk ke halaman rincian iklim kabupaten tersebut).
>
> *(Lakukan Live Demo 2 menit sesuai kotak di bawah slide:)*
> 1. Buka **Web Dashboard**: geser slider harga BBM dari Biosolar ke Dexlite & klik toggle Individu vs Kelompok Tani.
> 2. Buka **Power BI Page 1**: klik kanan **Gunungkidul → Drill through → Climate & Demand** untuk lihat grafik 15 tahun khusus Gunungkidul.
> 3. Pindah ke **Page 3**: tunjukkan matriks prediksi ML (Recall 97,3%) dan kurva kalibrasi."

---

## Slide 9 — Rekomendasi Keputusan & Perbandingan ROI
> "Dari seluruh perhitungan, ini 3 rekomendasi utama kami:
> 1. **Untuk Dinas Pertanian & ESDM:** Prioritaskan bantuan pompa komunal **5 kWp (5 ha)** di **Gunungkidul, Klaten, Bantul, dan Wonogiri** — 4 wilayah ini sudah layak di bawah 5 tahun meski masih pakai Biosolar subsidi, sekaligus jadi pelindung kalau subsidi BBM disesuaikan setelah 2026.
> 2. **Untuk Petani Individu (1 ha):** Pilih paket kecil **1 kWp (Rp 8,5–15,5 juta)** saja. **Hindari beli 5 kWp** untuk 1 hektar (*over-sizing*) karena kapasitas airnya terbuang dan balik modalnya membengkak di atas 12 tahun. Lalu sisihkan 15% penghematan solar tiap tahun untuk dana cadangan ganti motor pompa.
> 3. **Untuk Operasional Harian:** Gunakan sinyal peringatan ML H+1 (Recall 97,3%) untuk jadwal nyalakan pompa dan padukan dengan kalender tanam resmi KATAM."

---

## Slide 10 — Etika, Tata Kelola & Batasan
> "Dari sisi tata kelola data, proyek ini mematuhi **UU PDP No. 27/2022** karena 100% menggunakan data iklim publik tanpa data pribadi petani. Kami juga menyusun **Model Card** agar jelas bahwa prediksi ML ini adalah alat bantu keputusan bagi petani (*human-in-the-loop*), bukan saklar pompa otomatis tanpa pengawasan.
>
> Secara transparan, kami mengakui **4 batasan**: (1) data cuaca berbasis reanalisis satelit bukan sensor fisik BMKG di tiap sawah, (2) label irigasi dihitung dari rumus NFR FAO, (3) kurva debit pompa diekstrapolasi dari 1 studi lapangan di Gowa, dan (4) biaya penggantian motor pompa DC di tahun ke-5–7 belum dipotong dalam rumus balik modal."

---

## Slide 11 — Penutup
> "Sekian presentasi dari kelompok kami. Seluruh kode Python, skema SQL PostgreSQL, bukti harga Tokopedia, file Power BI, dan Web Dashboard Interaktif 8 kabupaten tersedia lengkap di repositori GitHub kami. Terima kasih, silakan jika Bapak/Ibu dosen atau teman-teman ada pertanyaan."

---

## Kamus Cepat Istilah & Tools (Bawaan Buat Jawab Pertanyaan Dosen)

| Istilah / Tool | Arti Simpel (1 Kalimat) | Dipakai di Slide |
|---|---|---|
| **ETL** (*Extract, Transform, Load*) | Proses ambil data mentah dari API, bersihkan (`0 null`), lalu muat ke database. | Slide 3, 4 |
| **Idempotent** | Skrip aman dijalankan berkali-kali tanpa bikin data jadi dobel (`ON CONFLICT DO UPDATE`). | Slide 3, 4 |
| **PostgreSQL** | Database relasional tempat menyimpan Data Warehouse lengkap (8 tabel, 1,05 juta baris). | Slide 3, 4 |
| **Kimball Star Schema** | Cara menyusun tabel database: tabel **Dimensi** (konteks: wilayah, tanggal, paket) mengelilingi tabel **Fakta** (angka hasil ukur). | Slide 3, 4 |
| **Open-Meteo & NASA POWER** | Dua sumber data cuaca global gratis; NASA dipakai untuk **validasi silang** keakuratan Open-Meteo. | Slide 3, 4 |
| **NFR** (*Net Field Requirement*) | Rumus standar irigasi (FAO/KP-01) untuk menghitung kebutuhan air bersih sawah per hari setelah dikurangi hujan. | Slide 3, 5 |
| **CAPEX / OPEX / BEP / kWp** | **CAPEX** = modal beli alat awal; **OPEX** = biaya perawatan 2%/thn; **BEP** = lama balik modal; **kWp** = ukuran daya panel surya. | Slide 3, 4, 9 |
| **SciPy** | Library Python khusus perhitungan statistik ilmiah (dipakai untuk menjalankan ANOVA & Welch t-test). | Slide 3, 5 |
| **One-Way ANOVA** | Uji statistik untuk membuktikan apakah rata-rata kebutuhan air di **lebih dari 2 kelompok (8 kabupaten)** benar-benar berbeda nyata. | Slide 3, 5 |
| **Welch t-test** | Uji statistik untuk membandingkan rata-rata **2 kelompok saja** (musim kemarau vs musim hujan). | Slide 3, 5 |
| **Scikit-Learn** | Library Python paling populer untuk melatih dan mengevaluasi model Machine Learning. | Slide 3, 6 |
| **Temporal Split** | Bagi data latih (2011–2022) & data uji (2023–2025) sesuai urutan waktu agar tidak bocor (*anti-leakage*). | Slide 3, 6 |
| **Logistic Regression** | Model ML yang menghitung probabilitas (0–100%) apakah besok sawah butuh disiram. | Slide 6 |
| **Random Forest** | Model ML pembanding yang menggabungkan banyak pohon keputusan (*decision trees*). | Slide 6 |
| **ROC-AUC** | Skor (0–1) seberapa baik model membedakan hari butuh siram vs tidak butuh siram (`0,794` = kuat). | Slide 6 |
| **Recall & False Negative (FN)** | **Recall** = persentase hari butuh siram yang berhasil terdeteksi (`97,3%`); **FN** = hari gagal siram (sawah kering tapi model bilang tidak perlu siram). | Slide 6 |
| **Power BI & Import Mode** | Software BI pembuat dashboard; *Import Mode* menyalin 6 tabel ringkas ke RAM Power BI agar filter & grafik sangat cepat. | Slide 4, 8 |
| **DAX** (*Data Analysis Expressions*) | Bahasa rumus di Power BI (mirip rumus Excel) untuk menghitung angka agregat dinamis saat slicer diklik. | Slide 3, 8 |
| **Drill-Through** | Fitur klik kanan satu baris/wilayah di Power BI untuk langsung lompat ke halaman detail khusus wilayah tersebut. | Slide 8 |
| **UU PDP & Model Card** | Aturan privasi data Indonesia (data kita 100% cuaca publik, bebas data pribadi) & dokumentasi batas penggunaan aman model ML. | Slide 10 |
