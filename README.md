# Civitai Grabber

**🇹🇷 Türkçe** · [🇬🇧 English](#-english)

JDownloader mantığıyla çalışan, Civitai için yazılmış PySide6 indirme yöneticisi. Linkleri panodan yakalar, listeler; sen linkleri seçip **gruplara** ayırır, her gruba bir **indirme klasörü** atar ve indirmeyi başlatırsın. Koyu tema varsayılandır.

> JDownloader'ın Civitai'de aldığı *"blocked by Cloudflare protection"* hatasına çözüm olarak yapıldı: istekler tarayıcı benzeri User-Agent ile, düşük eşzamanlılık ve aralarında bekleme ile gönderilir; engel gelirse sıra durdurulur.

## Özellikler

- **Pano izleme:** Civitai model sayfası, `api/download/models/…` veya `model-versions/…` linki kopyalayınca otomatik listeye eklenir (Ctrl+V ile elle, “Link ekle” ile toplu yapıştırma da var).
- **Otomatik çözümleme:** Her link için Civitai API'den model adı, sürüm, **yaratıcı**, tür (LORA/Checkpoint…), dosya adı ve boyut okunur. Model sayfası linki en yeni sürümü, `?modelVersionId=` varsa o sürümü indirir.
- **Gruplama:** Satırları seçip `Ctrl+G` → mevcut gruba ekle ya da yeni grup + klasör oluştur. Satırları sürükleyip soldaki gruba bırakabilirsin. **“Yaratıcıya göre grupla”** her yaratıcı için `AnaKlasör/YaratıcıAdı` klasörlü grup açar.
- **Grup başına klasör**, grup filtresi, sütun sıralama, sağ tık menüsü (taşı, tarayıcıda aç, klasörü aç, yeniden çözümle).
- **Sağlam indirme:** `.part` dosyasından devam etme (Range), otomatik yeniden deneme, duraklat/devam, aynı dosya klasörde zaten varsa kopya oluşturmaz (farklıysa `ad (1).ext` olarak kaydeder), isteğe bağlı SHA256 doğrulama.
- **Dosya türü filtresi:** Ayarlar → İndirme → *Dosya türleri* (varsayılan `safetensors, pt`, sıra = tercih). Sürümde birden çok dosya varsa (ör. `.ckpt` + `.safetensors` + `.zip`) yalnızca izin verilen türden olan indirilir; hiçbiri uymazsa satır hata verir ve sürümdeki dosyaları listeler. Boş bırakırsan her tür iner.
- **Günlük (log):** Araç çubuğundaki **☰ Günlük** düğmesi alttaki günlük panelini açar: her adım (çözümleme, seçilen dosya, HTTP durumu, Cloudflare ayrıntıları, yeniden denemeler, bitiş hızı) yazılır. Seviye ve metin filtresi var; satıra sağ tık → *Bu satırın günlüğünü göster* yalnızca o linkin kayıtlarını gösterir. Hata satırının üzerine gelince (tooltip) HTTP durumu, `cf-ray`, sunucu ve sayfa başlığı görünür. Kayıtlar ayrıca `logs/civitai-grabber.log` dosyasına yazılır (API anahtarı/token asla yazılmaz). Yakalanmamış hatalar da buraya düşer.
- **Cloudflare/giriş hatalarını ayırt eder:** hata satırında nedeni ve çözümü yazar; Cloudflare engeli gelirse kalan sırayı durdurur.
- Koyu (varsayılan) / açık tema, Türkçe / İngilizce arayüz. Liste, gruplar ve ayarlar kapanıp açılınca korunur.

## Kurulum

Python 3.10+ gerekir.

```bash
git clone https://github.com/BuRsTFiRe47/Civitai-Grabber.git
cd Civitai-Grabber
pip install -r requirements.txt
python main.py
```

Windows'ta `run.bat` (ilk çalıştırmada sanal ortam kurar), Linux/macOS'ta `./run.sh` de kullanılabilir.

## Kullanım

1. **Ayarlar → API anahtarı:** [civitai.com](https://civitai.com) → Hesap ayarları → *API Keys* ile oluşturduğun anahtarı gir. (Anahtar yalnızca Civitai'ye giden isteklerde `Authorization` başlığıyla gönderilir, indirme CDN'ine yönlendirmede gönderilmez.)
2. **Pano izleme** açıkken Civitai linklerini kopyala; liste dolar.
3. Linkleri seç → **Grupla…** (`Ctrl+G`) → grup adı + klasör. Ya da **Yaratıcıya göre grupla** (ilk kullanımda ana klasörü sorar).
4. **Seçilenleri başlat** veya soldan bir grup seçip **Görünenleri başlat**.

Klasörü olmayan linkleri başlatırsan varsayılan bir klasör sorulur.

## Cloudflare engeli alırsan

1. Ayarlar → İndirme: eşzamanlı indirmeyi `1`, bekleme süresini `5–10 s` yap.
2. Birkaç dakika bekleyip satırı tekrar başlat.
3. Hâlâ olmuyorsa: tarayıcıda Civitai'yi aç → geliştirici araçlarından `cf_clearance` çerezini ve tarayıcının User-Agent'ını kopyala → Ayarlar → Gelişmiş'e yapıştır. (Çerez IP ve User-Agent'a bağlıdır, süresi dolunca yenilenmelidir.)

## Bilinen sınırlar

- Test ortamında canlı Civitai'ye erişim yoktu: indirme, devam etme, hata ayrımı ve API çözümleme **yerel sahte bir Civitai/Cloudflare sunucusuna karşı** otomatik testlerle (`pytest`) doğrulandı. Gerçek Civitai/Cloudflare davranışı farklı olabilir; sorun görürsen hata metniyle bir *issue* aç.
- Sürüm başına **tek dosya** indirilir (filtreye göre seçilir; ek dosyalar/önizleme görselleri indirilmez). Filtreyi değiştirince eski satırlara uygulamak için sağ tık → *Yeniden çözümle*.
- API anahtarı ve çerez ayar dosyasında düz metin saklanır (`%APPDATA%\CivitaiGrabber\` / `~/.config/civitai-grabber/`).
- Listeden kaldırılan, yarım kalmış `.part` dosyaları silinir.

## GitHub'da derleme (kendi bilgisayarında derlemeden)

`.github/workflows/build.yml` Windows `.exe` paketini GitHub'ın sunucularında derler:

1. Repoyu GitHub'a gönder (`BuRsTFiRe47/Civitai-Grabber`). *Settings → Actions → General* altında Actions açık olmalı.
2. **Elle:** *Actions → Build → Run workflow*. İş bitince sayfanın altındaki **Artifacts → CivitaiGrabber-windows** zip'ini indir, aç, `CivitaiGrabber.exe`'yi çalıştır.
3. **Sürüm olarak:** `git tag v1.0.1 && git push origin v1.0.1` → zip otomatik olarak *Releases* sayfasına eklenir.

İş akışında ayrıca Ubuntu üzerinde testler (`pytest`) çalışır. Derleme tek klasörlük (`onedir`) paket üretir; tek dosya `exe` istersen workflow'daki `pyinstaller` satırına `--onefile` ekle (açılışı yavaşlar, antivirüs daha sık uyarır). İş akışı GitHub'da henüz çalıştırılmadı; ilk çalıştırmada bir hata çıkarsa Actions günlüğünü bir *issue* olarak paylaş.

## Geliştirme

```bash
pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen pytest        # Windows PowerShell: $env:QT_QPA_PLATFORM="offscreen"; pytest
```

Tek exe için (denenmedi): `pip install pyinstaller && pyinstaller --noconsole --name CivitaiGrabber main.py`

## Lisans

MIT — bkz. [LICENSE](LICENSE).

---

## 🇬🇧 English

A PySide6 download manager for Civitai that works like JDownloader: it grabs links from the clipboard and lists them; you select links, put them into **groups**, assign each group a **download folder**, and start. Dark theme is the default.

> Built as an answer to JDownloader's *"blocked by Cloudflare protection"* error on Civitai: requests use a browser-like User-Agent, low concurrency and a delay between starts, and the queue is parked when a block is detected.

### Features

- **Clipboard watch:** copying a Civitai model page, `api/download/models/…` or `model-versions/…` link adds it to the list automatically (Ctrl+V and a bulk “Add links” dialog also work).
- **Automatic resolving:** model name, version, **creator**, type (LORA/Checkpoint…), file name and size are read from the Civitai API. A model-page link downloads the newest version, or the one in `?modelVersionId=`.
- **Grouping:** select rows → `Ctrl+G` → add to an existing group or create a new group + folder. You can also drag rows onto a group on the left. **“Group by creator”** creates a group with folder `BaseFolder/CreatorName` per creator.
- **Per-group folder**, group filter, column sorting, context menu (move, open in browser, open folder, resolve again).
- **Robust downloads:** resume from the `.part` file (Range), automatic retries, pause/resume, does not create a duplicate if the identical file already exists (a different one is saved as `name (1).ext`), optional SHA256 verification.
- **File type filter:** Settings → Downloads → *File types* (default `safetensors, pt`, order = preference). If a version has several files (e.g. `.ckpt` + `.safetensors` + `.zip`) only one of the allowed types is downloaded; if none matches the row errors out and lists the files the version has. Leave it empty to allow any type.
- **Log:** the **☰ Log** toolbar button opens a log panel at the bottom: every step (resolving, chosen file, HTTP status, Cloudflare details, retries, finish speed) is written. It has level and text filters; right-click a row → *Show this row's log* shows only that link's records. Hovering an error row (tooltip) shows the HTTP status, `cf-ray`, server and page title. Records are also written to `logs/civitai-grabber.log` (API key/tokens are never logged). Uncaught errors end up there too.
- **Tells Cloudflare and login errors apart:** the error row explains the cause and remedy; on a Cloudflare block the rest of the queue is parked.
- Dark (default) / light theme, Turkish / English UI. List, groups and settings persist across restarts.

### Install

Python 3.10+ required.

```bash
git clone https://github.com/BuRsTFiRe47/Civitai-Grabber.git
cd Civitai-Grabber
pip install -r requirements.txt
python main.py
```

On Windows you can use `run.bat` (creates a virtual environment on first run); on Linux/macOS `./run.sh`.

### Usage

1. **Settings → API key:** enter the key you created at [civitai.com](https://civitai.com) → Account settings → *API Keys*. (It is sent only to Civitai in an `Authorization` header, never on the redirect to the download CDN.)
2. With **Clipboard watch** on, copy Civitai links; the list fills up.
3. Select links → **Group…** (`Ctrl+G`) → group name + folder. Or **Group by creator** (asks for a base folder the first time).
4. **Start selected**, or pick a group on the left and press **Start shown**.

If you start links that have no folder, you are asked for a default folder.

### If you get blocked by Cloudflare

1. Settings → Downloads: set concurrent downloads to `1` and the delay to `5–10 s`.
2. Wait a few minutes and start the row again.
3. Still blocked: open Civitai in your browser, copy the `cf_clearance` cookie and the browser's User-Agent from the dev tools, and paste them into Settings → Advanced. (The cookie is bound to your IP and User-Agent and expires.)

### Known limitations

- The build environment had no access to live Civitai: downloading, resuming, error classification and API resolving were verified by automated tests (`pytest`) **against a local fake Civitai/Cloudflare server**. Real Civitai/Cloudflare behaviour may differ; if you hit a problem, open an *issue* with the error text.
- One **file per version** is downloaded (chosen by the filter; no extra files / preview images). After changing the filter, use right-click → *Resolve again* on existing rows.
- The API key and cookie are stored as plain text in the settings file (`%APPDATA%\CivitaiGrabber\` / `~/.config/civitai-grabber/`).
- Removing an unfinished item from the list deletes its `.part` file.

### Building on GitHub (instead of on your own PC)

`.github/workflows/build.yml` builds the Windows `.exe` package on GitHub's servers:

1. Push the repo to GitHub (`BuRsTFiRe47/Civitai-Grabber`). Actions must be enabled under *Settings → Actions → General*.
2. **By hand:** *Actions → Build → Run workflow*. When it finishes, download **Artifacts → CivitaiGrabber-windows** at the bottom of the run page, unzip it and run `CivitaiGrabber.exe`.
3. **As a release:** `git tag v1.0.1 && git push origin v1.0.1` → the zip is attached to the *Releases* page automatically.

The workflow also runs the tests (`pytest`) on Ubuntu. The build produces a one-folder (`onedir`) package; for a single-file `exe` add `--onefile` to the `pyinstaller` line (slower start-up, more antivirus warnings). The workflow has not been run on GitHub yet; if the first run fails, share the Actions log in an *issue*.

### Development

```bash
pip install -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen pytest        # Windows PowerShell: $env:QT_QPA_PLATFORM="offscreen"; pytest
```

Single exe (untested): `pip install pyinstaller && pyinstaller --noconsole --name CivitaiGrabber main.py`

### License

MIT — see [LICENSE](LICENSE).
