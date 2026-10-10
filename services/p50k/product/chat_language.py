"""Versioned plain-language interpretation of existing evidence, without new scores."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from p50k.product.egress import Evidence, Packet
from p50k.product.validator import PLACEHOLDER, validate_text

DEFINITIONS = {
    'D1': ('Benzer fonlarla getiri karşılaştırması',
           'Fonun günlük getirisinin aynı kategorideki fonlara göre farkının yakın dönem ortanca değeri.',
           'Kategori güncel katalog bilgisidir. Farkın nedeni bu ölçümden çıkarılamaz.'),
    'D2': ('Getiri davranışındaki değişim',
           'Benzer fonlara göre getiri farkının yakın dönem ile önceki dönem arasında değişmesi.',
           'Bir değişim gösterir; gelecekteki getiri hakkında bilgi vermez.'),
    'D3': ('Ardışık fiyat hareketleri',
           'Ardışık günlerdeki getirilerin birbiriyle ne kadar ilişkili olduğunu inceler.',
           'İlişkinin nedeni veya kaynağı yalnızca fiyatlardan belirlenemez.'),
    'D4': ('Benzer fonlardan ayrışma',
           'Fonun günlük getirisi ile aynı kategorinin günlük getirisi arasındaki ilişkiyi inceler.',
           'Daha düşük ilişki farklı hareketi gösterir; değişimin nedeni bu ölçümden çıkarılamaz.'),
    'D5': ('Fiyat geçmişinin uzunluğu',
           'Arşivde gözlenen fiyat geçmişinin uzunluğunu gösterir; fonun kuruluş tarihi değildir.',
           'Bu bir geçmiş bilgisi, uyarı veya risk puanı değildir.'),
    'AN-DQ-001': ('Fiyat bilgisinin güncelliği',
                  'Son kullanılabilir pozitif fiyat kaydından değerlendirme tarihine kadar geçen hafta içi günlerini sayar.',
                  'Hafta sonları dışarıda bırakılır; resmî tatiller ayrıca doğrulanmamıştır. Veri gecikmesi tek başına fon hakkında olumsuz bir sonuç değildir.'),
    'AN-DQ-002': ('Son fiyat kaydının durumu',
                  'En yeni kaynak kaydında kullanılabilir fiyat bulunup bulunmadığını kontrol eder.',
                  'Boş fiyat kaydı fiyatın sıfır olduğu anlamına gelmez. Önceki fiyatlar varsa kendi tarihleriyle incelenebilir.'),
    'AN-FND-005': ('Resmî duyuruların incelenmesi',
                   'Arşivlenen resmî olayın kimliği ve ne zaman kullanılabilir olduğunun doğrulanıp doğrulanmadığını inceler.',
                   'Yayın zamanı bilinmiyorsa olay bir sonuç üretmez. Arşiv sınırlıdır; sonuç üretilememesi resmî olay bulunmadığı anlamına gelmez.'),
}


def label(item: Evidence) -> str:
    return DEFINITIONS.get(item.detector_id, ('Kaynak incelemesi', '', ''))[0]


def evidence_fact(item: Evidence, reason: str = '') -> str:
    """All numeric language is rendered from approved deterministic values."""
    if item.state == 'ABSTAINED':
        reasons = {
            'CATEGORY_MISSING':'Fonun türü kaynakta belirtilmediği için benzer fonlarla karşılaştırma yapılamıyor.',
            'NO_CATEGORY_THRESHOLD':'Bu fon türünde karşılaştırma sınırı belirlemeye yetecek uygun kayıt yok.',
            'CURRENT_INPUT_OR_HISTORY_UNAVAILABLE':'Karşılaştırma için gerekli güncel fiyat veya geçmiş kayıtlar eksik.',
            'NO_POSITIVE_HISTORY':'Arşivde kullanılabilir bir geçmiş fiyat kaydı bulunmuyor.',
            'NO_ADMISSIBLE_PRICE_HISTORY':'Bu tarih için kullanılabilir geçmiş fiyat kaydı bulunmuyor.',
            'EVENT_UNCONFIRMED_OR_UNDATED':'Resmî kaydın eşleşmesi veya ne zaman yayımlandığı yeterince doğrulanmamış.',
            'SOURCE_SCOPE_LIMITED':'İncelenen resmî kaynak arşivi bu konuda bir sonuç çıkarmaya yeterli değil.',
        }
        if reason in reasons:
            return reasons[reason]
        if item.detector_id == 'AN-FND-005':
            return 'Resmî duyurular için uygun zaman bilgisi olan yeterli kaynak bulunmuyor.'
        return f'{label(item)} için uygun tarihli bilgiler yeterli değil.'
    if item.detector_id == 'AN-DQ-001':
        if item.state == 'NOT_TRIGGERED':
            return 'Son fiyat kaydı, değerlendirmede kullanılan güncellik sınırı içinde.'
        try:
            number = Decimal(item.value or '')
            if number.is_finite() and number >= 0 and number == number.to_integral_value():
                return f'Son fiyat kaydından değerlendirme tarihine kadar {number:.0f} hafta içi gün geçmiş.'
        except InvalidOperation:
            pass
        return 'Son fiyat kaydı, değerlendirmede kullanılan güncellik sınırının gerisinde.'
    if item.detector_id == 'AN-DQ-002':
        return ('Kaynağın son kaydında kullanılabilir bir fiyat bulunmuyor.' if item.state == 'TRIGGERED'
                else 'Kaynağın son kaydında kullanılabilir bir fiyat var.')
    if item.detector_id == 'D5':
        return 'Bu bilgi yalnızca arşivdeki fiyat geçmişinin uzunluğunu anlatır.'
    if item.detector_id == 'AN-FND-005':
        return 'Uygun zaman bilgisiyle eşleşen resmî bir kayıt incelemeye alınmış.'
    descriptions = {
        'D1': 'Benzer fonlara göre getiri farkı, inceleme sınırını aşmış.',
        'D2': 'Benzer fonlara göre getiri davranışındaki değişim, inceleme sınırını aşmış.',
        'D3': 'Ardışık günlük getiriler arasındaki ilişki, inceleme sınırını aşmış.',
        'D4': 'Fonun fiyat hareketleri ile benzer fonlar arasındaki ilişki, inceleme sınırının altına düşmüş.',
    }
    if item.state == 'TRIGGERED':
        return descriptions.get(item.detector_id, 'Bu kaynak bilgisi ayrıca inceleme gerektiriyor.')
    return f'{label(item)} incelemesinde belirlenen sınır aşılmamış.'


def explanations(packet: Packet, reasons: dict[str,str] | None = None) -> list[dict[str, str]]:
    return [{'evidence_id':item.evidence_id, 'name_tr':label(item),
             'measures_tr':DEFINITIONS.get(item.detector_id, ('', 'Kaynak kaydı', ''))[1],
             'observed_fact_tr':evidence_fact(item,(reasons or {}).get(item.evidence_id,'')),
             'limits_tr':DEFINITIONS.get(item.detector_id, ('', '', 'Nedeni bu kayıttan belirlenemez.'))[2]}
            for item in packet.evidence]


def render_chat(text: str, packet: Packet, reasons: dict[str,str] | None = None) -> str:
    validate_text(text, packet)
    items = {item.evidence_id:item for item in packet.evidence}
    return PLACEHOLDER.sub(lambda match: evidence_fact(items[match.group(1)],(reasons or {}).get(match.group(1),'')) if match.group(1) else packet.fund_code, text)
