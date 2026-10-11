"""Fixed menus and plain Turkish labels; codes stay in records, never in prose."""
from __future__ import annotations

ROLES = ('sentinel', 'hypothesizer', 'skeptic', 'verifier', 'reporter')
AI_ROLES = ('hypothesizer', 'skeptic', 'verifier', 'reporter')
FAST_ROLES = ('hypothesizer', 'skeptic')

ROLE_NAMES = {
    'sentinel': 'Nöbetçi', 'hypothesizer': 'Hipotezci', 'skeptic': 'Şüpheci',
    'verifier': 'Doğrulayıcı', 'reporter': 'Raportör',
}
ROLE_DESCRIPTIONS = {
    'sentinel': 'Tamamlanmış hesaplamaları tarar ve inceleme sınırını aşan fonlar için vaka açar. Yapay zekâ kullanmaz.',
    'hypothesizer': 'Kanıtı açıklayabilecek en fazla üç olası açıklama önerir.',
    'skeptic': 'Karşı açıklamalar önerir ve Doğrulayıcının çalıştıracağı testleri sabit listeden seçer.',
    'verifier': 'Testleri kodla çalıştırır, ardından açıklamaları test sonuçları ve kanıtla değerlendirir.',
    'reporter': 'Denetlenebilir raporu yazar, karar önerisini insan incelemesine sunar ve sizinle konuşur.',
}
TASK_TITLES = {
    'sentinel': 'Hesaplamaları taradı ve vaka açtı',
    'hypothesizer': 'Olası açıklamaları çıkar',
    'skeptic': 'Karşı açıklamaları ve sınama testlerini seç',
    'verifier': 'Testleri çalıştır ve açıklamaları sına',
    'reporter': 'Raporu yaz ve karar önerisini insan incelemesine sun',
}
CASE_STATUS_TR = {'open': 'Açık', 'investigating': 'İnceleniyor', 'reported': 'Raporlandı', 'closed': 'Kapandı'}
TASK_STATUS_TR = {
    'queued': 'Sırada', 'running': 'Çalışıyor', 'done': 'Tamamlandı', 'failed': 'Tamamlanamadı',
    'waiting_budget': 'Bütçe bekliyor', 'skipped': 'Atlandı',
}

# Hipotezci's fixed menu (DEC-035). Descriptions are model input, not prose to copy.
HYPOTHESIS_TYPES = {
    'peer_divergence': 'Fon, aynı kategorideki benzer fonlardan farklı hareket ediyor olabilir.',
    'flow_change': 'Fona giriş veya fondan çıkışlarda bir değişim fiyat davranışını etkilemiş olabilir.',
    'allocation_shift': 'Fonun varlık dağılımındaki bir değişim fiyat davranışını etkilemiş olabilir.',
    'regulatory_action': 'Fonla ilgili resmî bir düzenleyici işlem gözlemi açıklayabilir.',
    'data_issue': 'Gözlem kaynak verideki eksik, gecikmiş veya çelişkili kayıtlardan kaynaklanıyor olabilir.',
    'market_wide_move': 'Gözlem kategorinin veya piyasanın genel hareketinden kaynaklanıyor olabilir.',
}
HYPOTHESIS_TYPE_TR = {
    'peer_divergence': 'Benzer fonlardan ayrışma', 'flow_change': 'Fon akışında değişim',
    'allocation_shift': 'Varlık dağılımında değişim', 'regulatory_action': 'Düzenleyici işlem',
    'data_issue': 'Veri sorunu', 'market_wide_move': 'Piyasa geneli hareket',
}
# Şüpheci's counter-explanation menu.
COUNTER_TYPES = {
    'market_wide_move': 'Kategorinin veya piyasanın genel hareketi gözlemi açıklayabilir.',
    'data_issue': 'Eksik, gecikmiş veya çelişkili kaynak kayıtları gözlemi açıklayabilir.',
    'peer_group_mismatch': 'Fonun güncel kategori bilgisi, karşılaştırıldığı fonlarla uyumlu olmayabilir.',
    'short_history': 'Gözlenen fiyat geçmişi kısa olduğundan karşılaştırma zayıf kalabilir.',
    'isolated_move': 'Gözlem kısa süreli tek bir hareketten kaynaklanıyor olabilir.',
}
COUNTER_TYPE_TR = {
    'market_wide_move': 'Piyasa geneli hareket', 'data_issue': 'Veri sorunu',
    'peer_group_mismatch': 'Karşılaştırma grubu uyumsuzluğu', 'short_history': 'Kısa fiyat geçmişi',
    'isolated_move': 'Tek seferlik hareket',
}
VERDICTS = ('supported', 'refuted', 'undetermined')
VERDICT_TR = {'supported': 'Kanıtla destekleniyor', 'refuted': 'Kanıtla desteklenmiyor', 'undetermined': 'Belirsiz'}

DECISION_MEANINGS = {
    'MATERIAL': 'İnsan incelemesi gerektiren önemli bir gözlem var; bu bir yatırım, hukuk veya risk sonucu değildir.',
    'NOT_MATERIAL': 'İncelenen ölçümler belirlenen sınırlar içinde; bu güvence veya sonuç anlamına gelmez.',
    'DATA_ISSUE': 'Kaynak verinin kontrol edilmesi gerekiyor.',
    'INSUFFICIENT_EVIDENCE': 'Mevcut kanıt bir değerlendirme için yeterli değil.',
}

FAILED_STEP_TR = 'Bu adım doğrulanamadı; insan incelemesi gerekli.'
SKIP_NOTES = {
    'AI_OFF': 'Yapay zekâ kapalı olduğu için bu adım çalıştırılmadı.',
    'AI_UNAVAILABLE': 'Yapay zekâ bu ortamda kullanılamadığı için bu adım çalıştırılmadı.',
    'EVIDENCE_CHANGED': 'Vakanın kanıtı yeni bir hesaplamayla değişti; bu adım eski kanıtla çalıştırılmadı.',
    'EVIDENCE_UNAVAILABLE': 'Seçili tarih için bu fonun hesaplanmış kanıtı bulunamadı.',
    'CASE_CLOSED': 'Vaka kapandığı için bu adım çalıştırılmadı.',
}
WAIT_REASON_TR = {
    'DAILY_BUDGET': 'Günlük yapay zekâ bütçesi doldu; yarın kaldığı yerden devam edecek.',
    'TOTAL_TARGET': 'Toplam bütçe hedefine ulaşıldı; devam etmek için insan onayı gerekiyor.',
}

ACTIVITY_TR = {
    'hypothesizer': 'Olası açıklamaları çıkarıyor',
    'skeptic': 'Karşı açıklamaları ve sınama testlerini seçiyor',
    'verifier': 'Testleri kodla çalıştırıyor ve açıklamaları sınıyor',
    'reporter': 'Raporu yazıyor ve karar önerisini hazırlıyor',
}
DECISION_TR = {
    'MATERIAL': 'İnsan incelemesi önerildi', 'NOT_MATERIAL': 'İncelenen ölçümler sınırlar içinde',
    'DATA_ISSUE': 'Kaynak verisinin kontrolü önerildi', 'INSUFFICIENT_EVIDENCE': 'Kanıt yetersiz',
    'UNDECIDED': 'Karar verilmedi',
}
REQUEST_NOTE_TR = 'Raportör, kullanıcının inceleme isteğini ekibin sırasına öncelikli olarak ekledi.'
AI_OFF_ACTIVITY_TR = 'Yapay zekâ kapalı; kural tabanlı adımlar çalışmaya devam ediyor.'

PAGE_VISIT_PRIORITY = 70
USER_PRIORITY = 100
REGULATORY_BONUS = 50
