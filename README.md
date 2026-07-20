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

## Higgsfield animasyon entegrasyonu

### Sağlayıcı bağımsız video motoru

Pipeline doğrudan bir video firmasına bağlı değildir. Tüm video motorları
`animation.provider.VideoProvider` arayüzünü uygular ve
`animation.factory.create_video_provider` üzerinden seçilir.

Setup sırasında seçim `.env` dosyasındaki tek ayarla yapılır:

```dotenv
VIDEO_PROVIDER=none
```

Mevcut seçenekler:

- `none`: animasyon motorunu kapatır ve mevcut slayt fallback sistemini kullanır.
- `higgsfield`: mevcut Higgsfield CLI adaptörünü kullanır.
- `runway`: Runway Gen-4 Turbo image-to-video adaptörünü kullanır.

Runway, Veo, doğrudan Kling veya gelecekteki başka bir motor eklenirken yalnızca
yeni bir `VideoProvider` adaptörü ve factory kaydı gerekir; hikâye, ses, montaj
ve YouTube pipeline'ı değiştirilmez. Eski kurulumlar için
`ENABLE_HIGGSFIELD=true`, `VIDEO_PROVIDER` tanımlı değilse Higgsfield seçimine
eşlenmeye devam eder.

### Runway Gen-4 Turbo

İlk Runway aşaması yalnızca sessiz, 5 saniyelik, 720p image-to-video üretimini
destekler. Act-Two, lip sync, Veo ve uzun video henüz bağlı değildir.

```dotenv
VIDEO_PROVIDER=runway
RUNWAY_API_KEY=
RUNWAY_MODEL=gen4_turbo
RUNWAY_RATIO=1280:720
RUNWAY_DURATION=5
RUNWAY_POLL_INTERVAL=5
RUNWAY_TIMEOUT=600
RUNWAY_MAX_RETRIES=3
```

Tek Leo–Scout test sahnesi:

```powershell
python scripts/test_runway_video.py
```

Anahtar boşsa script API çağrısı yapmadan açıklayıcı hata ile durur. Başarılı
çıktı `output/runway_test/leo_scout_scene_01.mp4` yoluna kaydedilir. Runway
Gen-4 Turbo 5 kredi/saniye, kredi başına $0,01 olduğundan 5 saniyelik testin
tahmini taban maliyeti $0,25'tir. Başarısız animasyon sahnelerinde mevcut
slayt fallback sistemi kullanılmaya devam eder.

Proje, Higgsfield'ın resmî ve Windows destekli CLI paketini kullanır. CLI,
Higgsfield hesabına tarayıcı üzerinden giriş yapar; `HIGGSFIELD_API_KEY` veya
özel bir REST endpoint gerekmez.

Windows PowerShell kurulumu:

```powershell
npm.cmd install -g @higgsfield/cli@latest
higgsfield.cmd version
higgsfield.cmd auth login
higgsfield.cmd model list
```

PowerShell yürütme ilkesi `.ps1` başlatıcılarını engelliyorsa `.cmd` uzantısını
kullanmak, ilkeyi gevşetmeden npm'in Windows başlatıcısını doğrudan çalıştırır.

Her sahne için `image_path`, `animation_prompt`, `duration`, `camera_motion` ve
`output_video` alanları korunur. `animation/higgsfield_service.py`, bunları
resmî komut biçimine dönüştürür:

```text
higgsfield generate create kling3_0 --prompt "..." --start-image "..." --duration 5 --wait --json
```

`camera_motion`, tüm modellerde ortak bir CLI bayrağı olmadığı için prompt
içine eklenir. Resmî CLI tamamlandığında sonuç URL'sini döndürür; belgelenmemiş
bir `--output` bayrağı kullanılmaz.

Varsayılan ve geriye uyumlu ayarlar:

```dotenv
HIGGSFIELD_MODEL=kling3_0
HIGGSFIELD_OUTPUT_DIR=data/animations
HIGGSFIELD_CLI_COMMAND=higgsfield
ENABLE_HIGGSFIELD=false
HIGGSFIELD_DRY_RUN=true
```

Dry-run için `ENABLE_HIGGSFIELD=true` bırakıp çalıştırın:

```powershell
python generate_video.py
```

Bu mod yalnızca resmî CLI komutlarını yazdırır; CLI çalışmaz, kredi harcanmaz.
Mevcut statik görsel + FFmpeg pipeline'ı önce çalışmaya devam eder. Gerçek
Higgsfield üretimini daha sonra bilinçli olarak açmak için:

```dotenv
ENABLE_HIGGSFIELD=true
HIGGSFIELD_DRY_RUN=false
```

Oturum süresi dolarsa `higgsfield.cmd auth login` komutunu tekrar çalıştırın. Model
adı geçersizse güncel değerleri `higgsfield model list` ile kontrol edin.

## Kids Shorts AŞAMA 1 — anahtarsız demo

Yeni AŞAMA 1 akışı, mevcut belgesel ve animasyon pipeline'ını değiştirmeden
ayrı `app/` paketi altında çalışır. Dış servise bağlanmaz ve API anahtarı
istemez. Tam olarak 6 sahneli, 25–35 saniyelik İngilizce çocuk hikâyesini
Pydantic ile doğrular; Character Bible tanımını bütün görsel promptlarında
değişmeden kullanır ve sonucu hem JSON hem SQLite olarak kaydeder.

Windows PowerShell kurulumu:

```powershell
cd "C:\Users\Semih\Desktop\otomasyon"
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Testler:

```powershell
python -m pytest -q -p no:cacheprovider
```

Anahtarsız demo:

```powershell
python scripts\generate_story.py
```

Tekrarlanabilir bir örnek:

```powershell
python scripts\generate_story.py --seed 42
```

Kategori ve süre seçimi:

```powershell
python scripts\generate_story.py --category animal_rescue --duration 30
```

Her çalıştırma aşağıdaki paketi oluşturur:

```text
output/episode_0001/
├── story.json
├── character_bible.json
└── metadata.json
```

SQLite veritabanı `data/kids_shorts.db` konumundadır. Demo yalnızca hikâye
paketi üretir; video oluşturmaz, API çağrısı yapmaz ve YouTube'a yüklemez.
Onay durumu varsayılan olarak `pending` kalır.

## Kids Shorts AŞAMA 2 — yerel demo MP4

AŞAMA 2, AŞAMA 1 hikâyesinden tamamen yerel olarak 1080x1920, 30 FPS,
H.264/AAC bir demo Shorts videosu üretir. Placeholder görseller Pillow ile,
hareket ve final montaj FFmpeg ile, anlatım Microsoft Zira ile, müzik ve
efektler Python ile sentezlenir. İnternetten medya indirilmez ve API anahtarı
kullanılmaz.

Önkoşul:

```powershell
winget install --id Gyan.FFmpeg -e
```

Kurulumdan sonra VS Code terminalini yeniden açın:

```powershell
ffmpeg -version
ffprobe -version
ffmpeg -hide_banner -filters | Select-String "ass|subtitles"
```

Mevcut bir episode için:

```powershell
python scripts\generate_demo_video.py --episode episode_0002
```

Yeni hikâye ve video birlikte:

```powershell
python scripts\generate_demo_video.py --create-story --seed 42
```

Kategori ve süre seçerek:

```powershell
python scripts\generate_demo_video.py --create-story --category animal_rescue --duration 30
```

Çıktı:

```text
output/episode_xxxx/
├── story.json
├── character_bible.json
├── metadata.json
├── images/
│   └── scene_01.png ... scene_06.png
├── clips/
│   └── scene_01.mp4 ... scene_06.mp4
├── audio/
│   ├── narration.wav
│   ├── music.wav
│   ├── effects.wav
│   ├── sound_effects.json
│   └── final_mix.wav
├── subtitles/
│   ├── subtitles.srt
│   └── subtitles.ass
├── final_short.mp4
└── quality_report.json
```

Video yalnızca yerelde oluşturulur. `approval_status=pending` ve
`upload_status=not_ready` olarak kalır.
