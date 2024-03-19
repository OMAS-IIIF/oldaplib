from enum import Enum, unique

from omaslib.src.helpers.serializer import serializer


@unique
@serializer
class Language(Enum):
    """
    Implements an Enum class for all ISO language. The form is as follows

    - ...
    - `Language.EN` = 'English'
    - `Language.DE` = 'German'
    - `Language.FR` = 'French'
    - `Language.IT` = 'Italian'
    - ...
    """
    def _as_dict(self):
        return {"value": self.value }

    AB = "Abkhazian"
    AA = "Afar"
    AF = "Afrikaans"
    AK = "Akan"
    SQ = "Albanian"
    AM = "Amharic"
    AR = "Arabic"
    AN = "Aragonese"
    HY = "Armenian"
    AS = "Assamese"
    AV = "Avaric"
    AE = "Avestan"
    AY = "Aymara"
    AZ = "Azerbaijani"
    BM = "Bambara"
    BA = "Bashkir"
    EU = "Basque"
    BE = "Belarusian"
    BN = "Bengali"
    BH = "Bihari languages"
    BI = "Bislama"
    BS = "Bosnian"
    BR = "Breton"
    BG = "Bulgarian"
    MY = "Burmese"
    CA = "Catalan, Valencian"
    CH = "Chamorro"
    CE = "Chechen"
    NY = "Chichewa, Chewa, Nyanja"
    ZH = "Chinese"
    CV = "Chuvash"
    KW = "Cornish"
    CO = "Corsican"
    CR = "Cree"
    HR = "Croatian"
    CS = "Czech"
    DA = "Danish"
    DV = "Divehi, Dhivehi, Maldivian"
    NL = "Dutch, Flemish"
    DZ = "Dzongkha"
    EN = "English"
    EO = "Esperanto"
    ET = "Estonian"
    EE = "Ewe"
    FO = "Faroese"
    FJ = "Fijian"
    FI = "Finnish"
    FR = "French"
    FF = "Fulah"
    GL = "Galician"
    KA = "Georgian"
    DE = "German"
    EL = "Greek, Modern (1453-)"
    GN = "Guarani"
    GU = "Gujarati"
    HT = "Haitian, Haitian Creole"
    HA = "Hausa"
    HE = "Hebrew"
    HZ = "Herero"
    HI = "Hindi"
    HO = "Hiri Motu"
    HU = "Hungarian"
    IA = "Interlingua (International Auxiliary Language Association)"
    ID = "Indonesian"
    IE = "Interlingue, Occidental"
    GA = "Irish"
    IG = "Igbo"
    IK = "Inupiaq"
    IO = "Ido"
    IS = "Icelandic"
    IT = "Italian"
    IU = "Inuktitut"
    JA = "Japanese"
    JV = "Javanese"
    KL = "Kalaallisut, Greenlandic"
    KN = "Kannada"
    KR = "Kanuri"
    KS = "Kashmiri"
    KK = "Kazakh"
    KM = "Central Khmer"
    KI = "Kikuyu, Gikuyu"
    RW = "Kinyarwanda"
    KY = "Kirghiz, Kyrgyz"
    KV = "Komi"
    KG = "Kongo"
    KO = "Korean"
    KU = "Kurdish"
    KJ = "Kuanyama, Kwanyama"
    LA = "Latin"
    LB = "Luxembourgish, Letzeburgesch"
    LG = "Ganda"
    LI = "Limburgan, Limburger, Limburgish"
    LN = "Lingala"
    LO = "Lao"
    LT = "Lithuanian"
    LU = "Luba-Katanga"
    LV = "Latvian"
    GV = "Manx"
    MK = "Macedonian"
    MG = "Malagasy"
    MS = "Malay"
    ML = "Malayalam"
    MT = "Maltese"
    MI = "Maori"
    MR = "Marathi"
    MH = "Marshallese"
    MN = "Mongolian"
    NA = "Nauru"
    NV = "Navajo, Navaho"
    ND = "North Ndebele"
    NE = "Nepali"
    NG = "Ndonga"
    NB = "Norwegian Bokm√•l"
    NN = "Norwegian Nynorsk"
    NO = "Norwegian"
    II = "Sichuan Yi, Nuosu"
    NR = "South Ndebele"
    OC = "Occitan"
    OJ = "Ojibwa"
    CU = "Church¬†Slavic, Old Slavonic, Church Slavonic, Old Bulgarian, Old¬†Church¬†Slavonic"
    OM = "Oromo"
    OR = "Oriya"
    OS = "Ossetian, Ossetic"
    PA = "Panjabi, Punjabi"
    PI = "Pali"
    FA = "Persian"
    PL = "Polish"
    PS = "Pashto, Pushto"
    PT = "Portuguese"
    QU = "Quechua"
    RM = "Romansh"
    RN = "Rundi"
    RO = "Romanian, Moldavian, Moldovan"
    RU = "Russian"
    SA = "Sanskrit"
    SC = "Sardinian"
    SD = "Sindhi"
    SE = "Northern Sami"
    SM = "Samoan"
    SG = "Sango"
    SR = "Serbian"
    GD = "Gaelic, Scottish Gaelic"
    SN = "Shona"
    SI = "Sinhala, Sinhalese"
    SK = "Slovak"
    SL = "Slovenian"
    SO = "Somali"
    ST = "Southern Sotho"
    ES = "Spanish, Castilian"
    SU = "Sundanese"
    SW = "Swahili"
    SS = "Swati"
    SV = "Swedish"
    TA = "Tamil"
    TE = "Telugu"
    TG = "Tajik"
    TH = "Thai"
    TI = "Tigrinya"
    BO = "Tibetan"
    TK = "Turkmen"
    TL = "Tagalog"
    TN = "Tswana"
    TO = "Tonga (Tonga Islands)"
    TR = "Turkish"
    TS = "Tsonga"
    TT = "Tatar"
    TW = "Twi"
    TY = "Tahitian"
    UG = "Uighur, Uyghur"
    UK = "Ukrainian"
    UR = "Urdu"
    UZ = "Uzbek"
    VE = "Venda"
    VI = "Vietnamese"
    VO = "Volap√ºk"
    WA = "Walloon"
    CY = "Welsh"
    WO = "Wolof"
    FY = "Western Frisian"
    XH = "Xhosa"
    YI = "Yiddish"
    YO = "Yoruba"
    ZA = "Zhuang, Chuang"
    ZU = "Zulu"
    XX = "Undefined"

if __name__ == "__main__":
    print(Language["ZUR"])
