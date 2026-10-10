"""Builds external_facts.csv (schema from exports): fact_id, claim, date, source_url, publisher, accessed, used_in_scenario_ids, confidence, channel.
G-ids are new to this study; A/B/C ids are reused verbatim from exports/external_facts.csv (not re-researched)."""
from pathlib import Path
import pandas as pd

OUT = Path(__file__).resolve().parent
ACC = "2026-10-05"
G = []


def f(fid, claim, date, url, pub, conf, channel, used="", url2=None, pub2=None):
    G.append(dict(fact_id=fid, claim=claim, date=date, source_url=url + (f" ; {url2}" if url2 else ""), publisher=pub + (f" ; {pub2}" if pub2 else ""),
                  accessed=ACC, used_in_scenario_ids=used, confidence=conf, channel=channel))


EXTRA = []   # filled by build() from research CSVs


def build(extra_rows=None, reuse_ids=()):
    rows = list(G) + list(extra_rows or [])
    X = pd.read_csv(OUT.parent / "exports" / "external_facts.csv")
    R = X[X.fact_id.isin(reuse_ids)].copy()
    R["claim"] = "[reused from exports] " + R.claim
    df = pd.concat([pd.DataFrame(rows), R], ignore_index=True)
    df.to_csv(OUT / "external_facts.csv", index=False)
    return df


R = OUT / "research"
f("G01", "2026 Chamber (513) by party: PL 121, PT 70, União 46, PSD 43, PP 41, Republicanos 41, MDB 36, Podemos 27, PSB 15, PSOL 14, PCdoB 11, PSDB 11, Novo 10, PV 7, PDT 6, PRD 5, Avante 5, Solidariedade 2, Rede 1, Missão 1 (sum 513); identical to the plan's list.",
  "2026-10-05", "https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip", "TSE open data (candidates marked elected, file generated 2026-10-05 10:14)", "high", "Congress", "all",
  "https://www.camara.leg.br/noticias/1309429-veja-a-lista-dos-513-deputados-federais-eleitos-por-estado-e-por-partido", "Agência Câmara (list of 513 by name/party)")
f("G02", "2026 Senate: 54 seats contested — PL 19, MDB 7, PT 6, PP/PSB/União/Novo 3 each, Republicanos/PSD/PSDB/Podemos 2 each, Rede/PDT 1 each (TSE per-state results, 100% totalised).",
  "2026-10-05", "https://resultados.tse.jus.br/oficial/ele2026/6259/dados/sp/sp-c0005-e006259-u.json", "TSE results (27 UF files)", "high", "Congress", "all",
  "https://www.congressoemfoco.com.br/noticia/122752/pl-conquista-19-das-54-vagas-no-senado-veja-os-senadores-eleitos", "Congresso em Foco")
f("G03", "Senate composition from 1 Feb 2027 (81): PL 28, PT 9, MDB 8, PP 6, Republicanos 6, PSD 5, União 5, PSB 4, Novo 3, Podemos 2, PSDB 2, Rede 1, PDT 1, no party 1. English Wikipedia shows PL 29 and no unaffiliated senator (one suplente's affiliation) — the 41/49 arithmetic is unchanged either way.",
  "2026-10-05", "https://agenciabrasil.ebc.com.br/politica/noticia/2026-10/pl-elege-19-senadores-e-soma-28-mdb-conquista-sete-vagas-e-pt-seis", "Agência Brasil", "high", "Congress", "all",
  "https://www.cnnbrasil.com.br/eleicoes/divisao-bancada-senado/", "CNN Brasil")
f("G04", "PL 28 is the largest start-of-legislature Senate bancada since the 1988 Constitution; previous record PMDB 27 at the start of 1999 (Senate 1999 report confirms PMDB 27).",
  "2026-10-04", "https://www12.senado.leg.br/noticias/materias/2026/10/04/pl-tera-maior-bancada-em-inicio-de-legislatura-no-senado-desde-1988", "Senado Notícias", "high", "Congress", "all",
  "https://www.senado.gov.br/Relatorios_SGM/RelPresi/1999/008-partidos.pdf", "Senado Relatório da Presidência 1999")
f("G05", "EU–Mercosur: signed 2026-01-17; Senate approved unanimously 2026-03-04; Decreto Legislativo 14/2026 on 2026-03-17; promulgated by Decreto 12.953 of 2026-04-28; provisionally applied from 2026-05-01.",
  "2026-04-28", "https://www.poder360.com.br/poder-congresso/congresso-promulga-acordo-entre-mercosul-e-uniao-europeia/", "Poder360", "high", "C6/C9/C10", "Lula IV|best|EU;Flávio|best|EU",
  "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/decreto/D12953.htm", "Planalto (Decreto 12.953/2026)")
f("G06", "Reciprocity Law: Lei 15.122 of 2025-04-11 (published DOU 2025-04-14) lets the Executive suspend trade concessions, investment obligations and IP rights and impose counter-tariffs in response to unilateral foreign measures; Executive (Camex) decides.",
  "2025-04-11", "https://www.migalhas.com.br/quentes/428377/apos-tarifaco-de-trump-lula-sanciona-lei-da-reciprocidade-economica", "Migalhas", "high", "C1", "Lula IV|worst|US",
  "https://www2.camara.leg.br/legin/fed/lei/2025/lei-15122-11-abril-2025-797315-norma-pl.html", "Câmara legin")
f("G07", "Dosimetria bill PL 2162/2023: Chamber 2025-12-10 (291–148), Senate 2025-12-17 (48–25); Lula vetoed it in full on 2026-01-08.",
  "2026-01-08", "https://dadosabertos.camara.leg.br/api/v2/proposicoes/2358548/votacoes", "Câmara open data", "high", "C1/C2", "Lula IV|best|US;Flávio|best|US",
  "https://pt.wikipedia.org/wiki/PL_da_Dosimetria", "Wikipedia (citing Agência Câmara/Senado)")
f("G08", "Sen. Esperidião Amin (PP-SC) filed a 'broad and unrestricted' amnesty bill for 8 January participants after the veto; no date set; 257/41 needed to override a veto.",
  "2026-01-09", "https://www.diariodepernambuco.com.br/politica/2026/01/11704670-apos-veto-de-lula-relator-do-pl-da-dosimetria-protocola-pl-da-anistia.html", "Diário de Pernambuco", "medium", "C1", "Flávio|best|US")
f("G09", "PLAN ANCHOR SUPERSEDED: Congress overrode the dosimetria veto on 2026-04-30 — Chamber 318–144 (5 abst.), Senate 49–24; promulgated by the Senate president as Lei 15.402 on 2026-05-08.",
  "2026-04-30", "https://www12.senado.leg.br/noticias/materias/2026/04/30/congresso-derruba-veto-e-possibilita-reducao-de-penas-pelo-8-de-janeiro", "Senado Notícias", "high", "C1/C2", "Lula IV|best|US;Flávio|best|US",
  "https://pt.wikipedia.org/wiki/PL_da_Dosimetria", "Wikipedia")
f("G10", "Justice Moraes suspended the application of Lei 15.402 (dosimetria) on 2026-05-09 pending STF review (ABI and PSOL-Rede challenges).",
  "2026-05-09", "https://pt.wikipedia.org/wiki/PL_da_Dosimetria", "Wikipedia (citing g1 2026-05-09, g1 not fetchable)", "medium", "C1/C2", "Flávio|best|US")
f("G11", "Emendas 2025: R$31.5bn paid within the budget year (SIOP, record); Portal da Transparência cash basis incl. restos a pagar R$43.5bn; 2026 LOA authorised R$61.4bn (R$49.9bn impositivas + R$11.5bn other).",
  "2026-01-15", "https://www.diariodepernambuco.com.br/politica/2026/01/11704130-governo-lula-registra-pagamento-recorde-de-rs-315-bilhoes-em-emendas-em-2025.html", "Diário de Pernambuco (SIOP)", "high", "C14", "all",
  "https://www.congressoemfoco.com.br/noticia/115071/congresso-aprova-orcamento-de-2026-com-superavit-de-r-34-5-bilhoes", "Congresso em Foco")
f("G12", "Emendas paid (cash incl. restos a pagar, R$bn): 2016 16.2, 2017 10.2, 2018 12.9, 2019 11.7, 2020 23.7, 2021 25.2, 2022 27.9, 2023 32.9, 2024 39.3, 2025 43.5, 2026 Jan–Sep 35.1; RP9 2020–22 8.5/10.2/11.5; Pix 2020–25 0.6→6.9. Executive discretionary (RTN 4.4.2) 2025 R$204.9bn.",
  "2026-10-01", "https://portaldatransparencia.gov.br/download-de-dados/emendas-parlamentares/UNICO", "Portal da Transparência (EmendasParlamentares.csv, extract 2026-10-01)", "high", "C14", "all",
  "https://www.tesourotransparente.gov.br/ckan/dataset/ab56485b-9c40-4efb-8563-9ce3e1973c4b/resource/527ccdb1-3059-42f3-bf23-b5e3ab4c6dc6/download/seriehistoricajul26.xlsx", "Tesouro RTN série histórica (Jul-2026)")
f("G13", "Governismo (Estadão Basômetro, share of Chamber roll calls voted with the government leader's orientation): Lula I 77, Lula II 79, Dilma I 75, Dilma II 65, Temer 76, Bolsonaro 76. Confirmed only via a search-result excerpt; definition = follow-rate, not win-rate.",
  "2022-01-01", "https://www.folhavitoria.com.br/politica/visoes-ideologicas-dividem-a-camara/", "Folha Vitória (citing Basômetro; via search excerpt)", "low", "Congress", "governability")
f("G14", "Arko Advice follow-rate (deputies following the government orientation in open roll calls): 46.4% Apr 2023, 46.5% May 2024 (lowest in 13 months; 20 of 52 oriented votes lost).",
  "2024-06-10", "https://www.infomoney.com.br/politica/governo-lula-tem-menor-apoio-na-camara-dos-deputados-em-13-meses-diz-levantamento/", "InfoMoney (Arko Advice)", "medium", "Congress", "governability")
f("G15", "MP conversion (converted / decided, post-EC 32): FHC 2001–02 82.3%, Lula I 90.4%, Lula II 83.2%, Dilma I 74.4%, Dilma II 78%, Temer 75% (108/144), Bolsonaro 68.3% (194/284), Lula III 23% (38 converted of 192 issued; 128 of 166 decided failed, to Apr 2026).",
  "2026-04-30", "https://www.infomoney.com.br/?p=3278641", "InfoMoney (Ranking dos Políticos)", "medium", "Congress", "governability",
  "https://congressoemfoco.com.br/area/governo/campeao-em-mps-bolsonaro-aprovou-menos-da-metade-delas-no-congresso", "Congresso em Foco")
f("G16", "Vetoes appreciated / at least partly overridden: FHC 1 overridden, Lula I+II 4, Dilma 7 of 142, Temer 21 of 144, Bolsonaro 114 of 258 (44%), Lula III 43 of 87 (49%, 2023–25).",
  "2025-12-31", "https://jornaldebrasilia.com.br/noticias/politica-e-poder/congresso-derruba-metade-dos-vetos-de-lula-e-muda-dinamica-de-governabilidade/", "Jornal de Brasília (Folha/Senado count)", "medium", "Congress", "veto_strength", "https://congressoemfoco.com.br/noticia/19100/lula-3-teve-no-primeiro-ano-de-governo-91-vetos-derrubados-pelo-congresso-bolsonaro-57", "Congresso em Foco")
f("G17", "Licensing law 15.190/2025: 52 of 63 vetoes overridden on 2025-11-27 (Chamber 295–167, Senate 52–15) [= exports C30].",
  "2025-11-27", "https://www.camara.leg.br/noticias/1227650-congresso-derruba-vetos-de-lula-ao-licenciamento-ambiental/", "Agência Câmara", "high", "C7/C8", "Lula IV|worst|EU")
f("G18", "FPA membership: 54th leg. 191 deputies + 14 senators; 55th 232 deputies (Câmara open data, signatures); 56th 225 + 32 at launch; 57th 300 + 47 (FPA site Jul-2026: 297 + 48). 53rd and 58th not available.",
  "2026-07-01", "https://www.scielo.br/j/rsocp/a/YY8KHZ8KMTjVLTMdjYWY6RP/?format=html&lang=pt", "Graciano 2023 (RSOCP) citing FPA", "medium", "C7", "EU cells",
  "https://www.camara.leg.br/noticias/442698-bancada-da-agropecuaria-vai-aumentar-no-proximo-ano/", "Agência Câmara 2014")
f("G19", "Coalition seat shares at cabinet dates 1987–2005 (Sarney 63–78%, Collor 35–44%, Itamar 60%, FHC 56→77% and 74→45%, Lula 43→70%) from Figueiredo (2007) Chart 2; 2007+ computed from election seats.",
  "2007-01-01", "https://bibliotecadigital.tse.jus.br/xmlui/bitstream/handle/bdtse/4518/2007_figueiredo_government_coalitions_democracy.pdf", "Figueiredo 2007 (TSE digital library)", "medium", "Congress", "panel")
f("G20", "Executive bill success (win-rate, Limongi 2006, CEBRAP): 70.7% for 1988–2006; Collor 65%; Itamar ≈66%. No sourced win-rates after 2006.",
  "2006-11-01", "https://www.scielo.br/scielo.php?script=sci_arttext&pid=S0101-33002006000300002", "Limongi 2006, Novos Estudos 76", "medium", "Congress", "governability")
f("G21", "PLAN ANCHOR SUPERSEDED: Mercosur–EFTA (signed 2025-09-16) approved by DL 146 of 2026-06-22, promulgated by Decreto 13.126 of 2026-09-23, in force for Brazil from 2026-10-01; Mercosur–Singapore approved by DL 147 of 2026-06-22, Decreto 13.081 of 2026-07-27.",
  "2026-09-23", "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/decreto/d13126.htm", "Planalto (Decreto 13.126/2026)", "high", "C9/C10", "Mercosur/LatAm cells",
  "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2026/decreto/D13081.htm", "Planalto (Decreto 13.081/2026)")
f("G22", "Treaty lags (signature→DL): Israel 24 m, Egypt 62 m, Palestine 81 m, Chile 35 m, US ATEC 13 m, Singapore 30.5 m, EFTA 9.2 m, EU 1.9 m.",
  "2026-09-23", "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/decreto/d7159.htm", "Planalto promulgation decrees (research/treaties.csv)", "high", "C9", "G10")
f("G23", "Reform dates (Câmara/Senado open data): PEC 241 1st round 2016-10-10 (366–111); labour reform 2017-04-26 (296–177); pension 1st round 2019-07-10 (379–131); BCB autonomy 2021-02-10 (339–114); precatórios 2021-11-04 (312–144); Kamikaze 1st round 2022-07-12; transição 2022-12-20; fiscal framework 2023-05-23 (372–108); PEC 45 1st round 2023-07-06 (382–118).",
  "2023-07-06", "https://dadosabertos.camara.leg.br/api/v2/proposicoes/2088351/votacoes", "Câmara open data (research/reforms.csv)", "high", "Congress", "event study")
f("G24", "Feb-2027 presidencies: PL launches Rogério Marinho for the Senate and says it will not back Alcolumbre; Sóstenes Cavalcante (PL-RJ) cited for the Chamber; Motta (Republicanos) and Alcolumbre (União) seek re-election.",
  "2026-10-05", "https://www.congressoemfoco.com.br/noticia/122994/valdemar-diz-que-pl-quer-eleger-rogerio-marinho-presidente-do-senado", "Congresso em Foco", "medium", "Congress", "presidency_subbranch",
  "https://www.cnnbrasil.com.br/politica/pl-mira-comando-da-camara-e-do-senado-mas-centrao-mantem-forca/", "CNN Brasil")
f("G25", "Chamber/Senate presidents 1987–2025 by party (PMDB dominance of the Senate chair 1987–2017; PP Lira 2021–25; Republicanos Motta 2025; União Alcolumbre 2025).",
  "2025-02-01", "https://pt.wikipedia.org/wiki/Lista_de_presidentes_da_C%C3%A2mara_dos_Deputados_do_Brasil", "Wikipedia lists (research/chamber_presidents.csv)", "medium", "Congress", "panel")
f("G26", "Historical Chamber seats by party 1986–2022: Portuguese Wikipedia election tables (citing TSE); 2002 from TSE open data; alternative values ±1–2 seats noted per row.",
  "2026-10-05", "https://pt.wikipedia.org/wiki/Elei%C3%A7%C3%B5es_gerais_no_Brasil_em_2022", "Wikipedia/TSE (research/chamber_seats.csv)", "medium", "Congress", "panel")
f("G27", "Senate composition at legislature start 1995–2023 from the Senate open-data API (party on 1 Feb); 1987 and 1991 not available.",
  "2026-10-05", "https://legis.senado.leg.br/dadosabertos/", "Senado open data (research/senate_seats.csv)", "medium", "Congress", "panel")
f("G28", "Party ideology: Zucco & Power BLS 1990–2021 party estimates (−1..+1, mapped to 0–10 as (s+1)·5); Bolognesi, Ribeiro & Codato 2023 DADOS 2018 round (0–10; no 2022 round in the paper).",
  "2023-01-01", "https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/6KVTUV", "Harvard Dataverse BLS9", "high", "Congress", "panel",
  "https://scielo.br/j/dados/a/zzyM3gzHD4P45WWdytXjZWg/?format=pdf", "SciELO DADOS")
f("G29", "2026 first round (TSE): Flávio Bolsonaro 47.03%, Lula 45.16% of valid votes; run-off 2026-10-25 [= exports A49/C63].",
  "2026-10-05", "https://en.wikipedia.org/wiki/2026_Brazilian_general_election", "Wikipedia (TSE count; see A49)", "high", "politics", "all")

if __name__ == "__main__":
    reuse = "A11 A12 A21 A25 A26 A27 A29 A32 A38 A49 A50 A51 B24 B51 C05 C06 C07 C23 C24 C25 C30 C32 C33 C60 C61 C63".split()
    df = build(reuse_ids=reuse)
    print(len(df), df.fact_id.tolist())
