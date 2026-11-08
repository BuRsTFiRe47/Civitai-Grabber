# Civitai Grabber

**🇹🇷 Türkçe** · [🇬🇧 English](#-english)

JDownloader mantığıyla çalışan, Civitai için yazılmış PySide6 indirme yöneticisi. Linkleri panodan yakalar, listeler; sen linkleri seçip **gruplara** ayırır, her gruba bir **indirme klasörü** atar ve indirmeyi başlatırsın. Koyu tema varsayılandır.

> JDownloader'ın Civitai'de aldığı *"blocked by Cloudflare protection"* hatasına çözüm olarak yapıldı: istekler tarayıcı benzeri User-Agent ile, düşük eşzamanlılık ve aralarında bekleme ile gönderilir; engel gelirse sıra durdurulur.

## Özellikler

- **Pano izleme:** Civitai model sayfası, `api/download/models/…` veya `model-versions/…` linki kopyalayınca otomatik listeye eklenir (Ctrl+V ile elle, “Link ekle” ile toplu yapıştırma da var).
- **Otomatik çözümleme:** Her link için Civitai API'den model adı, sürüm, **yaratıcı**, tür (LORA/Checkpoint…), dosya adı ve boyut okunur. Sürümü belirtilmemiş model linki (`civitai.com/models/123/ad`, `?` işaretinden öncesi) modelin **tüm sürümlerini** listeye ekler (ör. bir yaratıcının kıyafet koleksiyonu); `?modelVersionId=` varsa yalnızca o sürüm eklenir. Ayarlar → İndirme'den kapatılabilir (kapalıyken yalnızca en yeni sürüm).
- **Gruplama:** Satırları seçip `Ctrl+G` → mevcut gruba ekle ya da yeni grup + klasör oluştur. Satırları sürükleyip soldaki gruba bırakabilirsin. **“Yaratıcıya göre grupla”** her yaratıcı için `AnaKlasör/YaratıcıAdı` klasörlü grup açar.
- **Pratik klasör seçimi:** grup klasörü otomatik `ana klasör\grup adı` önerilir (ana klasör yoksa en son kullanılan konum); ▾ düğmesiyle son 8 konumdan seçilir, “Gözat…” en yakın var olan klasörden açılır.
- **Grup başına klasör**, grup filtresi, sütun sıralama, sağ tık menüsü (taşı, tarayıcıda aç, klasörü aç, yeniden çözümle).
- **Sağlam indirme:** `.part` dosyasından devam etme (Range), otomatik yeniden deneme, duraklat/devam, aynı dosya klasörde zaten varsa kopya oluşturmaz (farklıysa `ad (1).ext` olarak kaydeder), isteğe bağlı SHA256 doğrulama.
- **Dosya türü filtresi:** Ayarlar → İndirme → *Dosya türleri* (varsayılan `safetensors, pt`, sıra = tercih). Sürümde birden çok dosya varsa (ör. `.ckpt` + `.safetensors` + `.zip`) yalnızca izin verilen türden olan indirilir; hiçbiri uymazsa satır hata verir ve sürümdeki dosyaları listeler. Boş bırakırsan her tür iner.
- **Günlük (log):** Araç çubuğundaki **☰ Günlük** düğmesi alttaki günlük panelini açar: her adım (çözümleme, seçilen dosya, HTTP durumu, Cloudflare ayrıntıları, yeniden denemeler, bitiş hızı) yazılır. Seviye ve metin filtresi var; satıra sağ tık → *Bu satırın günlüğünü göster* yalnızca o linkin kayıtlarını gösterir. Hata satırının üzerine gelince (tooltip) HTTP durumu, `cf-ray`, sunucu ve sayfa başlığı görünür. Kayıtlar ayrıca `logs/civitai-grabber.log` dosyasına yazılır (API anahtarı/token asla yazılmaz). Yakalanmamış hatalar da buraya düşer.
- **Cloudflare/giriş hatalarını ayırt eder:** hata satırında nedeni ve çözümü yazar.
- **Zaten varsa atlar:** hedef klasörde aynı adlı ve aynı boyutlu dosya varsa indirme yapılmaz, satır *Bitti* olur (Ayarlar → İndirme → *Zaten varsa atla*, varsayılan açık). Yarım indirmeler `ad.<sürümId>.part` olarak tutulur; eski sürümün adsız `.part` dosyaları devam ettirilemez.
- **Durum ayrımı:** zaten var olan dosya **Atlandı (zaten var)** olarak görünür. Erken erişimdeki (Buzz isteyen) sürümler reddedilirse **Buzz gerekiyor** denir; bu Cloudflare engeli değildir, Civitai'de Buzz ile açıp satırı yeniden başlat veya erken erişimin bitmesini bekle.
- **Hata sırayı durdurmaz:** bir dosya hata verirse sıradaki dosyaya geçilir. Cloudflare engelinde sıradaki indirme 15 sn bekletilip devam edilir; istersen Ayarlar → *Cloudflare'de sırayı durdur* ile kalan sırayı beklemeye alabilirsin.
- **Hız sınırı:** durum çubuğundaki **Hız sınırı** menüsünden (Sınırsız, 0,5–50 MB/s) ya da Ayarlar → İndirme'den ayarla; tüm eşzamanlı indirmelerin toplamına uygulanır ve indirme sürerken de değişir.
- **Sürükle-bırak sıra:** satırları tutup başka bir satırın üstüne/altına bırakarak sırayı değiştir (çizgi ekleme yerini gösterir). Gruba atamak için aynı satırları soldaki gruba bırakmaya devam edebilirsin.
- **Sırayı değiştir:** indirirken de satırları yukarı/aşağı taşı: araç çubuğunda ▲/▼, `Alt+↑/↓`; en üste/alta için `Ctrl+Alt+↑/↓`; sağ tık → *Sırala*. İndirme sırası listedeki sıradır.
- **Bitince kapat:** durum çubuğundaki **Bitince** menüsü: *Hiçbir şey yapma / Hazırda beklet / Kapat*. Tüm indirmeler bitince 60 sn geri sayım gösterilir, **İptal** ile vazgeçilir. Seçim her açılışta “Hiçbir şey yapma”ya döner. Windows'ta hazırda bekletme için `powercfg /hibernate on` gerekebilir; kapatma açık kaydedilmemiş uygulamalarca engellenebilir (`/f` kullanılmaz). macOS'ta “hazırda beklet” uykuya alır.
- Koyu (varsayılan) / açık tema (KDE Breeze esinli arduvaz + mercan), Türkçe / İngilizce arayüz. Liste, gruplar ve ayarlar kapanıp açılınca korunur.

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

## Ayarlar nerede saklanır?

Taşınabilir: ayarlar, liste, gruplar ve günlük **exe'nin yanındaki `config` klasöründe** durur (`config/settings.json`, `config/state.json`, `config/logs/`). Klasörü kopyalayarak uygulamayı başka yere taşıyabilirsin. Ayarlar penceresinin altında klasörün yolu yazar.

- **Eski sürümden geçiş:** önceki sürümler verileri `%APPDATA%\CivitaiGrabber\` (Linux: `~/.config/civitai-grabber/`) altında tutuyordu. Yeni sürüm ilk açılışta, `config` klasöründe henüz veri yoksa, oradaki `settings.json`, `state.json` ve `logs` klasörünü **exe'nin yanına taşır**, kopyaları doğruladıktan sonra eski klasörü siler. Tanımadığı bir dosya varsa o dosyaya ve klasöre dokunmaz. Taşıma hata verirse eski veri olduğu gibi kalır ve bir sonraki açılışta tekrar denenir. Yapılanlar günlüğe yazılır.
- `config` klasörü zaten doluysa eski klasöre dokunulmaz.
- Exe klasörüne yazılamıyorsa (ör. `Program Files`) eski konum kullanılmaya devam eder.
- `CIVITAI_GRABBER_HOME` ortam değişkeni her şeyi geçersiz kılar ve başka bir klasör seçmeni sağlar.

## Bilinen sınırlar

- Test ortamında canlı Civitai'ye erişim yoktu: indirme, devam etme, hata ayrımı ve API çözümleme **yerel sahte bir Civitai/Cloudflare sunucusuna karşı** otomatik testlerle (`pytest`) doğrulandı. Gerçek Civitai/Cloudflare davranışı farklı olabilir; sorun görürsen hata metniyle bir *issue* aç.
- Sürüm başına **tek dosya** indirilir (filtreye göre seçilir; ek dosyalar/önizleme görselleri indirilmez). Filtreyi değiştirince eski satırlara uygulamak için sağ tık → *Yeniden çözümle*.
- API anahtarı ve çerez `config/settings.json` içinde düz metin saklanır; bu dosyayı paylaşma, GitHub'a yükleme (`config/` zaten `.gitignore`'da).
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

## Sürüm geçmişi

Bkz. [CHANGELOG.md](CHANGELOG.md).

## Lisans

MIT — bkz. [LICENSE](LICENSE).

---

## 🇬🇧 English

A PySide6 download manager for Civitai that works like JDownloader: it grabs links from the clipboard and lists them; you select links, put them into **groups**, assign each group a **download folder**, and start. Dark theme is the default.

> Built as an answer to JDownloader's *"blocked by Cloudflare protection"* error on Civitai: requests use a browser-like User-Agent, low concurrency and a delay between starts, and the queue backs off when a block is detected.

### Features

- **Clipboard watch:** copying a Civitai model page, `api/download/models/…` or `model-versions/…` link adds it to the list automatically (Ctrl+V and a bulk “Add links” dialog also work).
- **Automatic resolving:** model name, version, **creator**, type (LORA/Checkpoint…), file name and size are read from the Civitai API. A model link without a version (`civitai.com/models/123/name`, i.e. everything before the `?`) adds **every version** of the model (e.g. a creator's outfit collection); with `?modelVersionId=` only that version is added. Can be switched off in Settings → Downloads (then only the newest version is added).
- **Grouping:** select rows → `Ctrl+G` → add to an existing group or create a new group + folder. You can also drag rows onto a group on the left. **“Group by creator”** creates a group with folder `BaseFolder/CreatorName` per creator.
- **Quick folder picking:** the group folder is suggested as `base folder\group name` (or the location used last); the ▾ button lists your last 8 locations and “Browse…” opens at the nearest existing folder.
- **Per-group folder**, group filter, column sorting, context menu (move, open in browser, open folder, resolve again).
- **Robust downloads:** resume from the `.part` file (Range), automatic retries, pause/resume, does not create a duplicate if the identical file already exists (a different one is saved as `name (1).ext`), optional SHA256 verification.
- **File type filter:** Settings → Downloads → *File types* (default `safetensors, pt`, order = preference). If a version has several files (e.g. `.ckpt` + `.safetensors` + `.zip`) only one of the allowed types is downloaded; if none matches the row errors out and lists the files the version has. Leave it empty to allow any type.
- **Log:** the **☰ Log** toolbar button opens a log panel at the bottom: every step (resolving, chosen file, HTTP status, Cloudflare details, retries, finish speed) is written. It has level and text filters; right-click a row → *Show this row's log* shows only that link's records. Hovering an error row (tooltip) shows the HTTP status, `cf-ray`, server and page title. Records are also written to `logs/civitai-grabber.log` (API key/tokens are never logged). Uncaught errors end up there too.
- **Tells Cloudflare and login errors apart:** the error row explains the cause and remedy.
- **Skips what you already have:** if a file with the same name and size is in the target folder nothing is downloaded and the row becomes *Done* (Settings → Downloads → *Skip if exists*, on by default). Partial downloads are kept as `name.<versionId>.part`; the unnamed `.part` files of older versions cannot be resumed.
- **Clear statuses:** an existing file shows **Skipped (already there)**. Early-access versions (needing Buzz) that get refused say **Buzz required**; this is not a Cloudflare block: unlock it on Civitai with Buzz and restart the row, or wait for early access to end.
- **Errors don't stop the queue:** when a file fails the next one carries on. On a Cloudflare block the next download waits 15 s and continues; optionally Settings → *Stop queue on Cloudflare* parks the rest instead.
- **Speed limit:** from the **Speed limit** status-bar menu (Unlimited, 0.5–50 MB/s) or Settings → Downloads; applies to all concurrent downloads together and takes effect mid-download.
- **Drag & drop order:** drag rows onto another row to re-order the queue (a line shows the insertion point). Dragging the same rows onto a group on the left still assigns them to it.
- **Reorder the queue:** also while downloading: ▲/▼ in the toolbar, `Alt+↑/↓`, `Ctrl+Alt+↑/↓` for top/bottom, right-click → *Order*. Download order is the list order.
- **When done:** status-bar **When done** menu: *Do nothing / Hibernate / Shut down*. After all downloads finish a 60 s countdown appears, **Cancel** aborts it. The choice resets to “Do nothing” at every start. On Windows hibernation may need `powercfg /hibernate on`; shutdown can be blocked by apps with unsaved work (no `/f`). On macOS “hibernate” means sleep.
- Dark (default) / light theme (KDE Breeze inspired: slate + coral), Turkish / English UI. List, groups and settings persist across restarts.

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

### Where settings are stored

Portable: settings, list, groups and the log live **in a `config` folder next to the exe** (`config/settings.json`, `config/state.json`, `config/logs/`). Copy the folder to move the app elsewhere. The Settings window shows the folder path at the bottom.

- **Migration from older versions:** earlier versions kept data under `%APPDATA%\CivitaiGrabber\` (Linux: `~/.config/civitai-grabber/`). On first start, if `config` has no data yet, the new version **moves** `settings.json`, `state.json` and `logs` from there **next to the exe**, verifies the copies and then deletes the old folder. If it finds a file it does not know, it leaves that file and the folder alone. If the move fails the old data stays untouched and it is retried on the next start. Everything is written to the log.
- If `config` already has data the old folder is not touched.
- If the exe folder is not writable (e.g. `Program Files`) the old location keeps being used.
- The `CIVITAI_GRABBER_HOME` environment variable overrides everything and lets you pick another folder.

### Known limitations

- The build environment had no access to live Civitai: downloading, resuming, error classification and API resolving were verified by automated tests (`pytest`) **against a local fake Civitai/Cloudflare server**. Real Civitai/Cloudflare behaviour may differ; if you hit a problem, open an *issue* with the error text.
- One **file per version** is downloaded (chosen by the filter; no extra files / preview images). After changing the filter, use right-click → *Resolve again* on existing rows.
- The API key and cookie are stored as plain text in `config/settings.json`; do not share it or upload it to GitHub (`config/` is already in `.gitignore`).
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

### Changelog

See [CHANGELOG.md](CHANGELOG.md).

### License

MIT — see [LICENSE](LICENSE).
