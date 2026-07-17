# YouTube Otomasyon MVP

Bu proje, tek niş altında 5–10 dakikalık kısa belgesel videoları hazırlamak için
güvenli bir başlangıç sistemidir. İlk sürüm hiçbir ücretli yapay zekâ servisine
bağlanmaz ve YouTube'a otomatik yükleme yapmaz.

## Sistem ne yapıyor?

1. Hazır konu havuzundan konu seçer.
2. Test senaryosu, başlık, açıklama ve etiket üretir.
3. Senaryoyu sahnelere böler.
4. Her sahne için test görseli ve sessiz test sesi üretir.
5. Bilgisayarda FFmpeg varsa parçaları MP4 videoda birleştirir.
6. Kapak görseli hazırlar.
7. Tüm çıktıları ayrı proje klasöründe toplar.
8. Yayından önce insan onayı ister. Onay verilse bile bu MVP YouTube'a yüklemez.

## 1. Gerekenler

- Windows 10 veya 11
- Python 3.11 ya da daha yeni bir sürüm
- İsteğe bağlı: FFmpeg (MP4 oluşturmak için)

Önce PowerShell'i açın ve proje klasörüne girin:

```powershell
cd "C:\Users\Semih\Documents\Codex\2026-07-17\referenced-chatgpt-conversation-this-is-untrusted-2\youtube-otomasyon"
```

Python kurulu mu kontrol edin:

```powershell
python --version
```

## 2. Güvenli sanal ortamı oluşturun

```powershell
python -m venv .venv
```

Etkinleştirin:

```powershell
.\.venv\Scripts\Activate.ps1
```

PowerShell izin uyarısı verirse yalnızca bu pencere için şu komutu çalıştırıp
etkinleştirme komutunu tekrar deneyin:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 3. Gerekli paketleri kurun

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

İndirme yavaşsa komut birkaç dakika sürebilir. Tamamlandığında PowerShell
satırının yeniden görünmesini bekleyin.

## 4. Ayar dosyasını oluşturun

```powershell
Copy-Item .env.example .env
```

İlk testte `.env` dosyasını değiştirmeniz gerekmez. Anahtarlar boş, YouTube
yüklemesi kapalı kalmalıdır.

## 5. Paneli açın

```powershell
python -m streamlit run app.py
```

Tarayıcı otomatik açılmazsa PowerShell'de gösterilen yerel adresi (genellikle
`http://localhost:8501`) tarayıcıya yazın. Konuyu ve süreyi seçip
**Test videosu paketini üret** düğmesine basın.

## Panelsiz hızlı test

```powershell
python run_demo.py
```

## Testleri çalıştırın

```powershell
python -m pytest
```

## Çıktılar nerede?

Her çalışma şurada yeni bir klasör oluşturur:

```text
data/projects/TARIH-SAAT-konu/
├── approval_status.json
├── audio/
├── clips/                 # FFmpeg varsa
├── final_video.mp4        # FFmpeg varsa
├── metadata.json
├── scenes/
├── script.txt
└── thumbnail.png
```

## Modüler yapı

- `src/providers/content.py`: senaryo ve metadata sağlayıcısı
- `src/providers/voice.py`: seslendirme sağlayıcısı
- `src/providers/media.py`: görsel/video sağlayıcısı
- `src/video.py`: FFmpeg birleştirme
- `src/youtube_upload.py`: varsayılan kapalı yükleme güvenlik kapısı

Gerçek servisler daha sonra aynı temel sınıflardan yeni sağlayıcılar eklenerek
bağlanabilir. API anahtarları yalnızca `.env` içinde tutulmalı; `.env` Git'e
eklenmez.

## Önemli güvenlik ve kalite notları

- Test metinleri doğrulanmış bilgi kaynağı değildir.
- Yayından önce olguları ve kaynakları insan kontrol etmelidir.
- Telifli karakter, görüntü, müzik veya başkasının videosu kullanılmamalıdır.
- Çocuklara özel içerik seçilirse YouTube'un çocuk içeriği ayarları ayrıca
  uygulanmalıdır.
- Finans, sigorta, sağlık ve hukuk konularında güncel uzman kontrolü olmadan
  yayın yapılmamalıdır.
- `YOUTUBE_UPLOAD_ENABLED=false` varsayılan ayardır. Mevcut modül gerçek yükleme
  kodu içermez; yanlışlıkla yayın yapamaz.

## Sonraki güvenli geliştirme sırası

1. Seçilen nişi kesinleştirme ve 50–100 doğrulanabilir konu ekleme.
2. Kaynak URL'lerini ve kaynak kontrol ekranını ekleme.
3. Gerçek metin, ses ve görsel sağlayıcılarından yalnızca birer tane bağlama.
4. Maliyet limiti ve günlük üretim limiti koyma.
5. YouTube Data API'yi ayrı modül olarak ekleme; varsayılanı kapalı tutma.
6. Gerçek yüklemede iki aşamalı insan onayı ve önce `private` görünürlük kullanma.
