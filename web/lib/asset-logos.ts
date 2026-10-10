/** Public brand metadata only. Provenance and SHA-256: /asset-logos/provenance.json. */
export type AssetKind = 'fund'|'stock';
export type AssetLogoRecord = {path:string;issuer:string;sourceUrl:string;background?:string};
export const stockLogos:Record<string,AssetLogoRecord> = {
  "AEFES": {
    "path": "/asset-logos/aefes.png",
    "issuer": "ANADOLU EFES B\u0130RACILIK VE MALT SANAY\u0130\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140e95bea0140ed2fde10009d"
  },
  "AKBNK": {
    "path": "/asset-logos/akbnk.jpg",
    "issuer": "AKBANK T.A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a240e8d1830140e905edcd0006"
  },
  "ASELS": {
    "path": "/asset-logos/asels.png",
    "issuer": "ASELSAN ELEKTRON\u0130K SANAY\u0130 VE T\u0130CARET A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a1413b7ef401413bc2251e0047"
  },
  "ASTOR": {
    "path": "/asset-logos/astor.jpg",
    "issuer": "ASTOR ENERJ\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c562329bd10164405fe6c17996"
  },
  "BIMAS": {
    "path": "/asset-logos/bimas.png",
    "issuer": "B\u0130M B\u0130RLE\u015e\u0130K MA\u011eAZALAR A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140e95be70140ee1b7b030119"
  },
  "EKGYO": {
    "path": "/asset-logos/ekgyo.png",
    "issuer": "EMLAK KONUT GAYR\u0130MENKUL YATIRIM ORTAKLI\u011eI A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a2422d9a780142513cda5b232e"
  },
  "ENKAI": {
    "path": "/asset-logos/enkai.jpg",
    "issuer": "ENKA \u0130N\u015eAAT VE SANAY\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a240e95dc90140ed3883fe0093"
  },
  "EREGL": {
    "path": "/asset-logos/eregl.jpg",
    "issuer": "ERE\u011eL\u0130 DEM\u0130R VE \u00c7EL\u0130K FABR\u0130KALARI T.A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a240e95dc90140ede4c12a0133"
  },
  "FROTO": {
    "path": "/asset-logos/froto.png",
    "issuer": "FORD OTOMOT\u0130V SANAY\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140f2ed71014106890fae0138"
  },
  "GARAN": {
    "path": "/asset-logos/garan.png",
    "issuer": "T\u00dcRK\u0130YE GARANT\u0130 BANKASI A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140f2ed720140f37cb2a601b7"
  },
  "GUBRF": {
    "path": "/asset-logos/gubrf.jpg",
    "issuer": "G\u00dcBRE FABR\u0130KALARI T.A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a241733d4a01417989f3760a4d"
  },
  "ISCTR": {
    "path": "/asset-logos/isctr.png",
    "issuer": "T\u00dcRK\u0130YE \u0130\u015e BANKASI A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140f2ed7201411682b0cb05c6"
  },
  "KCHOL": {
    "path": "/asset-logos/kchol.png",
    "issuer": "KO\u00c7 HOLD\u0130NG A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140f2ed710140f2f4d6c70039"
  },
  "KRDMD": {
    "path": "/asset-logos/krdmd.png",
    "issuer": "KARDEM\u0130R KARAB\u00dcK DEM\u0130R \u00c7EL\u0130K SANAY\u0130 VE T\u0130CARET A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140f2ed7201412ace3ada0707"
  },
  "MGROS": {
    "path": "/asset-logos/mgros.jpg",
    "issuer": "M\u0130GROS T\u0130CARET A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a141462df2014150162e1c3424"
  },
  "PETKM": {
    "path": "/asset-logos/petkm.jpg",
    "issuer": "PETK\u0130M PETROK\u0130MYA HOLD\u0130NG A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a240f2ef470141165c566a03e4"
  },
  "PGSUS": {
    "path": "/asset-logos/pgsus.jpg",
    "issuer": "PEGASUS HAVA TA\u015eIMACILI\u011eI A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a2422d9a78014232e751bc22a4"
  },
  "SAHOL": {
    "path": "/asset-logos/sahol.jpg",
    "issuer": "HACI \u00d6MER SABANCI HOLD\u0130NG A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a240ee37a90140ee50087e000b"
  },
  "SASA": {
    "path": "/asset-logos/sasa.png",
    "issuer": "SASA POLYESTER SANAY\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a240ee866c0140f20abd9500cc"
  },
  "SISE": {
    "path": "/asset-logos/sise.jpg",
    "issuer": "T\u00dcRK\u0130YE \u015e\u0130\u015eE VE CAM FABR\u0130KALARI A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140f2ed710140f385d5690102"
  },
  "TAVHL": {
    "path": "/asset-logos/tavhl.png",
    "issuer": "TAV HAVAL\u0130MANLARI HOLD\u0130NG A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140f2ed720140f31195ef010e"
  },
  "TCELL": {
    "path": "/asset-logos/tcell.png",
    "issuer": "TURKCELL \u0130LET\u0130\u015e\u0130M H\u0130ZMETLER\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a1486ec80a0148c55510d71d31"
  },
  "THYAO": {
    "path": "/asset-logos/thyao.jpg",
    "issuer": "T\u00dcRK HAVA YOLLARI A.O.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140f2ed720140f376bebb01a7"
  },
  "TOASO": {
    "path": "/asset-logos/toaso.png",
    "issuer": "TOFA\u015e T\u00dcRK OTOMOB\u0130L FABR\u0130KASI A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140f2ed710140f328bed700a5"
  },
  "TRALT": {
    "path": "/asset-logos/tralt.jpg",
    "issuer": "T\u00dcRK ALTIN \u0130\u015eLETMELER\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a2422d9a6e0142bd91d3687a69"
  },
  "TRMET": {
    "path": "/asset-logos/trmet.jpg",
    "issuer": "TR ANADOLU METAL MADENC\u0130L\u0130K \u0130\u015eLETMELER\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a2422d9a6e0142bd921d307a6d"
  },
  "TTKOM": {
    "path": "/asset-logos/ttkom.png",
    "issuer": "T\u00dcRK TELEKOM\u00dcN\u0130KASYON A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a241e538ab0141ea9c96912c8b"
  },
  "TUPRS": {
    "path": "/asset-logos/tuprs.jpg",
    "issuer": "T\u00dcPRA\u015e-T\u00dcRK\u0130YE PETROL RAF\u0130NER\u0130LER\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140f2ed720140f37f139c01bc"
  },
  "VAKBN": {
    "path": "/asset-logos/vakbn.jpg",
    "issuer": "T\u00dcRK\u0130YE VAKIFLAR BANKASI T.A.O.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a1415f4d9b01415fe3340f36e4"
  },
  "YKBNK": {
    "path": "/asset-logos/ykbnk.jpg",
    "issuer": "YAPI VE KRED\u0130 BANKASI A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a240f2ef4c01412ae6d6630538"
  }
};
export const fundManagerLogos:(AssetLogoRecord&{prefixes:string[]})[] = [
  {
    "prefixes": [
      "A1 CAPITAL PORTFOY"
    ],
    "path": "/asset-logos/manager-a1-capital-portfoy.jpg",
    "issuer": "A1 CAP\u0130TAL PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c494bafc93019566721bf70ddf"
  },
  {
    "prefixes": [
      "AHLATCI PORTFOY"
    ],
    "path": "/asset-logos/manager-ahlatci-portfoy.png",
    "issuer": "AHLATCI PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c59145e00a019667f2cfb61c13"
  },
  {
    "prefixes": [
      "AK PORTFOY"
    ],
    "path": "/asset-logos/manager-ak.svg",
    "issuer": "Ak Portf\u00f6y",
    "sourceUrl": "https://www.akportfoy.com.tr/images/logo-bf73802c5e7beb4af700311c8e1f5b0c.svg"
  },
  {
    "prefixes": [
      "AKTIF PORTFOY"
    ],
    "path": "/asset-logos/manager-aktif-portfoy.png",
    "issuer": "AKT\u0130F PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c45835eb6601594aab49376642"
  },
  {
    "prefixes": [
      "ALBARAKA PORTFOY"
    ],
    "path": "/asset-logos/manager-albaraka-portfoy.jpg",
    "issuer": "ALBARAKA PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c4508ff72301513da7a3690e68"
  },
  {
    "prefixes": [
      "ALLBATROSS PORTFOY"
    ],
    "path": "/asset-logos/manager-allbatross-portfoy.png",
    "issuer": "ALLBATROSS PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c469cee2a4016ad972e7f11276"
  },
  {
    "prefixes": [
      "ASTRA PORTFOY"
    ],
    "path": "/asset-logos/manager-astra-portfoy.png",
    "issuer": "ASTRA PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://astraportfoy.com.tr/assets/img/dark-logo.png"
  },
  {
    "prefixes": [
      "ATA PORTFOY"
    ],
    "path": "/asset-logos/manager-ata-portfoy.jpg",
    "issuer": "ATA PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140e95bea0140ede30ded013f"
  },
  {
    "prefixes": [
      "ATLAS PORTFOY"
    ],
    "path": "/asset-logos/manager-atlas-portfoy.jpg",
    "issuer": "ATLAS PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a141558bdd0141561817540562"
  },
  {
    "prefixes": [
      "AURA PORTFOY"
    ],
    "path": "/asset-logos/manager-aura-portfoy.png",
    "issuer": "AURA PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a243dd5e8f01448d9c23ae7e93"
  },
  {
    "prefixes": [
      "AZIMUT PORTFOY",
      "AZIMUT PYS"
    ],
    "path": "/asset-logos/manager-azimut.svg",
    "issuer": "Azimut Portf\u00f6y",
    "sourceUrl": "https://azimutportfoy.com/wp-content/uploads/2022/05/azimut-logo.svg",
    "background": "#102139"
  },
  {
    "prefixes": [
      "BTCTURK PORTFOY"
    ],
    "path": "/asset-logos/manager-btcturk-portfoy.png",
    "issuer": "BTCTURK PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c4998f24d8019a4e14810301dc"
  },
  {
    "prefixes": [
      "BULLS PORTFOY"
    ],
    "path": "/asset-logos/manager-bulls-portfoy.png",
    "issuer": "BULLS PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c59145e00a0193abc32de87981"
  },
  {
    "prefixes": [
      "BV PORTFOY"
    ],
    "path": "/asset-logos/manager-bv-portfoy.svg",
    "issuer": "BV PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.bvportfoy.com/storage/site-images/logo.svg"
  },
  {
    "prefixes": [
      "DENIZ PORTFOY"
    ],
    "path": "/asset-logos/manager-deniz.png",
    "issuer": "Deniz Portf\u00f6y",
    "sourceUrl": "https://www.denizportfoy.com/asset/img/denizportfoy-header-logo.png",
    "background": "#102139"
  },
  {
    "prefixes": [
      "EMAA BLUE PORTFOY"
    ],
    "path": "/asset-logos/manager-emaa-blue-portfoy.png",
    "issuer": "EMAA BLUE PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://emaaportfoy.com.tr/images/logo-400.png"
  },
  {
    "prefixes": [
      "FIBA PORTFOY"
    ],
    "path": "/asset-logos/manager-fiba-portfoy.png",
    "issuer": "F\u0130BA PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a2422d9a780142ec1bd59a193c"
  },
  {
    "prefixes": [
      "FONMAP PORTFOY"
    ],
    "path": "/asset-logos/manager-fonmap-portfoy.png",
    "issuer": "FONMAP PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c486d22a3b01894e77f0b63fed"
  },
  {
    "prefixes": [
      "GARANTI PORTFOY",
      "GARANTI BBVA PORTFOY"
    ],
    "path": "/asset-logos/manager-garanti.svg",
    "issuer": "Garanti BBVA Portf\u00f6y",
    "sourceUrl": "https://www.garantibbvaportfoy.com.tr/assets/garanti-favicon.svg?cache=31536000"
  },
  {
    "prefixes": [
      "GLOBAL MD PORTFOY"
    ],
    "path": "/asset-logos/manager-global-md-portfoy.jpg",
    "issuer": "GLOBAL MD PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a14158e41f01415b1b93e3618a"
  },
  {
    "prefixes": [
      "GOLDEN GLOBAL PORTFOY"
    ],
    "path": "/asset-logos/manager-golden-global-portfoy.png",
    "issuer": "GOLDEN GLOBAL PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c4998f24d80199c3afb0d320dc"
  },
  {
    "prefixes": [
      "HAS PORTFOY"
    ],
    "path": "/asset-logos/manager-has-portfoy.png",
    "issuer": "HAS PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c57f7cbb490180d71931c56213"
  },
  {
    "prefixes": [
      "HEDEF PORTFOY"
    ],
    "path": "/asset-logos/manager-hedef.png",
    "issuer": "Hedef Portf\u00f6y",
    "sourceUrl": "https://hedefportfoy.com.tr/media/img/Hedef_Portfoy_Logo_new.png"
  },
  {
    "prefixes": [
      "HSBC PORTFOY",
      "HSBC PYS"
    ],
    "path": "/asset-logos/manager-hsbc-portfoy.png",
    "issuer": "HSBC PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a2413b80ca01413b9b10830009"
  },
  {
    "prefixes": [
      "INVEO PORTFOY"
    ],
    "path": "/asset-logos/manager-inveo-portfoy.png",
    "issuer": "INVEO PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a240f2ef4c01413b5ccdb3075e"
  },
  {
    "prefixes": [
      "IS PORTFOY"
    ],
    "path": "/asset-logos/manager-is.png",
    "issuer": "\u0130\u015f Portf\u00f6y",
    "sourceUrl": "https://www.isportfoy.com.tr/_assets/images/favicon/android-icon-192x192.png"
  },
  {
    "prefixes": [
      "ISTANBUL PORTFOY"
    ],
    "path": "/asset-logos/manager-istanbul.svg",
    "issuer": "\u0130stanbul Portf\u00f6y",
    "sourceUrl": "https://www.istanbulportfoy.com/assets/img/logo_black.svg"
  },
  {
    "prefixes": [
      "KARE PORTFOY"
    ],
    "path": "/asset-logos/manager-kare-portfoy.jpg",
    "issuer": "KARE PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/402821814da3a99c014e2ab71fee6e8e"
  },
  {
    "prefixes": [
      "KUVEYT TURK PORTFOY",
      "KT PORTFOY"
    ],
    "path": "/asset-logos/manager-kuveyt-turk.png",
    "issuer": "Kuveyt T\u00fcrk Portf\u00f6y",
    "sourceUrl": "https://www.kuveytturkportfoy.com.tr/Content/images/favicon/apple-touch-icon.png"
  },
  {
    "prefixes": [
      "LOGOS PORTFOY"
    ],
    "path": "/asset-logos/manager-logos-portfoy.jpg",
    "issuer": "LOGOS PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/9376ae46e2b841f38f024cada869f7cb"
  },
  {
    "prefixes": [
      "MARMARA CAPITAL PORTFOY"
    ],
    "path": "/asset-logos/manager-marmara-capital-portfoy.png",
    "issuer": "MARMARA CAP\u0130TAL PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/402821814da3a99c014e49c9dbfb5a38"
  },
  {
    "prefixes": [
      "MT PORTFOY"
    ],
    "path": "/asset-logos/manager-mt-portfoy.png",
    "issuer": "MT PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c48c3efabf019053c36ee94619"
  },
  {
    "prefixes": [
      "NEO PORTFOY"
    ],
    "path": "/asset-logos/manager-neo.svg",
    "issuer": "Neo Portf\u00f6y",
    "sourceUrl": "https://www.neoportfoy.com.tr/TR/Content/images/neo_portfoy_logo-01.svg"
  },
  {
    "prefixes": [
      "NUROL PORTFOY"
    ],
    "path": "/asset-logos/manager-nurol-portfoy.jpg",
    "issuer": "NUROL PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c57902e74f0179139e5075055d"
  },
  {
    "prefixes": [
      "ONE PORTFOY"
    ],
    "path": "/asset-logos/manager-one-portfoy.jpg",
    "issuer": "ONE PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c57d3bf001017f2aacfe03557e"
  },
  {
    "prefixes": [
      "OSMANLI PORTFOY"
    ],
    "path": "/asset-logos/manager-osmanli-portfoy.png",
    "issuer": "OSMANLI PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/402821814da3a99c014e8702206748d8"
  },
  {
    "prefixes": [
      "OYAK PORTFOY"
    ],
    "path": "/asset-logos/manager-oyak-portfoy.png",
    "issuer": "OYAK PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a140ee35c70140ee4bf71b0032"
  },
  {
    "prefixes": [
      "PARDUS PORTFOY"
    ],
    "path": "/asset-logos/manager-pardus.png",
    "issuer": "Pardus Portf\u00f6y",
    "sourceUrl": "https://pardusportfoy.com/wp-content/uploads/2026/02/PARDUS-PORTFOY-LOGO-fav.png"
  },
  {
    "prefixes": [
      "PERFORM PORTFOY"
    ],
    "path": "/asset-logos/manager-perform-portfoy.png",
    "issuer": "PERFORM PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a1413b7ef5014144ecbaca00a2"
  },
  {
    "prefixes": [
      "PHILLIP PORTFOY"
    ],
    "path": "/asset-logos/manager-phillip-portfoy.png",
    "issuer": "PH\u0130LL\u0130P PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c5794d3d6a01795675f77d0208"
  },
  {
    "prefixes": [
      "PIRAMIT PORTFOY"
    ],
    "path": "/asset-logos/manager-piramit-portfoy.png",
    "issuer": "P\u0130RAM\u0130T PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.piramitportfoy.com.tr/logo.png"
  },
  {
    "prefixes": [
      "PUSULA PORTFOY"
    ],
    "path": "/asset-logos/manager-pusula-portfoy.png",
    "issuer": "PUSULA PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c58b2fa64e018c4892184924cb"
  },
  {
    "prefixes": [
      "QNB PORTFOY",
      "QNB FINANS PORTFOY"
    ],
    "path": "/asset-logos/manager-qnb.png",
    "issuer": "QNB Portf\u00f6y",
    "sourceUrl": "https://www.qnbportfoy.com.tr/assets/qnb/qnb-logo.png"
  },
  {
    "prefixes": [
      "RE-PIE PORTFOY"
    ],
    "path": "/asset-logos/manager-re-pie-portfoy.jpg",
    "issuer": "RE-PIE PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a1486ec80b0149cd1831905a49"
  },
  {
    "prefixes": [
      "ROTA PORTFOY"
    ],
    "path": "/asset-logos/manager-rota.png",
    "issuer": "Rota Portf\u00f6y",
    "sourceUrl": "https://www.rotaportfoy.com.tr/images/favicon/favicon-96x96.png"
  },
  {
    "prefixes": [
      "SPARTA PORTFOY"
    ],
    "path": "/asset-logos/manager-sparta-portfoy.png",
    "issuer": "SPARTA PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c59145e00a0193f2cc94b21877"
  },
  {
    "prefixes": [
      "STATECH PORTFOY"
    ],
    "path": "/asset-logos/manager-statech-portfoy.jpg",
    "issuer": "STATECH PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c47d3bee4e017ebfae3ef118d6"
  },
  {
    "prefixes": [
      "STRATEJI PORTFOY"
    ],
    "path": "/asset-logos/manager-strateji-portfoy.png",
    "issuer": "STRATEJ\u0130 PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/1DE05DAA83D6073AE0530A4A622A2EBD"
  },
  {
    "prefixes": [
      "TACIRLER PORTFOY"
    ],
    "path": "/asset-logos/manager-tacirler.svg",
    "issuer": "Tacirler Portf\u00f6y",
    "sourceUrl": "https://tacirlerportfoy.com.tr/upload/images/tacirler_portfoy/portfoy-logo.svg",
    "background": "#102139"
  },
  {
    "prefixes": [
      "TEB PORTFOY"
    ],
    "path": "/asset-logos/manager-teb.svg",
    "issuer": "TEB Portf\u00f6y",
    "sourceUrl": "https://www.tebportfoy.com.tr/_assets/img/logo.svg",
    "background": "#102139"
  },
  {
    "prefixes": [
      "TERA PORTFOY"
    ],
    "path": "/asset-logos/manager-tera.png",
    "issuer": "Tera Portf\u00f6y",
    "sourceUrl": "https://www.teraportfoy.com/img/android-icon-192x192.png"
  },
  {
    "prefixes": [
      "TRIVE PORTFOY"
    ],
    "path": "/asset-logos/manager-trive-portfoy.jpg",
    "issuer": "TRIVE PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c57f7cbb48018046fa790f7a84"
  },
  {
    "prefixes": [
      "UNLU PORTFOY"
    ],
    "path": "/asset-logos/manager-unlu-portfoy.png",
    "issuer": "\u00dcNL\u00dc PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/4028e4a142140a8c014222e48869248c"
  },
  {
    "prefixes": [
      "V PORTFOY"
    ],
    "path": "/asset-logos/manager-v-portfoy.png",
    "issuer": "V PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c59b85fa03019bbc9da18f365b"
  },
  {
    "prefixes": [
      "VEGA PORTFOY"
    ],
    "path": "/asset-logos/manager-vega-portfoy.png",
    "issuer": "VEGA PORTF\u00d6Y Y\u00d6NET\u0130M\u0130 A.\u015e.",
    "sourceUrl": "https://www.kap.org.tr/tr/api/member/logo/8acae2c58b2fa64e018b956289953cdd"
  },
  {
    "prefixes": [
      "YAPI KREDI PORTFOY"
    ],
    "path": "/asset-logos/manager-yapi-kredi.svg",
    "issuer": "Yap\u0131 Kredi Portf\u00f6y",
    "sourceUrl": "https://www.yapikrediportfoy.com.tr/assets/images/logo-mobile.svg"
  },
  {
    "prefixes": [
      "ZIRAAT PORTFOY"
    ],
    "path": "/asset-logos/manager-ziraat.png",
    "issuer": "Ziraat Portf\u00f6y",
    "sourceUrl": "https://www.ziraatportfoy.com.tr/media/hkfjhysg/favicon180x180.png"
  }
];
export function normalizeIssuerName(name:string):string{
  return name.replace(/\u0131/g,'i').replace(/\u0130/g,'I').normalize('NFKD').replace(/[\u0300-\u036f]/g,'').toUpperCase().replace(/\s+/g,' ').trim();
}
export function resolveAssetLogo(kind:AssetKind,code:string,name?:string):AssetLogoRecord|undefined{
  if(kind==='stock')return stockLogos[code.toUpperCase()];
  if(!name)return undefined;
  const normalized=normalizeIssuerName(name);
  return fundManagerLogos.find(manager=>manager.prefixes.some(prefix=>normalized===prefix||normalized.startsWith(prefix+' ')));
}
