# Changelog / Değişiklik günlüğü

## 1.0.9 — 2026-11-23

- **TR:** **Grupları sırala:** gruplar sürükle-bırakla yukarı/aşağı taşınır (çizgi ekleme yerini gösterir); sol paneldeki **▲ ▼** düğmeleri seçili grubu bir basamak taşır; **A→Z** tüm grupları ada göre dizer (büyük/küçük harf fark etmez, `Pack 2` `Pack 10`'dan önce gelir). Sağ tık menüsünde *Sırala* alt menüsü (en üste/yukarı/aşağı/en alta) ve A→Z de var. Sıra kaydedilir. Satırları gruba bırakmak eskisi gibi çalışır.
- **EN:** **Re-order groups:** drag & drop groups up/down (a line shows the insertion point); the **▲ ▼** buttons under the group list move the selected group one step; **A→Z** sorts all groups by name (case-insensitive, natural numbers: `Pack 2` before `Pack 10`). The right-click menu has an *Order* submenu (top/up/down/bottom) and A→Z too. The order is saved. Dropping rows onto a group still works as before.
- Includes everything from 1.0.8 (system tray options) if it was not published yet.

## 1.0.8 — 2026-11-17

- **TR:** **Sistem tepsisi (isteğe bağlı):** Ayarlar → Genel'de iki seçenek: *Küçültünce tepsiye gizle* ve *Kapatınca (X) çıkma, tepsiye gizle*. Tepsideki simge uygulamayla aynıdır; üzerine gelince kaç dosyanın indiği ve toplam hız görünür, tıklayınca pencere açılıp kapanır, sağ tık → *Çık* ile tamamen çıkılır. Varsayılan: kapalı. Tepsi olmayan sistemlerde pencere normal kapanır.
- **TR:** Uygulama, görev çubuğu ve pencere simgeleri tek kaynaktan çiziliyor; ilk açılışta simge görünmüyorsa uygulamayı yeni sürümle derleyip eski görev çubuğu kısayolunu çözüp yeniden sabitle (Windows eski simgeyi önbellekte tutar).
- **EN:** **System tray (optional):** two options in Settings → General: *Hide in the tray when minimized* and *Hide in the tray instead of quitting when closed (X)*. The tray icon is the same as the app icon; hover shows how many files are downloading and the total speed, click shows/hides the window, right-click → *Quit* exits completely. Off by default. Without a system tray the window closes normally.
- **EN:** App, taskbar and window icons are drawn from one source; if you still see the old icon after rebuilding, unpin the old taskbar shortcut and pin again (Windows caches icons).

## 1.0.7 — 2026-11-13

- **TR:** Görev çubuğu simgesi: uygulama artık kendi simgesiyle (mercan zemin, beyaz indirme oku) görünür; exe dosyasına da gömülü (`assets/icon.ico`) ve Windows'ta kendi görev çubuğu kimliğiyle açılır, böylece diğer Python/başlatıcı pencerelerinden ayırt edilir. Simgeyi yeniden üretmek için `python tools/make_icon.py`.
- **TR:** Cloudflare engelinden sonra sıradaki indirmenin bekleme süresi 15 sn → **6 sn**.
- **EN:** Taskbar icon: the app now shows its own icon (coral tile, white download arrow), embedded in the exe too (`assets/icon.ico`), and starts with its own Windows taskbar identity so it is no longer grouped with other Python/launcher windows. Regenerate with `python tools/make_icon.py`.
- **EN:** Wait after a Cloudflare block before the next download: 15 s → **6 s**.

## 1.0.6 — 2026-11-10

- **TR:** Tabloya **Temel model** sütunu eklendi (SDXL 1.0, Pony, Illustrious, SD 1.5 …); Civitai'nin bildirdiği değer gösterilir, sütuna tıklayarak sıralayabilirsin. Eski kayıtlı satırlarda da görünür.
- **EN:** Added a **Base model** column to the table (SDXL 1.0, Pony, Illustrious, SD 1.5 …), as reported by Civitai; click the header to sort. Also shows for rows saved earlier.

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
