# Changelog / Değişiklik günlüğü

## 1.0.5 — 2026-11-09

### Türkçe

**Yeni**
- **Hız sınırı:** durum çubuğundan (Sınırsız, 0,5–50 MB/s) veya Ayarlar → İndirme'den; tüm indirmelerin toplamına uygulanır, indirme sürerken değişir.
- **Sürükle-bırak sıra:** satırları başka bir satırın üstüne/altına bırakarak indirme sırasını değiştir.
- **Tüm sürümler:** sürümsüz model linki (`?` öncesi) modelin tüm sürümlerini ekler; `?modelVersionId=` varsa yalnızca o sürüm. Ayarlardan kapatılabilir.
- **Pratik klasör seçimi:** yeni grup açarken klasör otomatik `ana klasör\grup adı` olur; ana klasör yoksa en son kullandığın konum kullanılır. Yanındaki ▾ ile son 8 konumdan birini seçebilirsin, “Gözat…” da (olmayan klasörde bile) en yakın var olan klasörden açılır. Elle seçtiğin klasör, ad değişince ezilmez.
- **“Atlandı (zaten var)” durumu:** hedef klasörde dosya zaten varsa satır “Bitti” yerine sarı renkte **Atlandı (zaten var)** yazar (üzerine gelince dosya yolu görünür).
- **Buzz / erken erişim ayrımı:** erken erişimdeki sürümler işaretlenir (satırın üstüne gelince bitiş tarihi) ve reddedilirse hata “Cloudflare engeli” yerine **Buzz gerekiyor (erken erişim)** olarak gösterilir; Cloudflare bekleme süresi de devreye girmez.
- **Breeze teması:** arduvaz zemin + mercan vurgu (koyu varsayılan, açık tema da var), özel onay kutusu ve açılır menü oku.
- **Zaten varsa atla** (aynı ad + aynı boyut), **hata sırayı durdurmaz** (Cloudflare'de 15 sn bekleyip devam; istersen "sırayı durdur" ayarı), **yukarı/aşağı sıralama** (▲/▼, `Alt+↑/↓`), **Bitince hazırda beklet / kapat** (60 sn iptal edilebilir geri sayım).
- Dosya türü filtresi (`safetensors, pt`), günlük paneli, taşınabilir `config` klasörü (AppData'dan otomatik taşıma), GitHub Actions ile derleme.

**Değişti / düzeltildi**
- Yarım indirmeler `ad.<sürümId>.part` adıyla tutulur (aynı adlı dosyalar çakışmaz). Eski sürümün adsız `.part` dosyaları devam etmez, baştan iner.
- 2 GB üzeri dosyalarda görülen `OverflowError` giderildi.
- Günlük paneli ve çalışan iş parçacıklarından kaynaklanan rastgele çökme riski giderildi.

### English

**New**
- **Speed limit:** status-bar menu (Unlimited, 0.5–50 MB/s) or Settings → Downloads; applies to all downloads together and changes live.
- **Drag & drop order:** drop rows above/below another row to re-order the queue.
- **All versions:** a model link without a version (everything before the `?`) adds every version of the model; with `?modelVersionId=` only that version. Can be turned off in Settings.
- **Quicker folder picking:** a new group's folder is filled in as `base folder\group name`; without a base folder the location you used last is taken. The ▾ next to it lists your last 8 locations, and “Browse…” opens at the nearest existing folder. A folder you picked by hand is no longer overwritten when the name changes.
- **“Skipped (already there)” status:** when the file already exists the row says **Skipped (already there)** in amber instead of “Done” (hover shows the file path).
- **Buzz / early access told apart:** early-access versions are flagged (hover shows the end date) and when refused the error reads **Buzz required (early access)** instead of “Cloudflare block”; no Cloudflare back-off is applied.
- **Breeze theme:** slate background + coral accent (dark default, light available), custom checkbox and combo chevron.
- **Skip if exists** (same name + size), **errors don't stop the queue** (15 s wait then continue on Cloudflare; optional "stop queue" setting), **move up/down** (▲/▼, `Alt+↑/↓`), **When done: hibernate / shut down** (60 s cancellable countdown).
- File type filter (`safetensors, pt`), log panel, portable `config` folder (automatic migration from AppData), GitHub Actions build.

**Changed / fixed**
- Partial downloads are kept as `name.<versionId>.part` (same-named files no longer collide). Unnamed `.part` files from older versions are not resumed.
- Fixed the `OverflowError` seen with files over 2 GB.
- Fixed a rare crash risk involving the log panel and worker threads.
