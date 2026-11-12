#!/usr/bin/env python3
"""L3 country parsing for the ENT attention-burden census (signed work
report v1, section 4 L3): parse the first-author affiliation string of
every pulled record to a country/region unit.

Method = dictionary parsing only, in four declared layers; nothing is
imputed. A record with no first-author affiliation string is 'missing'
(reported, never filled); a record no layer can place is 'unparsed'.

Layer 1 'name'   Country names and variants (English + the native forms
                 actually observed in the corpus: Brasil, España,
                 Deutschland, México, Italia, Belgique, Tunisie, Maroc,
                 Turkiye, Slovak Republic, ...). The match that ENDS
                 LAST in the string wins (affiliations conventionally
                 end with the country); longest alias wins ties.
Layer 2 'region' Sub-country region names competing on the same
                 rightmost footing: US states -> USA, Canadian
                 provinces -> CAN. Two-letter codes are accepted only
                 as an uppercase trailing comma segment (US state /
                 Canadian province abbreviations), as are ISO alpha-3
                 country codes in the same position ('code').
Layer 3 'city'   A finite, corpus-driven city dictionary, applied only
                 when layers 1-2 found nothing anywhere in the string.
                 Every entry is an unambiguous city for this corpus and
                 is listed in data_l3/geo/COUNTRY_PARSE_QA.md.

Conventions: England/Scotland/Wales/Northern Ireland -> United Kingdom
(GBD location unit). Hong Kong / Taiwan / Macao stay separate units as
printed; any GBD-side merge is an L2 join decision, not done here.
'Georgia' is disambiguated by city context (Tbilisi -> GEO country;
Atlanta/Augusta -> USA). 'New England' is protected from the England
alias. Emails are stripped before matching.

Outputs under data_l3/geo/:
  records_country.csv   epmc_id, area, period, iso3, country, status, via
  country_counts.csv    area x period x iso3 counts (parsed only)
  parse_coverage.csv    area x period totals by status and layer
  unparsed_top_tails.csv  most frequent trailing segments still unparsed
"""
import csv, glob, json, os, re, collections

PARTS = "data_l3/parts"
OUT = "data_l3/geo"

# alias (lowercase) -> (iso3, canonical)
_RAW = {
 "china": ("CHN", "China"), "people's republic of china": ("CHN", "China"),
 "p.r. china": ("CHN", "China"), "pr china": ("CHN", "China"),
 "p.r.c.": ("CHN", "China"),
 "united states": ("USA", "United States"), "usa": ("USA", "United States"),
 "u.s.a.": ("USA", "United States"), "u.s.a": ("USA", "United States"),
 "united states of america": ("USA", "United States"),
 "u.s.": ("USA", "United States"),
 "united kingdom": ("GBR", "United Kingdom"), "uk": ("GBR", "United Kingdom"),
 "u.k.": ("GBR", "United Kingdom"), "england": ("GBR", "United Kingdom"),
 "scotland": ("GBR", "United Kingdom"), "wales": ("GBR", "United Kingdom"),
 "northern ireland": ("GBR", "United Kingdom"),
 "great britain": ("GBR", "United Kingdom"),
 "japan": ("JPN", "Japan"), "italy": ("ITA", "Italy"),
 "italia": ("ITA", "Italy"),
 "india": ("IND", "India"), "germany": ("DEU", "Germany"),
 "deutschland": ("DEU", "Germany"),
 "france": ("FRA", "France"),
 "south korea": ("KOR", "South Korea"), "republic of korea": ("KOR", "South Korea"),
 "korea": ("KOR", "South Korea"),
 "north korea": ("PRK", "North Korea"), "dprk": ("PRK", "North Korea"),
 "australia": ("AUS", "Australia"), "canada": ("CAN", "Canada"),
 "turkey": ("TUR", "Turkey"), "türkiye": ("TUR", "Turkey"),
 "turkiye": ("TUR", "Turkey"),
 "brazil": ("BRA", "Brazil"), "brasil": ("BRA", "Brazil"),
 "spain": ("ESP", "Spain"), "españa": ("ESP", "Spain"),
 "espana": ("ESP", "Spain"),
 "iran": ("IRN", "Iran"), "islamic republic of iran": ("IRN", "Iran"),
 "netherlands": ("NLD", "Netherlands"), "the netherlands": ("NLD", "Netherlands"),
 "holland": ("NLD", "Netherlands"),
 "poland": ("POL", "Poland"), "sweden": ("SWE", "Sweden"),
 "belgium": ("BEL", "Belgium"), "belgique": ("BEL", "Belgium"),
 "israel": ("ISR", "Israel"),
 "switzerland": ("CHE", "Switzerland"), "greece": ("GRC", "Greece"),
 "finland": ("FIN", "Finland"), "denmark": ("DNK", "Denmark"),
 "saudi arabia": ("SAU", "Saudi Arabia"),
 "kingdom of saudi arabia": ("SAU", "Saudi Arabia"),
 "thailand": ("THA", "Thailand"),
 "austria": ("AUT", "Austria"), "egypt": ("EGY", "Egypt"),
 "portugal": ("PRT", "Portugal"), "malaysia": ("MYS", "Malaysia"),
 "taiwan": ("TWN", "Taiwan"), "hong kong": ("HKG", "Hong Kong"),
 "republic of china": ("TWN", "Taiwan"),
 "macao": ("MAC", "Macao"), "macau": ("MAC", "Macao"),
 "mexico": ("MEX", "Mexico"), "méxico": ("MEX", "Mexico"),
 "mexicanos": ("MEX", "Mexico"),
 "argentina": ("ARG", "Argentina"),
 "chile": ("CHL", "Chile"), "colombia": ("COL", "Colombia"),
 "peru": ("PER", "Peru"), "venezuela": ("VEN", "Venezuela"),
 "ecuador": ("ECU", "Ecuador"), "bolivia": ("BOL", "Bolivia"),
 "paraguay": ("PRY", "Paraguay"), "uruguay": ("URY", "Uruguay"),
 "cuba": ("CUB", "Cuba"), "dominican republic": ("DOM", "Dominican Republic"),
 "puerto rico": ("PRI", "Puerto Rico"), "jamaica": ("JAM", "Jamaica"),
 "trinidad and tobago": ("TTO", "Trinidad and Tobago"),
 "costa rica": ("CRI", "Costa Rica"), "panama": ("PAN", "Panama"),
 "guatemala": ("GTM", "Guatemala"), "honduras": ("HND", "Honduras"),
 "el salvador": ("SLV", "El Salvador"), "nicaragua": ("NIC", "Nicaragua"),
 "russia": ("RUS", "Russia"), "russian federation": ("RUS", "Russia"),
 "ukraine": ("UKR", "Ukraine"), "belarus": ("BLR", "Belarus"),
 "czech republic": ("CZE", "Czech Republic"), "czechia": ("CZE", "Czech Republic"),
 "slovakia": ("SVK", "Slovakia"), "slovak republic": ("SVK", "Slovakia"),
 "hungary": ("HUN", "Hungary"),
 "romania": ("ROU", "Romania"), "bulgaria": ("BGR", "Bulgaria"),
 "croatia": ("HRV", "Croatia"), "serbia": ("SRB", "Serbia"),
 "slovenia": ("SVN", "Slovenia"), "bosnia and herzegovina": ("BIH", "Bosnia and Herzegovina"),
 "montenegro": ("MNE", "Montenegro"), "north macedonia": ("MKD", "North Macedonia"),
 "macedonia": ("MKD", "North Macedonia"), "albania": ("ALB", "Albania"),
 "estonia": ("EST", "Estonia"), "latvia": ("LVA", "Latvia"),
 "lithuania": ("LTU", "Lithuania"), "ireland": ("IRL", "Ireland"),
 "iceland": ("ISL", "Iceland"), "norway": ("NOR", "Norway"),
 "luxembourg": ("LUX", "Luxembourg"), "malta": ("MLT", "Malta"),
 "cyprus": ("CYP", "Cyprus"), "georgia": ("GEO", "Georgia"),
 "armenia": ("ARM", "Armenia"), "azerbaijan": ("AZE", "Azerbaijan"),
 "kazakhstan": ("KAZ", "Kazakhstan"), "uzbekistan": ("UZB", "Uzbekistan"),
 "kyrgyzstan": ("KGZ", "Kyrgyzstan"), "tajikistan": ("TJK", "Tajikistan"),
 "turkmenistan": ("TKM", "Turkmenistan"), "moldova": ("MDA", "Moldova"),
 "pakistan": ("PAK", "Pakistan"), "bangladesh": ("BGD", "Bangladesh"),
 "sri lanka": ("LKA", "Sri Lanka"), "nepal": ("NPL", "Nepal"),
 "myanmar": ("MMR", "Myanmar"), "burma": ("MMR", "Myanmar"),
 "vietnam": ("VNM", "Vietnam"), "viet nam": ("VNM", "Vietnam"),
 "cambodia": ("KHM", "Cambodia"), "laos": ("LAO", "Laos"),
 "indonesia": ("IDN", "Indonesia"), "philippines": ("PHL", "Philippines"),
 "singapore": ("SGP", "Singapore"), "brunei": ("BRN", "Brunei"),
 "mongolia": ("MNG", "Mongolia"), "bhutan": ("BTN", "Bhutan"),
 "maldives": ("MDV", "Maldives"), "afghanistan": ("AFG", "Afghanistan"),
 "iraq": ("IRQ", "Iraq"), "syria": ("SYR", "Syria"),
 "syrian arab republic": ("SYR", "Syria"),
 "lebanon": ("LBN", "Lebanon"), "jordan": ("JOR", "Jordan"),
 "yemen": ("YEM", "Yemen"), "oman": ("OMN", "Oman"),
 "united arab emirates": ("ARE", "United Arab Emirates"),
 "uae": ("ARE", "United Arab Emirates"), "qatar": ("QAT", "Qatar"),
 "kuwait": ("KWT", "Kuwait"), "bahrain": ("BHR", "Bahrain"),
 "palestine": ("PSE", "Palestine"), "palestinian territories": ("PSE", "Palestine"),
 "south africa": ("ZAF", "South Africa"), "nigeria": ("NGA", "Nigeria"),
 "kenya": ("KEN", "Kenya"), "ethiopia": ("ETH", "Ethiopia"),
 "ghana": ("GHA", "Ghana"), "tanzania": ("TZA", "Tanzania"),
 "united republic of tanzania": ("TZA", "Tanzania"),
 "uganda": ("UGA", "Uganda"), "morocco": ("MAR", "Morocco"),
 "maroc": ("MAR", "Morocco"),
 "algeria": ("DZA", "Algeria"), "tunisia": ("TUN", "Tunisia"),
 "tunisie": ("TUN", "Tunisia"),
 "libya": ("LBY", "Libya"), "sudan": ("SDN", "Sudan"),
 "angola": ("AGO", "Angola"), "mozambique": ("MOZ", "Mozambique"),
 "zambia": ("ZMB", "Zambia"), "zimbabwe": ("ZWE", "Zimbabwe"),
 "cameroon": ("CMR", "Cameroon"), "senegal": ("SEN", "Senegal"),
 "mali": ("MLI", "Mali"), "madagascar": ("MDG", "Madagascar"),
 "malawi": ("MWI", "Malawi"), "rwanda": ("RWA", "Rwanda"),
 "burkina faso": ("BFA", "Burkina Faso"), "niger": ("NER", "Niger"),
 "chad": ("TCD", "Chad"), "somalia": ("SOM", "Somalia"),
 "eritrea": ("ERI", "Eritrea"), "mauritania": ("MRT", "Mauritania"),
 "benin": ("BEN", "Benin"), "sierra leone": ("SLE", "Sierra Leone"),
 "togo": ("TGO", "Togo"), "congo": ("COG", "Congo"),
 "democratic republic of the congo": ("COD", "DR Congo"),
 "gabon": ("GAB", "Gabon"), "namibia": ("NAM", "Namibia"),
 "botswana": ("BWA", "Botswana"), "lesotho": ("LSO", "Lesotho"),
 "eswatini": ("SWZ", "Eswatini"), "swaziland": ("SWZ", "Eswatini"),
 "mauritius": ("MUS", "Mauritius"), "guinea": ("GIN", "Guinea"),
 "ivory coast": ("CIV", "Ivory Coast"), "côte d'ivoire": ("CIV", "Ivory Coast"),
 "liberia": ("LBR", "Liberia"), "gambia": ("GMB", "Gambia"),
 "new zealand": ("NZL", "New Zealand"), "fiji": ("FJI", "Fiji"),
 "papua new guinea": ("PNG", "Papua New Guinea"),
 "new caledonia": ("NCL", "New Caledonia"),
 "french polynesia": ("PYF", "French Polynesia"),
 "guam": ("GUM", "Guam"),
}
_ISO3 = {}
for _iso, _name in _RAW.values():
    _ISO3.setdefault(_iso, _name)

# region name -> (iso3, canonical country)
_REGIONS = {}
for _s in ["alabama", "alaska", "arizona", "arkansas", "california",
 "colorado", "connecticut", "delaware", "florida", "hawaii", "idaho",
 "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
 "maine", "maryland", "massachusetts", "michigan", "minnesota",
 "mississippi", "missouri", "montana", "nebraska", "nevada",
 "new hampshire", "new jersey", "new mexico", "new york",
 "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
 "pennsylvania", "rhode island", "south carolina", "south dakota",
 "tennessee", "texas", "utah", "vermont", "virginia", "washington",
 "west virginia", "wisconsin", "wyoming", "district of columbia"]:
    _REGIONS[_s] = ("USA", "United States")
_REGIONS["georgia"] = ("USA", "United States")  # country dict also has it;
# disambiguation happens after the rightmost contest (see parse()).
for _p in ["ontario", "quebec", "québec", "british columbia", "alberta",
 "manitoba", "saskatchewan", "nova scotia", "new brunswick",
 "newfoundland", "prince edward island"]:
    _REGIONS[_p] = ("CAN", "Canada")
_REGION_NAMES = set(_REGIONS)

STATE_ABBR = {"AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","IA",
 "ID","IL","IN","KS","KY","LA","MA","MD","ME","MI","MN","MO","MS","MT",
 "NC","ND","NE","NH","NJ","NM","NV","NY","OH","OK","OR","PA","RI","SC",
 "SD","TN","TX","UT","VA","VT","WA","WI","WV","WY","DC"}
STATE_ABBR_DOT = {"ill", "mass", "calif", "colo", "conn", "mich", "minn",
 "wis", "va", "wash", "ore", "ariz", "okla", "tenn", "ala", "fla", "tex",
 "pa", "ark", "miss", "kan", "neb", "nev", "ut", "wyo", "mont", "ida"}
PROV_ABBR = {"ON": "CAN", "QC": "CAN", "BC": "CAN", "AB": "CAN",
 "MB": "CAN", "SK": "CAN", "NS": "CAN", "NB": "CAN", "NL": "CAN",
 "PE": "CAN"}
AUS_ABBR = {"NSW": "AUS", "VIC": "AUS", "QLD": "AUS", "TAS": "AUS",
 "NT": "AUS"}

# city (lowercase) -> (iso3, canonical); finite corpus-driven list,
# each entry unambiguous in this corpus; see COUNTRY_PARSE_QA.md.
_CITIES = {
 "tokyo": ("JPN", "Japan"), "osaka": ("JPN", "Japan"),
 "nagoya": ("JPN", "Japan"), "kyoto": ("JPN", "Japan"),
 "fukuoka": ("JPN", "Japan"), "sapporo": ("JPN", "Japan"),
 "sendai": ("JPN", "Japan"), "hiroshima": ("JPN", "Japan"),
 "kobe": ("JPN", "Japan"), "yokohama": ("JPN", "Japan"),
 "beijing": ("CHN", "China"), "shanghai": ("CHN", "China"),
 "guangzhou": ("CHN", "China"), "shenzhen": ("CHN", "China"),
 "wuhan": ("CHN", "China"), "changsha": ("CHN", "China"),
 "chengdu": ("CHN", "China"), "chongqing": ("CHN", "China"),
 "nanjing": ("CHN", "China"), "hangzhou": ("CHN", "China"),
 "xian": ("CHN", "China"), "xi'an": ("CHN", "China"),
 "shenyang": ("CHN", "China"), "tianjin": ("CHN", "China"),
 "harbin": ("CHN", "China"), "kunming": ("CHN", "China"),
 "taipei": ("TWN", "Taiwan"), "taichung": ("TWN", "Taiwan"),
 "kaohsiung": ("TWN", "Taiwan"), "tainan": ("TWN", "Taiwan"),
 "seoul": ("KOR", "South Korea"), "busan": ("KOR", "South Korea"),
 "incheon": ("KOR", "South Korea"), "daegu": ("KOR", "South Korea"),
 "paris": ("FRA", "France"), "strasbourg": ("FRA", "France"),
 "lyon": ("FRA", "France"), "marseille": ("FRA", "France"),
 "bordeaux": ("FRA", "France"), "nantes": ("FRA", "France"),
 "toulouse": ("FRA", "France"), "lille": ("FRA", "France"),
 "montpellier": ("FRA", "France"),
 "madrid": ("ESP", "Spain"), "barcelona": ("ESP", "Spain"),
 "valencia": ("ESP", "Spain"), "granada": ("ESP", "Spain"),
 "sevilla": ("ESP", "Spain"), "seville": ("ESP", "Spain"),
 "bilbao": ("ESP", "Spain"), "zaragoza": ("ESP", "Spain"),
 "roma": ("ITA", "Italy"), "rome": ("ITA", "Italy"),
 "milano": ("ITA", "Italy"), "milan": ("ITA", "Italy"),
 "napoli": ("ITA", "Italy"), "naples": ("ITA", "Italy"),
 "torino": ("ITA", "Italy"), "turin": ("ITA", "Italy"),
 "bologna": ("ITA", "Italy"), "firenze": ("ITA", "Italy"),
 "florence": ("ITA", "Italy"), "genova": ("ITA", "Italy"),
 "genoa": ("ITA", "Italy"), "padova": ("ITA", "Italy"),
 "berlin": ("DEU", "Germany"), "hannover": ("DEU", "Germany"),
 "hamburg": ("DEU", "Germany"), "münchen": ("DEU", "Germany"),
 "munich": ("DEU", "Germany"), "frankfurt": ("DEU", "Germany"),
 "köln": ("DEU", "Germany"), "cologne": ("DEU", "Germany"),
 "heidelberg": ("DEU", "Germany"), "freiburg": ("DEU", "Germany"),
 "tübingen": ("DEU", "Germany"), "göttingen": ("DEU", "Germany"),
 "amsterdam": ("NLD", "Netherlands"), "utrecht": ("NLD", "Netherlands"),
 "rotterdam": ("NLD", "Netherlands"), "leiden": ("NLD", "Netherlands"),
 "groningen": ("NLD", "Netherlands"), "maastricht": ("NLD", "Netherlands"),
 "nijmegen": ("NLD", "Netherlands"),
 "zürich": ("CHE", "Switzerland"), "zurich": ("CHE", "Switzerland"),
 "genève": ("CHE", "Switzerland"), "geneva": ("CHE", "Switzerland"),
 "lausanne": ("CHE", "Switzerland"), "bern": ("CHE", "Switzerland"),
 "basel": ("CHE", "Switzerland"),
 "london": ("GBR", "United Kingdom"),
 "budapest": ("HUN", "Hungary"),
 "beograd": ("SRB", "Serbia"), "belgrade": ("SRB", "Serbia"),
 "karachi": ("PAK", "Pakistan"), "lahore": ("PAK", "Pakistan"),
 "islamabad": ("PAK", "Pakistan"),
 "aalborg": ("DNK", "Denmark"), "aarhus": ("DNK", "Denmark"),
 "copenhagen": ("DNK", "Denmark"), "odense": ("DNK", "Denmark"),
 "warszawie": ("POL", "Poland"), "warsaw": ("POL", "Poland"),
 "warszawa": ("POL", "Poland"), "kraków": ("POL", "Poland"),
 "krakow": ("POL", "Poland"), "gdańsk": ("POL", "Poland"),
 "gdansk": ("POL", "Poland"), "poznań": ("POL", "Poland"),
 "poznan": ("POL", "Poland"), "wrocław": ("POL", "Poland"),
 "wroclaw": ("POL", "Poland"),
 "istanbul": ("TUR", "Turkey"), "ankara": ("TUR", "Turkey"),
 "izmir": ("TUR", "Turkey"),
 "tehran": ("IRN", "Iran"), "shiraz": ("IRN", "Iran"),
 "isfahan": ("IRN", "Iran"), "mashhad": ("IRN", "Iran"),
 "tabriz": ("IRN", "Iran"),
 "cairo": ("EGY", "Egypt"), "alexandria": ("EGY", "Egypt"),
 "delhi": ("IND", "India"), "new delhi": ("IND", "India"),
 "mumbai": ("IND", "India"), "chennai": ("IND", "India"),
 "kolkata": ("IND", "India"), "bangalore": ("IND", "India"),
 "bengaluru": ("IND", "India"), "hyderabad": ("IND", "India"),
 "pune": ("IND", "India"), "ahmedabad": ("IND", "India"),
 "são paulo": ("BRA", "Brazil"), "sao paulo": ("BRA", "Brazil"),
 "rio de janeiro": ("BRA", "Brazil"),
 "buenos aires": ("ARG", "Argentina"),
 "santiago": ("CHL", "Chile"),
 "athens": ("GRC", "Greece"), "thessaloniki": ("GRC", "Greece"),
 "stockholm": ("SWE", "Sweden"), "gothenburg": ("SWE", "Sweden"),
 "uppsala": ("SWE", "Sweden"),
 "oslo": ("NOR", "Norway"), "bergen": ("NOR", "Norway"),
 "helsinki": ("FIN", "Finland"), "turku": ("FIN", "Finland"),
 "tampere": ("FIN", "Finland"), "oulu": ("FIN", "Finland"),
 "vienna": ("AUT", "Austria"), "wien": ("AUT", "Austria"),
 "graz": ("AUT", "Austria"), "innsbruck": ("AUT", "Austria"),
 "brussels": ("BEL", "Belgium"), "ghent": ("BEL", "Belgium"),
 "leuven": ("BEL", "Belgium"), "antwerp": ("BEL", "Belgium"),
 "lisbon": ("PRT", "Portugal"), "lisboa": ("PRT", "Portugal"),
 "porto": ("PRT", "Portugal"), "coimbra": ("PRT", "Portugal"),
 "dublin": ("IRL", "Ireland"),
 "reykjavik": ("ISL", "Iceland"),
 "tel aviv": ("ISR", "Israel"), "jerusalem": ("ISR", "Israel"),
 "haifa": ("ISR", "Israel"),
 "riyadh": ("SAU", "Saudi Arabia"), "jeddah": ("SAU", "Saudi Arabia"),
 "bangkok": ("THA", "Thailand"),
 "kuala lumpur": ("MYS", "Malaysia"),
 "jakarta": ("IDN", "Indonesia"),
 "manila": ("PHL", "Philippines"),
 "hanoi": ("VNM", "Vietnam"),
 "dhaka": ("BGD", "Bangladesh"),
 "kathmandu": ("NPL", "Nepal"),
 "colombo": ("LKA", "Sri Lanka"),
 "sydney": ("AUS", "Australia"), "melbourne": ("AUS", "Australia"),
 "brisbane": ("AUS", "Australia"), "perth": ("AUS", "Australia"),
 "adelaide": ("AUS", "Australia"), "canberra": ("AUS", "Australia"),
 "darwin": ("AUS", "Australia"),
 "auckland": ("NZL", "New Zealand"), "wellington": ("NZL", "New Zealand"),
 "christchurch": ("NZL", "New Zealand"), "dunedin": ("NZL", "New Zealand"),
 "moscow": ("RUS", "Russia"),
 "kyiv": ("UKR", "Ukraine"), "kiev": ("UKR", "Ukraine"),
 "minsk": ("BLR", "Belarus"),
 "bucharest": ("ROU", "Romania"), "bucurești": ("ROU", "Romania"),
 "sofia": ("BGR", "Bulgaria"),
 "zagreb": ("HRV", "Croatia"),
 "ljubljana": ("SVN", "Slovenia"),
 "bratislava": ("SVK", "Slovakia"),
 "prague": ("CZE", "Czech Republic"), "praha": ("CZE", "Czech Republic"),
 "brno": ("CZE", "Czech Republic"),
 "tallinn": ("EST", "Estonia"), "tartu": ("EST", "Estonia"),
 "riga": ("LVA", "Latvia"),
 "vilnius": ("LTU", "Lithuania"), "kaunas": ("LTU", "Lithuania"),
 "tbilisi": ("GEO", "Georgia"),
 "yerevan": ("ARM", "Armenia"),
 "baku": ("AZE", "Azerbaijan"),
 "almaty": ("KAZ", "Kazakhstan"),
 "tashkent": ("UZB", "Uzbekistan"),
 "johannesburg": ("ZAF", "South Africa"),
 "cape town": ("ZAF", "South Africa"), "pretoria": ("ZAF", "South Africa"),
 "lagos": ("NGA", "Nigeria"),
 "nairobi": ("KEN", "Kenya"),
 "addis ababa": ("ETH", "Ethiopia"),
 "accra": ("GHA", "Ghana"),
 "tunis": ("TUN", "Tunisia"),
 "algiers": ("DZA", "Algeria"), "alger": ("DZA", "Algeria"),
 "casablanca": ("MAR", "Morocco"), "rabat": ("MAR", "Morocco"),
 "beirut": ("LBN", "Lebanon"),
 "amman": ("JOR", "Jordan"),
 "baghdad": ("IRQ", "Iraq"),
 "damascus": ("SYR", "Syria"),
 "dubai": ("ARE", "United Arab Emirates"),
 "abu dhabi": ("ARE", "United Arab Emirates"),
 "doha": ("QAT", "Qatar"),
 "muscat": ("OMN", "Oman"),
 "ulaanbaatar": ("MNG", "Mongolia"),
}

def _combined(aliases):
    alt = "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True))
    return re.compile(r"(?<![a-zà-ÿ])" + "(?:" + alt + ")" + r"(?![a-zà-ÿ])")

_COUNTRY_RE = _combined(_RAW.keys())
_REGION_RE = _combined(_REGION_NAMES)
_CITY_RE = _combined(_CITIES.keys())
_EMAIL_RE = re.compile(r"\S+@\S+")

def _rightmost(re_, text_l, table):
    best = None
    for m in re_.finditer(text_l):
        key = (m.end(), len(m.group(0)))
        if best is None or key > best[0]:
            best = (key, table[m.group(0)], m.group(0))
    return best

def _segment_fastpath(aff):
    segs = [x.strip(" .") for x in aff.split(",")]
    for seg in reversed(segs[-2:]):
        words = seg.lower().split()
        for k in range(min(4, len(words)), 0, -1):
            cand = " ".join(words[-k:])
            if cand in _RAW:
                return ("country", _RAW[cand], cand)
            if cand in _REGIONS:
                return ("region", _REGIONS[cand], cand)
    return None

def _segment_code(aff):
    segs = [x.strip() for x in aff.split(",")]
    if not segs:
        return None
    last = segs[-1].strip(" .")
    if last in STATE_ABBR:
        return ("USA", "United States")
    if last in PROV_ABBR:
        return ("CAN", "Canada")
    if last in AUS_ABBR:
        return ("AUS", "Australia")
    if len(last) == 3 and last in _ISO3:
        return (last, _ISO3[last])
    if last == "BR":
        return ("BRA", "Brazil")
    if last.lower().strip(".") in STATE_ABBR_DOT:
        return ("USA", "United States")
    return None

def parse(aff):
    if not aff:
        return ("", "", "missing", "")
    aff = _EMAIL_RE.sub("", aff)
    s = aff.replace("New England", "NewEngland")
    sl = s.lower()
    cand = _segment_fastpath(s)
    if cand is None:
        c = _rightmost(_COUNTRY_RE, sl, _RAW)
        r = _rightmost(_REGION_RE, sl, _REGIONS)
        if c and (not r or c[0] >= r[0]):
            cand = ("country", c[1], c[2])
        elif r:
            cand = ("region", r[1], r[2])
    if cand:
        kind, (iso3, name), hit = cand
        if hit == "georgia":
            # Disambiguation by institutional/city clues. Country clues
            # first: 'georgian' (adjective) and Georgian cities; then US
            # clues (Athens/Atlanta/Augusta and the two big Georgia
            # universities). QA found University of Georgia (Athens, GA)
            # records initially landing on GEO without these clues.
            if any(c in sl for c in ("tbilisi", "batumi", "kutaisi",
                                     "tskhaltubo", "rustavi", "georgian")):
                return ("GEO", "Georgia", "parsed", "name")
            if any(c in sl for c in ("athens", "atlanta", "augusta",
                                     "savannah", "macon", "valdosta",
                                     "university of georgia",
                                     "georgia state university",
                                     "georgia institute of technology",
                                     "georgia southern", "emory university")):
                return ("USA", "United States", "parsed", "region")
            if kind == "country":
                return ("GEO", "Georgia", "parsed", "name")
            return ("USA", "United States", "parsed", "region")
        return (iso3, name, "parsed", "name" if kind == "country" else "region")
    code = _segment_code(aff)
    if code:
        return (code[0], code[1], "parsed", "code")
    city = _rightmost(_CITY_RE, sl, _CITIES)
    if city:
        iso3, name = city[1]
        return (iso3, name, "parsed", "city")
    return ("", "", "unparsed", "")

def main():
    os.makedirs(OUT, exist_ok=True)
    counts = collections.Counter()
    coverage = collections.Counter()
    tails = collections.Counter()
    rows_out = []
    for path in sorted(glob.glob(os.path.join(PARTS, "*.jsonl"))):
        base = os.path.basename(path)[:-6]
        area, period = base.rsplit("_", 1)
        for line in open(path):
            r = json.loads(line)
            # Signed design: FIRST-author affiliation only. The
            # any_affiliation fallback pulled for QC is never parsed.
            aff_used = r["first_author_affiliation"]
            iso3, name, status, via = parse(aff_used)
            coverage[(area, period, "records")] += 1
            if aff_used:
                coverage[(area, period, "with_aff")] += 1
            coverage[(area, period, status)] += 1
            if via:
                coverage[(area, period, "via_" + via)] += 1
            if status == "parsed":
                counts[(area, period, iso3, name)] += 1
            elif status == "unparsed":
                tails[aff_used.split(",")[-1].strip()] += 1
            rows_out.append((r["epmc_id"], area, period, iso3, name, status, via))
    with open(os.path.join(OUT, "records_country.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["epmc_id", "area", "period", "iso3", "country", "status", "via"])
        w.writerows(rows_out)
    with open(os.path.join(OUT, "country_counts.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["area", "period", "iso3", "country", "n"])
        for (area, period, iso3, name), n in sorted(counts.items()):
            w.writerow([area, period, iso3, name, n])
    with open(os.path.join(OUT, "parse_coverage.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["area", "period", "records", "with_aff", "parsed",
                    "unparsed", "missing", "via_name", "via_region",
                    "via_code", "via_city"])
        keys = sorted({(a, p) for (a, p, _) in coverage})
        for (a, p) in keys:
            w.writerow([a, p] + [coverage[(a, p, k)] for k in
                        ("records", "with_aff", "parsed", "unparsed",
                         "missing", "via_name", "via_region", "via_code",
                         "via_city")])
    with open(os.path.join(OUT, "unparsed_top_tails.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tail_segment", "n"])
        for tail, n in tails.most_common(300):
            w.writerow([tail, n])
    tot = {k: sum(v for (_, _, kk), v in coverage.items() if kk == k)
           for k in ("records", "with_aff", "parsed", "unparsed", "missing",
                     "via_name", "via_region", "via_code", "via_city")}
    print(f"records {tot['records']}  with_aff {tot['with_aff']}  "
          f"parsed {tot['parsed']} ({100*tot['parsed']/max(tot['with_aff'],1):.2f}% of with-aff)  "
          f"unparsed {tot['unparsed']}  missing {tot['missing']}  "
          f"via name {tot['via_name']} region {tot['via_region']} "
          f"code {tot['via_code']} city {tot['via_city']}")

if __name__ == "__main__":
    main()
