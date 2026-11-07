"""Tiny TR/EN translation layer. Turkish is the default."""
from __future__ import annotations

_lang = "tr"

TR: dict[str, str] = {
    # buttons
    "btn.ok": "Tamam", "btn.cancel": "İptal", "btn.browse": "Gözat…", "btn.add": "Ekle",
    "btn.move": "Taşı", "btn.group_new": "+ Grup", "btn.group_edit": "Düzenle",
    "btn.group_delete": "Sil", "btn.reset_ua": "Varsayılana dön",
    # toolbar
    "act.add": "＋ Link ekle", "act.monitor": "Pano izleme", "act.start_sel": "▶ Seçilenleri başlat",
    "act.start_view": "▶ Görünenleri başlat", "act.pause": "⏸ Duraklat", "act.group": "▣ Grupla…",
    "act.autogroup": "Yaratıcıya göre grupla", "act.remove": "✕ Kaldır", "act.clear": "Bitenleri temizle",
    "act.settings": "⚙ Ayarlar",
    "tip.add": "Linkleri elle yapıştır (Ctrl+V ile panodan direkt ekleyebilirsin)",
    "tip.monitor": "Açıkken kopyaladığın Civitai linkleri otomatik listeye eklenir",
    "tip.start_sel": "Seçili satırları indirmeye başla",
    "tip.start_view": "Şu an listede görünen (seçili gruptaki) tüm linkleri başlat",
    "tip.group": "Seçili linkleri bir gruba koy ve klasör ata (Ctrl+G)",
    "tip.autogroup": "Her yaratıcı için ayrı grup + klasör oluştur (Ayarlar'daki ana klasörün altında)",
    # table
    "col.name": "Ad", "col.version": "Sürüm", "col.creator": "Yaratıcı", "col.type": "Tür",
    "col.size": "Boyut", "col.group": "Grup", "col.status": "Durum", "col.progress": "İlerleme",
    "col.speed": "Hız",
    "state.resolving": "Çözümleniyor…", "state.ready": "Hazır", "state.queued": "Sırada",
    "state.downloading": "İndiriyor", "state.paused": "Duraklatıldı", "state.done": "Bitti",
    "state.error": "Hata",
    # errors
    "err.cloudflare": "Cloudflare engeli", "err.login": "Giriş / API anahtarı gerekli",
    "err.notfound": "Bulunamadı", "err.http": "HTTP hatası", "err.network": "Bağlantı hatası",
    "err.hash": "SHA256 uyuşmadı", "err.unknown": "Hata", "err.nofolder": "İndirme klasörü yok",
    "err.disk": "Disk hatası",
    "errlong.cloudflare": "Cloudflare isteği engelledi (bot doğrulaması). Birkaç dakika bekleyip tekrar dene; "
                          "eşzamanlı indirmeyi 1'e indir ve bekleme süresini artır. Olmazsa Ayarlar → Gelişmiş'te "
                          "tarayıcındaki cf_clearance çerezini ve aynı User-Agent'ı gir.",
    "errlong.login": "Bu dosya için Civitai girişi gerekiyor ya da API anahtarı geçersiz. Ayarlar'dan geçerli bir "
                     "API anahtarı gir. Erken erişimli modeller hesabında açık olmalı.",
    "errlong.notfound": "Civitai bu model/sürümü bulamadı (silinmiş veya gizli olabilir).",
    "errlong.network": "Ağ hatası veya sunucu geçici olarak yanıt vermedi; otomatik denemeler tükendi. "
                       "Tekrar başlatınca kaldığı yerden devam eder.",
    "errlong.hash": "İndirilen dosyanın SHA256 değeri Civitai'dekiyle aynı değil; dosya silindi.",
    "errlong.nofolder": "Bu link için bir klasör yok. Bir gruba klasör ata veya Ayarlar'dan varsayılan klasör seç.",
    # groups
    "lbl.groups": "GRUPLAR", "grp.all": "Tümü", "grp.none": "Gruplanmamış", "grp.no_folder": "(klasör atanmamış)",
    "empty.hint": "Henüz link yok.\n\nCivitai'de bir model sayfasının veya indirme butonunun linkini kopyala; "
                  "pano izleme açıkken otomatik buraya eklenir.\nSonra linkleri seçip gruplayabilir, "
                  "her gruba klasör atayıp indirmeyi başlatabilirsin.",
    # context menus
    "menu.open_folder": "Klasörü aç", "menu.move_to": "Gruba taşı", "menu.open_page": "Tarayıcıda aç",
    "menu.copy_link": "Linki kopyala", "menu.re_resolve": "Yeniden çözümle",
    # dialogs
    "dlg.pick_folder": "Klasör seç", "dlg.paste_title": "Link ekle",
    "dlg.paste_hint": "Civitai linklerini yapıştır (her satıra bir tane ya da karışık metin; linkler otomatik ayıklanır).",
    "dlg.group_new": "Yeni grup", "dlg.group_edit": "Grubu düzenle", "dlg.assign_title": "{n} link için grup",
    "dlg.new_group_item": "＋ Yeni grup…", "dlg.settings_title": "Ayarlar",
    "dlg.default_folder_title": "Klasörü olmayan {n} link için varsayılan indirme klasörü seç",
    "dlg.base_folder_title": "Yaratıcı klasörlerinin oluşturulacağı ana klasörü seç",
    "lbl.group_name": "Grup adı", "lbl.folder": "İndirme klasörü", "lbl.group": "Grup",
    "lbl.api_key": "Civitai API anahtarı", "lbl.show": "Göster", "lbl.default_folder": "Varsayılan klasör",
    "lbl.base_folder": "Yaratıcı ana klasörü", "lbl.language": "Dil", "lbl.theme": "Tema",
    "lbl.monitor": "Panoyu izle (Civitai linklerini otomatik ekle)",
    "lbl.concurrent": "Eşzamanlı indirme", "lbl.delay": "İndirmeler arası bekleme",
    "lbl.retries": "Hata durumunda deneme", "lbl.verify": "Bittiğinde SHA256 doğrula (büyük dosyalarda yavaş)",
    "lbl.user_agent": "User-Agent", "lbl.cookie": "Tarayıcı çerezi (isteğe bağlı)",
    "ph.api_key": "civitai.com → Hesap ayarları → API Keys",
    "hint.api_key": "Anahtar yalnızca Civitai'ye giden isteklerde Authorization başlığıyla gönderilir; "
                    "indirme CDN'ine yönlendirmede gönderilmez. Ayar dosyasında düz metin olarak saklanır.",
    "hint.base_folder": "“Yaratıcıya göre grupla” her yaratıcı için bu klasörün altında alt klasör açar.",
    "hint.delay": "Cloudflare art arda gelen isteklerden hoşlanmaz: düşük eşzamanlılık + bekleme engellenme riskini azaltır.",
    "hint.cloudflare": "Cloudflare engeli alırsan: tarayıcıda Civitai'yi açıp çerezlerden cf_clearance değerini kopyala "
                       "(tarayıcı geliştirici araçları → Depolama/Çerezler) ve tarayıcının User-Agent'ını yukarıya yaz. "
                       "Çerez yalnızca Civitai alan adına gönderilir ve süresi dolunca yenilenmelidir.",
    "opt.dark": "Koyu", "opt.light": "Açık",
    "tab.general": "Genel", "tab.downloads": "İndirme", "tab.advanced": "Gelişmiş",
    # messages
    "msg.confirm_group_delete": "“{name}” grubu silinsin mi? İçindeki linkler silinmez, “Gruplanmamış”a geçer.",
    "msg.confirm_remove": "{n} link listeden kaldırılsın mı? (Yarım kalan .part dosyaları silinir)",
    "msg.moved": "{n} link taşındı", "msg.monitor_on": "Pano izleme açık", "msg.monitor_off": "Pano izleme kapalı",
    "msg.added": "{n} yeni link eklendi", "msg.nothing_added": "Yeni Civitai linki bulunamadı (ya da hepsi zaten listede)",
    "msg.nothing_to_start": "Başlatılacak link yok", "msg.started": "{n} link kuyruğa alındı",
    "msg.select_first": "Önce listeden link seç", "msg.nothing_to_group": "Gruplanacak link yok",
    "msg.autogrouped": "{groups} yeni grup oluşturuldu, {n} link gruplandı",
    "msg.unresolved_skipped": "({n} linkin yaratıcısı henüz bilinmiyor, atlandı)",
    "msg.folder_missing": "Klasör bulunamadı: {path}",
    "msg.duplicate": "Zaten listede, tekrar eklenmedi: {detail}",
    "msg.queue_stopped_cf": "Cloudflare engeli: sıradaki indirmeler durduruldu. Bir süre bekleyip tekrar başlat.",
    "status.counts": "{total} link · {active} indiriyor · {queued} sırada · {done} bitti · {err} hata",
    "status.no_key": "⚠ API anahtarı girilmedi (Ayarlar)",
    "log.migrated": "Ayarlar eski konumdan taşındı: {src} → {dst} (taşınan: {moved}). Eski klasör temizlendi.",
    "log.migrated_left": "Eski konumda tanımadığım dosyalar kaldığı için klasör silinmedi: {left}",
    "log.migrate_failed": "Eski ayarlar taşınamadı ({err}); eski konumdaki veriler dokunulmadan duruyor: {src}",
    "log.config_fallback": "Exe klasörüne yazılamadı ({target}); ayarlar şurada tutuluyor: {path}",
    "msg.migrated": "Önceki ayarlar ve liste exe'nin yanındaki config klasörüne taşındı, eski klasör temizlendi",
    "lbl.config_dir": "Ayar klasörü",
    # log messages
    "log.link_added": "Link eklendi: {url}",
    "log.resolving": "Çözümleniyor (izin verilen uzantılar: {allowed})",
    "log.resolved": "Çözümlendi: yaratıcı={creator} tür={mtype} dosya={file} boyut={size} bayt",
    "log.resolve_failed": "Çözümleme başarısız: {err} | {info}",
    "log.no_matching_file": "Uzantı filtresine uyan dosya yok (izin verilen: {allowed}). Sürümdeki dosyalar: {files}",
    "log.file_chosen": "Seçilen dosya: {file} (atlananlar: {others})",
    "log.no_folder": "İndirme klasörü yok: gruba klasör ata ya da varsayılan klasör seç",
    "log.queued": "Kuyruğa alındı → {folder}",
    "log.dl_start": "İndirme başlıyor: {file} → {folder} (kaldığı yer: {resume} bayt)",
    "log.dl_done": "Bitti: {path} ({size} bayt, {secs} sn, {speed} MB/s)",
    "log.dl_paused": "Duraklatıldı/durduruldu (.part dosyasında {bytes} bayt)",
    "log.dl_retry": "Yeniden deneme {n}/{total} ({err}), {secs} sn sonra | {info}",
    "log.dl_failed": "İndirilemedi: {err} | {info}",
    "log.range_ignored": "Sunucu Range isteğini yok saydı; dosya baştan indiriliyor",
    # log panel + file filter
    "act.log": "☰ Günlük", "tip.log": "Neden inmedi? Ayrıntılı günlüğü aç/kapat",
    "logui.title": "Günlük", "logui.level_debug": "Ayrıntılı", "logui.level_info": "Bilgi",
    "logui.level_warn": "Uyarı ve hata", "logui.level_error": "Yalnızca hata",
    "logui.search": "Ara… (satır kodu: #a1b2c3)", "logui.clear": "Ekranı temizle",
    "logui.copy": "Kopyala", "logui.open_folder": "Günlük klasörü", "logui.file": "Dosya: {path}",
    "menu.show_log": "Bu satırın günlüğünü göster",
    "err.nofile": "Uzantı filtresine uyan dosya yok",
    "errlong.nofile": "Bu sürümde izin verilen uzantıda (Ayarlar → İndirme → Dosya türleri) dosya yok. "
                      "Sürümdeki dosyalar aşağıda. Filtreyi genişletip “Yeniden çözümle” yapabilirsin.",
    "lbl.file_extensions": "İzin verilen dosya türleri",
    "hint.file_extensions": "Virgülle ayır, sıra = tercih (ör. safetensors, pt). Boş bırakırsan her tür indirilir. "
                            "Sürümde birden çok dosya varsa bu türlerden biri seçilir; hiçbiri uymazsa satır hata verir. "
                            "Değişiklik yeni eklenen linklere uygulanır; eskiler için sağ tık → Yeniden çözümle.",
}

EN: dict[str, str] = {
    "btn.ok": "OK", "btn.cancel": "Cancel", "btn.browse": "Browse…", "btn.add": "Add",
    "btn.move": "Move", "btn.group_new": "+ Group", "btn.group_edit": "Edit",
    "btn.group_delete": "Delete", "btn.reset_ua": "Reset to default",
    "act.add": "＋ Add links", "act.monitor": "Clipboard watch", "act.start_sel": "▶ Start selected",
    "act.start_view": "▶ Start shown", "act.pause": "⏸ Pause", "act.group": "▣ Group…",
    "act.autogroup": "Group by creator", "act.remove": "✕ Remove", "act.clear": "Clear finished",
    "act.settings": "⚙ Settings",
    "tip.add": "Paste links manually (Ctrl+V adds straight from the clipboard)",
    "tip.monitor": "While on, copied Civitai links are added to the list automatically",
    "tip.start_sel": "Start the selected rows",
    "tip.start_view": "Start every link currently shown (in the selected group)",
    "tip.group": "Put the selected links into a group and assign a folder (Ctrl+G)",
    "tip.autogroup": "Create one group + folder per creator (under the base folder from Settings)",
    "col.name": "Name", "col.version": "Version", "col.creator": "Creator", "col.type": "Type",
    "col.size": "Size", "col.group": "Group", "col.status": "Status", "col.progress": "Progress",
    "col.speed": "Speed",
    "state.resolving": "Resolving…", "state.ready": "Ready", "state.queued": "Queued",
    "state.downloading": "Downloading", "state.paused": "Paused", "state.done": "Done",
    "state.error": "Error",
    "err.cloudflare": "Blocked by Cloudflare", "err.login": "Login / API key required",
    "err.notfound": "Not found", "err.http": "HTTP error", "err.network": "Connection error",
    "err.hash": "SHA256 mismatch", "err.unknown": "Error", "err.nofolder": "No download folder",
    "err.disk": "Disk error",
    "errlong.cloudflare": "Cloudflare blocked the request (bot check). Wait a few minutes and retry; lower the "
                          "concurrent downloads to 1 and raise the delay. If that is not enough, enter your "
                          "browser's cf_clearance cookie and the same User-Agent under Settings → Advanced.",
    "errlong.login": "This file needs a Civitai login, or the API key is invalid. Enter a valid API key in Settings. "
                     "Early-access models must be unlocked on your account.",
    "errlong.notfound": "Civitai could not find this model/version (it may be deleted or hidden).",
    "errlong.network": "Network error or the server did not answer in time; automatic retries are used up. "
                       "Starting it again resumes where it stopped.",
    "errlong.hash": "The SHA256 of the downloaded file does not match Civitai's; the file was deleted.",
    "errlong.nofolder": "This link has no folder. Assign a folder to its group or pick a default folder in Settings.",
    "lbl.groups": "GROUPS", "grp.all": "All", "grp.none": "Ungrouped", "grp.no_folder": "(no folder assigned)",
    "empty.hint": "No links yet.\n\nCopy the link of a model page or download button on Civitai; "
                  "with clipboard watch on it is added here automatically.\nThen select links, group them, "
                  "assign a folder to each group and start the downloads.",
    "menu.open_folder": "Open folder", "menu.move_to": "Move to group", "menu.open_page": "Open in browser",
    "menu.copy_link": "Copy link", "menu.re_resolve": "Resolve again",
    "dlg.pick_folder": "Choose folder", "dlg.paste_title": "Add links",
    "dlg.paste_hint": "Paste Civitai links (one per line, or any mixed text; links are extracted automatically).",
    "dlg.group_new": "New group", "dlg.group_edit": "Edit group", "dlg.assign_title": "Group for {n} link(s)",
    "dlg.new_group_item": "＋ New group…", "dlg.settings_title": "Settings",
    "dlg.default_folder_title": "Choose a default download folder for {n} link(s) without a folder",
    "dlg.base_folder_title": "Choose the base folder where creator folders will be created",
    "lbl.group_name": "Group name", "lbl.folder": "Download folder", "lbl.group": "Group",
    "lbl.api_key": "Civitai API key", "lbl.show": "Show", "lbl.default_folder": "Default folder",
    "lbl.base_folder": "Creator base folder", "lbl.language": "Language", "lbl.theme": "Theme",
    "lbl.monitor": "Watch the clipboard (add Civitai links automatically)",
    "lbl.concurrent": "Concurrent downloads", "lbl.delay": "Delay between downloads",
    "lbl.retries": "Retries on error", "lbl.verify": "Verify SHA256 when finished (slow for big files)",
    "lbl.user_agent": "User-Agent", "lbl.cookie": "Browser cookie (optional)",
    "ph.api_key": "civitai.com → Account settings → API Keys",
    "hint.api_key": "The key is sent only to Civitai in an Authorization header, never on the redirect to the "
                    "download CDN. It is stored as plain text in the settings file.",
    "hint.base_folder": "“Group by creator” creates one sub-folder per creator under this folder.",
    "hint.delay": "Cloudflare dislikes bursts of requests: low concurrency + a delay lowers the chance of being blocked.",
    "hint.cloudflare": "If you get blocked by Cloudflare: open Civitai in your browser, copy the cf_clearance cookie "
                       "(browser dev tools → Storage/Cookies) and put your browser's User-Agent above. "
                       "The cookie is only sent to the Civitai domain and expires, so it needs refreshing.",
    "opt.dark": "Dark", "opt.light": "Light",
    "tab.general": "General", "tab.downloads": "Downloads", "tab.advanced": "Advanced",
    "msg.confirm_group_delete": "Delete group “{name}”? Its links are kept and move to “Ungrouped”.",
    "msg.confirm_remove": "Remove {n} links from the list? (unfinished .part files are deleted)",
    "msg.moved": "{n} link(s) moved", "msg.monitor_on": "Clipboard watch on", "msg.monitor_off": "Clipboard watch off",
    "msg.added": "{n} new link(s) added", "msg.nothing_added": "No new Civitai links found (or all are already listed)",
    "msg.nothing_to_start": "Nothing to start", "msg.started": "{n} link(s) queued",
    "msg.select_first": "Select links in the list first", "msg.nothing_to_group": "Nothing to group",
    "msg.autogrouped": "{groups} new group(s) created, {n} link(s) grouped",
    "msg.unresolved_skipped": "({n} link(s) have no creator yet, skipped)",
    "msg.folder_missing": "Folder not found: {path}",
    "msg.duplicate": "Already in the list, not added again: {detail}",
    "msg.queue_stopped_cf": "Cloudflare block: the remaining queue was stopped. Wait a while, then start again.",
    "status.counts": "{total} links · {active} downloading · {queued} queued · {done} done · {err} errors",
    "status.no_key": "⚠ No API key set (Settings)",
    "log.migrated": "Settings moved from the old location: {src} → {dst} (moved: {moved}). Old folder cleaned up.",
    "log.migrated_left": "The old folder was kept because it still holds files I do not know: {left}",
    "log.migrate_failed": "Could not move the old settings ({err}); the old data is untouched at: {src}",
    "log.config_fallback": "Cannot write next to the exe ({target}); settings are kept in: {path}",
    "msg.migrated": "Previous settings and list were moved to the config folder next to the exe; old folder cleaned up",
    "lbl.config_dir": "Config folder",
    # log messages
    "log.link_added": "Link added: {url}",
    "log.resolving": "Resolving (allowed extensions: {allowed})",
    "log.resolved": "Resolved: creator={creator} type={mtype} file={file} size={size} bytes",
    "log.resolve_failed": "Resolve failed: {err} | {info}",
    "log.no_matching_file": "No file matches the extension filter (allowed: {allowed}). Files in this version: {files}",
    "log.file_chosen": "Chosen file: {file} (skipped: {others})",
    "log.no_folder": "No download folder: assign a folder to the group or pick a default folder",
    "log.queued": "Queued → {folder}",
    "log.dl_start": "Download starting: {file} → {folder} (resuming at {resume} bytes)",
    "log.dl_done": "Done: {path} ({size} bytes, {secs} s, {speed} MB/s)",
    "log.dl_paused": "Paused/stopped ({bytes} bytes in the .part file)",
    "log.dl_retry": "Retry {n}/{total} ({err}) in {secs} s | {info}",
    "log.dl_failed": "Download failed: {err} | {info}",
    "log.range_ignored": "Server ignored the Range request; restarting the file from the beginning",
    "act.log": "☰ Log", "tip.log": "Why did it not download? Show/hide the detailed log",
    "logui.title": "Log", "logui.level_debug": "Detailed", "logui.level_info": "Info",
    "logui.level_warn": "Warnings and errors", "logui.level_error": "Errors only",
    "logui.search": "Search… (row code: #a1b2c3)", "logui.clear": "Clear view",
    "logui.copy": "Copy", "logui.open_folder": "Log folder", "logui.file": "File: {path}",
    "menu.show_log": "Show this row's log",
    "err.nofile": "No file matches the extension filter",
    "errlong.nofile": "This version has no file with an allowed extension (Settings → Downloads → File types). "
                      "The files it does have are listed below. Widen the filter and use “Resolve again”.",
    "lbl.file_extensions": "Allowed file types",
    "hint.file_extensions": "Comma separated, order = preference (e.g. safetensors, pt). Leave empty to allow any type. "
                            "If a version has several files, one of these types is chosen; if none match the row errors out. "
                            "A change applies to newly added links; for existing ones use right-click → Resolve again.",
}

_TABLES = {"tr": TR, "en": EN}


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in _TABLES else "tr"


def get_language() -> str:
    return _lang


def t(key: str, **kw) -> str:
    text = _TABLES[_lang].get(key) or TR.get(key) or key
    if kw:
        try:
            return text.format(**kw)
        except (KeyError, IndexError):
            return text
    return text


def error_text(err: str, long: bool = False) -> str:
    """Translate an `Item.error` string of the form 'code[:detail]'."""
    code, _, detail = (err or "").partition(":")
    if code == "http" and detail.startswith("disk:"):
        return f"{t('err.disk')}: {detail[5:]}"
    if long:
        key = f"errlong.{code}"
        if key in TR:
            return t(key)
    key = f"err.{code}"
    base = t(key) if key in TR else t("err.unknown")
    return f"{base} ({detail})" if detail else base
