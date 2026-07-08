/** Normaliza nome de país da base Gold para chave de lookup. */
export function normalizeCountryKey(name: string): string {
  return name
    .trim()
    .toUpperCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
}

/** Mapeamento extensível: nome normalizado (sem acentos) → ISO 3166-1 alpha-2. */
const COUNTRY_NAME_TO_ISO2: Record<string, string> = {
  AFEGANISTAO: 'AF',
  'AFRICA DO SUL': 'ZA',
  ALBANIA: 'AL',
  ALEMANHA: 'DE',
  ANDORRA: 'AD',
  ANGOLA: 'AO',
  'ANTIGUA E BARBUDA': 'AG',
  ARGENTINA: 'AR',
  ARGELIA: 'DZ',
  ARMENIA: 'AM',
  ARUBA: 'AW',
  'ARABIA SAUDITA': 'SA',
  AUSTRALIA: 'AU',
  AUSTRIA: 'AT',
  AZERBAIJAO: 'AZ',
  BAHAMAS: 'BS',
  BANGLADESH: 'BD',
  BARBADOS: 'BB',
  BAREIN: 'BH',
  BELGICA: 'BE',
  BELIZE: 'BZ',
  BENIN: 'BJ',
  BIELORRUSSIA: 'BY',
  BOLIVIA: 'BO',
  BOTSWANA: 'BW',
  BRASIL: 'BR',
  'NATURALIDADE BRASILEIRA': 'BR',
  BRUNEI: 'BN',
  BULGARIA: 'BG',
  'BURKINA FASO': 'BF',
  BURUNDI: 'BI',
  BUTAO: 'BT',
  'BOSNIA-HERZEGOVINA': 'BA',
  'CABO VERDE': 'CV',
  CAMAROES: 'CM',
  CAMBOJA: 'KH',
  CANADA: 'CA',
  CATAR: 'QA',
  CHADE: 'TD',
  CHILE: 'CL',
  CHINA: 'CN',
  CHIPRE: 'CY',
  'CINGAPURA-SINGAPURA': 'SG',
  COLOMBIA: 'CO',
  'COMORES, ILHAS': 'KM',
  CONGO: 'CG',
  'COREIA DO NORTE': 'KP',
  'COREIA DO SUL': 'KR',
  'COSTA DO MARFIM': 'CI',
  'COSTA RICA': 'CR',
  CROACIA: 'HR',
  CUBA: 'CU',
  DINAMARCA: 'DK',
  DOMINICA: 'DM',
  'EL SALVADOR': 'SV',
  EGITO: 'EG',
  'EMIRADOS ARABES UNIDOS': 'AE',
  EQUADOR: 'EC',
  ESLOVAQUIA: 'SK',
  ESLOVENIA: 'SI',
  ESPANHA: 'ES',
  'ESTADOS UNIDOS': 'US',
  ESTONIA: 'EE',
  ETIOPIA: 'ET',
  FILIPINAS: 'PH',
  FINLANDIA: 'FI',
  FRANCA: 'FR',
  GANA: 'GH',
  GEORGIA: 'GE',
  GRECIA: 'GR',
  GUATEMALA: 'GT',
  GUIANA: 'GY',
  'GUIANA FRANCESA': 'GF',
  HAITI: 'HT',
  HONDURAS: 'HN',
  HUNGRIA: 'HU',
  INDIA: 'IN',
  INDONESIA: 'ID',
  IRA: 'IR',
  IRAQUE: 'IQ',
  IRLANDA: 'IE',
  ISRAEL: 'IL',
  ITALIA: 'IT',
  JAMAICA: 'JM',
  JAPAO: 'JP',
  JORDANIA: 'JO',
  KENYA: 'KE',
  LIBANO: 'LB',
  LIBIA: 'LY',
  LITUANIA: 'LT',
  LUXEMBURGO: 'LU',
  MADAGASCAR: 'MG',
  MALASIA: 'MY',
  MALI: 'ML',
  MARROCOS: 'MA',
  MEXICO: 'MX',
  MOCAMBIQUE: 'MZ',
  MONGOLIA: 'MN',
  NEPAL: 'NP',
  NICARAGUA: 'NI',
  NIGERIA: 'NG',
  NORUEGA: 'NO',
  'NOVA ZELANDIA': 'NZ',
  OMAN: 'OM',
  'PAISES BAIXOS': 'NL',
  PAKISTAO: 'PK',
  PALESTINA: 'PS',
  PANAMA: 'PA',
  PARAGUAI: 'PY',
  PERU: 'PE',
  POLONIA: 'PL',
  PORTUGAL: 'PT',
  'PORTO RICO': 'PR',
  'REINO UNIDO': 'GB',
  'REPUBLICA DOMINICANA': 'DO',
  'REPUBLICA TCHECA': 'CZ',
  ROMENIA: 'RO',
  RUSSIA: 'RU',
  SENEGAL: 'SN',
  SIRIA: 'SY',
  SOMALIA: 'SO',
  'SRI LANKA': 'LK',
  SUDAO: 'SD',
  SUECIA: 'SE',
  SUICA: 'CH',
  SURINAME: 'SR',
  TAILANDIA: 'TH',
  TAIWAN: 'TW',
  TANZANIA: 'TZ',
  TOGO: 'TG',
  'TRINDADE E TOBAGO': 'TT',
  TUNISIA: 'TN',
  TURQUIA: 'TR',
  UCRANIA: 'UA',
  UGANDA: 'UG',
  URUGUAI: 'UY',
  UZBEQUISTAO: 'UZ',
  VENEZUELA: 'VE',
  VIETNA: 'VN',
  ZIMBABUE: 'ZW',
}

export function countryNameToIso2(countryName: string): string | null {
  const key = normalizeCountryKey(countryName)
  if (!key) return null
  return COUNTRY_NAME_TO_ISO2[key] ?? null
}

export function getCountryInitials(countryName: string): string {
  const cleaned = countryName.trim()
  if (!cleaned) return '??'
  const parts = cleaned.split(/\s+/).filter((p) => p.length > 0)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0] ?? ''}${parts[1][0] ?? ''}`.toUpperCase()
}

/** URL de bandeira circular SVG (circle-flags). */
export function circleFlagSvgUrl(iso2: string): string {
  return `https://hatscripts.github.io/circle-flags/flags/${iso2.toLowerCase()}.svg`
}

/** URL de bandeira retangular (flagcdn). */
export function rectangularFlagUrl(iso2: string, width = 320): string {
  return `https://flagcdn.com/w${width}/${iso2.toLowerCase()}.png`
}
