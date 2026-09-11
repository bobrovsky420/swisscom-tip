# Residence permit in Switzerland - hackathon MVP source catalogue

Research dates: 2026-09-10 and 2026-09-11. The residence-permit MCP pilot is the hackathon MVP.
This catalogue owns its curated source plan and nationwide expansion inventory.
It records source selection, not an acquired or published corpus.

## Nationwide and multilingual expansion - 2026-09-11

The user has requested all available residence-permit information from all
identified official sources in every language published by those sources.
The earlier federal/Zurich semantic subset is incomplete and does not satisfy
that scope. All cantons require substantive source coverage, not contact rows alone.

The machine-readable [expanded source inventory](hackathon.sources.expanded.json)
records discovered language versions and linked residence-topic pages/documents,
including advertised languages, discovery reasons and acquisition status. Full
referring URLs and link labels remain in the local `audit-state.json` ledger.
It supplements the legacy scan registry below. It is a working inventory, not
an assertion of exhaustive discovery or independently reviewed legal knowledge.

Audit the languages actually offered on each page and in linked documents; do not
assume that every page has the site's full set of languages. Published language
links must be fetched and checked for redirects, fallback text and empty shells.
Retain all offered languages, including languages beyond DE/FR/IT/EN/RM. Automated
translation widgets are not evidence of independently published translations.
Fedlex language availability must come from the work's publication metadata.

Follow substantive procedures, forms, checklists, fees and directives beyond
landing pages. Keep unavailable downloads, unresolved dynamic sites and unreviewed
links visible in the audit. Acquisition and language discovery precede semantic
extraction; source-text extraction alone is not semantic completion.

New acquisition storage: `.local/corpora/hackathon-residence-all-languages-2026-09-11/`.
Its `audit-state.json` records language links and unselected links requiring scope
review. Original downloads and the first experimental serving release are retained.

The [coverage checkpoint](hackathon.sources.coverage.md) records the current
download and native-text coverage for every canton. The standalone preparation
workflow is documented in [scripts/corpora](../../scripts/corpora/README.md).
Its expanded serving collection is under
`.local/mvp/residence-all-languages-2026-09-11-v1/`; source assertions and OCR have
separate intermediate directories and review ledgers. Serving-contract validation
does not establish complete discovery, translation equivalence or semantic review.

## MVP source plan and registry status

The machine-readable [scan registry](hackathon.sources.json) currently contains 59
entries: 24 federal, 34 cantonal and one municipal. All 26 cantons are represented;
the additional cantonal entries provide more detail for Zurich. Four entries are
language versions of the SEM residence overview, so 59 is not a count of distinct
authorities or independent bodies of knowledge.

The source plan below includes additions that are not yet configured in the scan
registry. The [registered seed index](#registered-seed-index) preserves its exact
source IDs, priorities and scan statuses. These additions need source definitions
and reviewed allowlists before they can be selected by the crawler.

The gaps are depth and source types:

- Add federal implementing legislation beyond AIG, VZAE and FZA.
- Expand SEM guidance beyond the foreign-nationals directives to free movement,
  integration, visas and protection-related residence.
- Include the work-authorisation branch of each canton, public forms, checklists,
  fee schedules, administrative directives and relevant cantonal legislation.
- Add municipal sources, especially the separate authorities listed by SEM.
- Add FDFA representation-specific national-visa instructions and diplomatic
  residence/Ci material.
- Include relevant court decisions as a separately curated legal layer.

The inventory below covers the principal government source families and all
cantonal jurisdictions. It does **not** establish that every relevant government
page, PDF, municipal website or judgment has been enumerated. Full municipal,
representation-specific and cantonal legal-document discovery remains necessary
before describing the corpus as exhaustive.

## Scope and selection

Include eligibility and procedures for initial residence, renewal, settlement,
employment and self-employment, study, residence without employment, family
reunification, integration/language requirements, changes of canton or purpose,
loss/replacement of documents, absence, departure, expiry, refusal and revocation.
Include nationality-specific and transitional regimes, hardship routes, and
residence consequences of separation, bereavement or domestic violence.

Cover L, B, C and Ci; include F, N and S as distinct status/document categories and
their residence-related transitions. Keep G and short-term notification rules as
boundary topics, so the corpus can distinguish cross-border work and notification
from residence permission. Do not model every document category as the same type
of residence entitlement.

Use public government publications and official court publications. Exclude
private relocation advice, authenticated case files and application submissions.
Naturalisation, tourism, general housing/tax/customs advice and the full asylum
determination process are outside the initial permit-focused corpus. Protection
status, related family/work/mobility rules and transitions to residence remain in
scope. This broadens the scan registry's existing asylum/protection boundary;
its machine-readable scope still needs to be aligned before acquiring that material.

In the tables, **retain** means already explicitly seeded; **deepen** means select
specific material within an existing source family; **add** means an additional
source branch. None of these labels means content has been ingested.

## Federal guidance

Each link identifies the official publication or discovery page. Select linked
substantive pages and attachments, not only the landing-page text.

| Action | Source | Material to curate |
| --- | --- | --- |
| Retain/deepen | [SEM residence](https://www.sem.admin.ch/sem/de/home/themen/aufenthalt.html), [EU/EFTA](https://www.sem.admin.ch/sem/de/home/themen/aufenthalt/eu_efta.html), [non-EU/EFTA](https://www.sem.admin.ch/sem/de/home/themen/aufenthalt/nicht_eu_efta.html) | Individual permit/status pages and linked factsheets; preserve each regime's scope. |
| Deepen | [SEM residence and integration FAQ](https://www.sem.admin.ch/sem/de/home/themen/aufenthalt/faq.html) | Explicitly select this child of the existing residence branch. |
| Retain/deepen | [SEM free-movement FAQ](https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html) | Employment, non-working residence, family and changes in circumstances. |
| Retain/deepen | [SEM third-country work admission](https://www.sem.admin.ch/sem/de/home/themen/arbeit/nicht-eu_efta-angehoerige.html) | Admission criteria, procedure, current quota circulars and linked legal bases. |
| Add | [SEM work FAQ](https://www.sem.admin.ch/sem/de/home/themen/arbeit/faq.html) | Work-related questions across admission routes. |
| Add | [SEM short-term notification](https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/meldeverfahren.html) | Permit/notification boundary and competent authorities. |
| Add | [UK acquired rights](https://www.sem.admin.ch/sem/de/home/themen/arbeit/uk/erworbene-rechte.html), [new admission](https://www.sem.admin.ch/sem/de/home/themen/arbeit/uk/zulassung.html), [UK FAQ](https://www.sem.admin.ch/sem/de/home/themen/arbeit/uk/faq.html) | Keep acquired-rights and subsequent admission routes separately identified. |
| Retain/deepen | [SEM entry](https://www.sem.admin.ch/sem/de/home/themen/einreise.html) and [entry FAQ](https://www.sem.admin.ch/sem/de/home/themen/einreise/faq.html) | National visa, entry approval and return/re-entry material relevant to residence. |
| Retain/deepen | [SEM biometric permits](https://www.sem.admin.ch/sem/de/home/themen/aufenthalt/biometr_auslaenderausweis.html) | Permit-card issuance and document guidance. |
| Deepen | [SEM travel documents](https://www.sem.admin.ch/sem/de/home/themen/aufenthalt/reisedokumente.html) | Status-related travel documentation. |
| Deepen | [SEM sans-papiers](https://www.sem.admin.ch/sem/de/home/themen/aufenthalt/sans-papiers.html) | Public guidance and links for irregular residence/hardship routes. |
| Retain/deepen | [SEM foreign-nationals directives](https://www.sem.admin.ch/sem/de/home/publiservice/weisungen-kreisschreiben/auslaenderbereich.html) | Current directive chapters, annexes and applicable circulars, including PDFs. |
| Add | [SEM free-movement directives](https://www.sem.admin.ch/sem/de/home/publiservice/weisungen-kreisschreiben/fza.html) | VFP guidance, annexes and circulars. |
| Add | [SEM integration directives](https://www.sem.admin.ch/sem/de/home/publiservice/weisungen-kreisschreiben/integration.html) | Relevant integration guidance and linked language-evidence material. |
| Add | [SEM visa directives](https://www.sem.admin.ch/sem/de/home/publiservice/weisungen-kreisschreiben/visa.html) | Residence-related visa instructions and annexes. |
| Add | [SEM asylum directives](https://www.sem.admin.ch/sem/de/home/publiservice/weisungen-kreisschreiben/asylgesetz.html) | Only the residence/status, family, work and mobility sections for this corpus. |
| Add | [SEM Ukraine/protection FAQ](https://www.sem.admin.ch/sem/de/home/sem/aktuell/ukraine-krieg.html) | Current S-status guidance and related residence transitions; retain effective dates. |
| Retain | [SEM authority directory](https://www.sem.admin.ch/sem/de/home/sem/kontakt/kantonale_behoerden/adressen_kantone_und.html) | Authority discovery and routing; not evidence of permit eligibility. |
| Retain/deepen | [ch.ch permits](https://www.ch.ch/de/auslander-in-der-schweiz/einreise-in-die-schweiz/aufenthaltsbewilligung/), [family](https://www.ch.ch/de/auslander-in-der-schweiz/einreise-in-die-schweiz/familiennachzug/), [work](https://www.ch.ch/de/auslander-in-der-schweiz/in-der-schweiz-arbeiten/) | Accessible summaries and terminology, backed by detailed sources. Existing seeds retained; their redirects were not all rechecked in this review. |
| Add | [FDFA visa information](https://www.eda.admin.ch/eda/de/home/einreise-und-aufenthaltinderschweiz/visa.html) | Discover the responsible Swiss representation's public national-visa checklist for each relevant country of residence. |
| Add | [FDFA residence in Switzerland](https://www.eda.admin.ch/en/residence-in-switzerland) | Diplomatic/consular legitimation cards and Ci procedures. |
| Add | [Swiss Mission Geneva: legitimation cards](https://www.mission-geneve.dfae.admin.ch/en/manual-fdfa-legitimation-cards) and [family members](https://www.mission-geneve.dfae.admin.ch/en/manual-members-of-family) | International organisations and permanent missions; related family and Ci guidance. |

The FDFA country/representation layer is a source family, not one universal
checklist. For example, the [German representation's national-visa document
page](https://www.schweiz-deutschland.eda.admin.ch/en/documents-national-visa)
is a concrete additional seed. Discover other representations through FDFA;
record their geographic competence and retain country-specific instructions.

## Federal legislation

Use Fedlex as the legal-text source. Preserve the selected consolidation date and
effective interval. A search result pointing to an old PDF is useful for discovery
but does not establish the current law. The Fedlex ELI pages below returned a
JavaScript shell during this review; full current-text acquisition is still required.

| Action | Instrument / source | Purpose in the corpus |
| --- | --- | --- |
| Retain | [AIG / LEI / FNIA, SR 142.20](https://www.fedlex.admin.ch/eli/cc/2007/758/de) | Core statutory residence framework. |
| Retain | [VZAE / OASA, SR 142.201](https://www.fedlex.admin.ch/eli/cc/2007/759/de) | Admission, residence and employment implementation. |
| Retain | [FZA / ALCP, SR 0.142.112.681](https://www.fedlex.admin.ch/eli/cc/2002/243/de) | EU free-movement agreement and annexes. |
| Add | [VFP / OLCP, SR 142.203](https://www.fedlex.admin.ch/eli/cc/2002/261/de) | Free-movement implementation. |
| Add | [VIntA / OIE, SR 142.205](https://www.fedlex.admin.ch/eli/cc/2018/511/de) | Integration framework; use alongside AIG/VZAE. |
| Add | [VEV / OEV, SR 142.204](https://www.fedlex.admin.ch/eli/cc/2018/493/de) | Entry and visa rules. |
| Add | [GebV-AIG, SR 142.209](https://www.fedlex.admin.ch/eli/cc/2007/763/de) | Federal migration-fee framework, supplemented by local schedules. |
| Add; exact current text to resolve | EJPD consent-procedure ordinance, SR 142.201.1, via [SEM legal bases](https://www.sem.admin.ch/sem/de/home/themen/arbeit/nicht-eu_efta-angehoerige.html) | Which decisions require federal consent. |
| Add; exact current texts to resolve | EFTA Convention, SR 0.632.31, including Annex K; CH-UK acquired-rights agreement, via [Fedlex](https://www.fedlex.admin.ch/) and [SEM UK guidance](https://www.sem.admin.ch/sem/de/home/themen/arbeit/uk/erworbene-rechte.html) | EFTA and UK treaty foundations beyond FZA. |
| Add; exact current texts to resolve | AsylG, SR 142.31, and relevant implementing provisions, via [SEM asylum directives](https://www.sem.admin.ch/sem/de/home/publiservice/weisungen-kreisschreiben/asylgesetz.html) | Legal basis for the protection/status slice. |
| Add; exact current texts to resolve | Host State Act and Host State Ordinance, via [FDFA residence guidance](https://www.eda.admin.ch/en/residence-in-switzerland) | Diplomatic and institutional residence regimes. |

For refusal/revocation and appeal questions, also select the relevant constitutional,
ECHR and procedural provisions cited by official guidance or judgments from Fedlex.
For country-specific settlement privileges, follow the settlement directives to
the relevant bilateral treaties. These are discovery tasks, not a claim that the
above instruments form an exhaustive legal bibliography.

## Cantonal sources - all 26 cantons

Retain every migration entry point below. Migration links are carried over from
the registry, not all independently revalidated here. Work-source links were
discovered through the [SEM directory](https://www.sem.admin.ch/sem/de/home/sem/kontakt/kantonale_behoerden/adressen_kantone_und.html).

Work-source status: **O** = page opened and identified during this review;
**D** = authority/host identified in the directory, but the destination could not
be read, so resolve its current topic URL before acquisition. O does not mean
every child page or document was checked. An office homepage is a discovery seed.

| Canton | Existing migration seed to retain/deepen | Additional work-source discovery seed | Status |
| --- | --- | --- | --- |
| AG - Aargau | [Migration](https://www.ag.ch/de/themen/migration-integration) | [Economy and work](https://www.ag.ch/de/themen/wirtschaft-arbeit) - refers work-permit questions to MIKA | O |
| AI - Appenzell Innerrhoden | [Entry/residence forms](https://www.ai.ch/themen/auslaender/einreise-und-aufenthalt/gesuchformulare-merkblaetter-einreise-und-aufenthalt) | Arbeitsamt through [canton](https://www.ai.ch/) | D |
| AR - Appenzell Ausserrhoden | [Internal affairs](https://ar.ch/verwaltung/departement-inneres-und-sicherheit/amt-fuer-inneres/) | Economy/work office through [canton](https://www.ar.ch/) | D |
| BE - Bern | [Migration](https://www.migration.sid.be.ch/de/start.html) | Amt fuer Wirtschaft through [directory](https://www.sem.admin.ch/sem/de/home/sem/kontakt/kantonale_behoerden/adressen_kantone_und.html) | D |
| BL - Basel-Landschaft | [Migration](https://www.baselland.ch/politik-und-behorden/direktionen/sicherheitsdirektion/amt_fuer_migration) | [KIGA](https://www.baselland.ch/politik-und-behorden/direktionen/volkswirtschafts-und-gesundheitsdirektion/kiga) | O |
| BS - Basel-Stadt | [Migration](https://www.bs.ch/jsd/bdm/migrationsamt) | [AWA](https://www.bs.ch/wsu/awa) | O |
| FR - Fribourg | [Population/migration](https://www.fr.ch/de/sjsd/bma) | [Foreign workforce](https://www.fr.ch/travail-et-entreprises/employeurs/main-doeuvre-etrangere) | O |
| GE - Geneva | [OCPM](https://www.ge.ch/organisation/office-cantonal-population-migrations-ocpm) | [OCIRT](https://www.ge.ch/organisation/ocirt-office-cantonal-inspection-relations-du-travail) | O |
| GL - Glarus | [Migration](https://www.gl.ch/verwaltung/sicherheit-und-justiz/justiz/migration.html/1215) | [Labour inspectorate](https://www.gl.ch/verwaltung/volkswirtschaft-und-inneres/wirtschaft-und-arbeit/arbeit/inspektorat-arbeitsmarkt.html/1013) | O |
| GR - Graubunden | [Entry/residence](https://www.gr.ch/DE/institutionen/verwaltung/djsg/afm/dienstleistungen/Einreise_Aufenthalt/NAA/Seiten/default.aspx) | [KIGA](https://www.kiga.gr.ch/) | D |
| JU - Jura | [Foreign nationals](https://www.jura.ch/fr/Autorites/Administration/DSJP/SPOP/Police-des-etrangers/Police-des-etrangers.html) | [SEE](https://www.jura.ch/fr/Autorites/Administration/DES/Economie-et-Emploi-SEE/Service-de-l-economie-et-de-l-emploi-SEE.html) | O |
| LU - Lucerne | [Migration](https://migration.lu.ch/) | [WIRA](https://wira.lu.ch/) | D |
| NE - Neuchatel | [Residence permits](https://www.ne.ch/themes/migration-et-integration/sejour-et-etablissement/permis-de-sejour) | Office de la main-d'oeuvre through [canton](https://www.ne.ch/) | D |
| NW - Nidwalden | [Residence information](https://integration.nw.ch/aufenthalt/) | [Arbeitsamt](https://www.nw.ch/arbeitsamt/314) | D |
| OW - Obwalden | [Migration](https://www.ow.ch/fachbereiche/1822) | [Amt fuer Arbeit](https://www.ow.ch/aemter/161) | O |
| SG - St Gallen | [Entry/residence/departure](https://www.sg.ch/sicherheit/einreise-aufenthalt-ausreise.html) | [AWA](https://www.awa.sg.ch/) | D |
| SH - Schaffhausen | [Migration](https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Verwaltung/Departement-des-Innern/Migrationsamt-und-Passb-ro-3454-DE.html) | [Work permits/notification](https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Verwaltung/Volkswirtschaftsdepartement/Arbeitsamt/Arbeitgeber-und-Unternehmen/Arbeitsbewilligungen-und-Meldeverfahren-1546859-DE.html) | O |
| SO - Solothurn | [Permits](https://so.ch/verwaltung/departement-des-innern/migrationsamt/aufenthalt-und-integration/bewilligungen/) | [AWA](https://so.ch/verwaltung/volkswirtschaftsdepartement/amt-fuer-wirtschaft-und-arbeit/) | O |
| SZ - Schwyz | [Migration](https://www.sz.ch/behoerden/verwaltung/volkswirtschaftsdepartement/amt-fuer-migration.html/8756-8758-8802-10373-10961) | [Amt fuer Arbeit](https://www.sz.ch/behoerden/verwaltung/volkswirtschaftsdepartement/amt-fuer-arbeit.html/8756-8758-8802-10373-10896) | O |
| TG - Thurgau | [Migration](https://www.migrationsamt.tg.ch/) | [AWA](https://awa.tg.ch/) | D |
| TI - Ticino | [Foreign nationals](https://www4.ti.ch/di/spop/stranieri) | [USML](https://www4.ti.ch/dfe/de/usml/home) | O |
| UR - Uri | [Migration](https://www.ur.ch/unterinstanzen/907) | Work/migration office through [canton](https://www.ur.ch/) | D |
| VD - Vaud | [Entry/residence](https://www.vd.ch/population/population-etrangere/entree-et-sejour) | [DGEM residence/work permits](https://www.vd.ch/economie/prestations-de-la-direction-generale-de-lemploi-et-du-marche-du-travail-dgem/permis-de-sejour-et-de-travail-pour-etrangers) | O |
| VS - Valais | [Population/migration](https://www.vs.ch/de/web/spm/) | [SICT](https://www.vs.ch/fr/web/sict) | O |
| ZG - Zug | [Entry/residence](https://zg.ch/de/migration-integration/einreise-und-aufenthalt) | [AWA](https://zg.ch/de/volkswirtschaftsdirektion/amt-fuer-wirtschaft-und-arbeit) | O |
| ZH - Zurich | [Residence](https://www.zh.ch/de/migration-integration/aufenthalt.html) plus existing detailed Zurich seeds | [Foreign-national employment](https://www.zh.ch/de/wirtschaft-arbeit/erwerbstaetigkeit-auslaender.html) | O |

For each canton, select residence-topic pages, relevant work-topic pages, downloadable
forms/checklists, fees, directives and the official legal collection's applicable
implementing/procedural provisions. Follow the canton website's official links to
legal-publication services even when hosted on a separate domain; record the
publishing canton. A domain or office entry alone does not establish topic coverage.

Two specific improvements to existing coverage:

- Zurich: explicitly add [migration forms, brochures and directives](https://www.zh.ch/de/sicherheitsdirektion/migrationsamt/formulare-broschueren-weisungen-des-migrationsamts.html).
  This and the work branch sit outside the current residence topic path.
- Nidwalden: supplement the integration information page with the actual migration
  authority and its public forms. A [residence-permit application form](https://www.nw.ch/online-schalter/5572/download)
  was located in official search results; authority-page access remains unresolved.

The scan registry already flags AI, NW and TG for access review. Preserve
those flags until acquisition succeeds. Do not interpret browsing failures as
absence of official information.

## Municipal sources

The SEM directory explicitly lists Bern, Biel/Bienne, Thun and Lausanne in addition
to cantonal authorities. Add them to the existing Zurich city source. These five
entries are an initial municipal set, not complete municipal coverage.

| Action | Source | Selection / verification |
| --- | --- | --- |
| Retain/deepen | [City of Zurich arrival registration](https://www.stadt-zuerich.ch/de/lebenslagen/einwohner-services/umziehen-melden/zuzug.html) | Existing `zurich-city-arrival`; select foreign-national arrival/move/departure instructions. |
| Add | [City of Bern foreign-national information](https://www.bern.ch/themen/auslanderinnen-und-auslander) | Opened from the SEM directory; select residence procedures and forms. |
| Add | [Thun migration service](https://www.thun.ch/fachbereiche/32216) | Opened from the SEM directory. |
| Add; destination to resolve | [Biel/Bienne city](https://www.biel-bienne.ch/) | Migration service identified by SEM; directory destination failed to load. |
| Add | [Lausanne residents' registration](https://www.lausanne.ch/officiel/administration/securite-et-economie/controle-des-habitants) | Opened from SEM; local procedures and links. |

For nationwide local-procedure coverage, enumerate the official commune websites
from each canton's municipal directory and select Einwohnerkontrolle,
Einwohnerdienste, Controle des habitants and Controllo abitanti material. Record
when a commune delegates to a regional or cantonal service. Do not infer one
commune's documents, fees or appointment process for another. The municipal
directories and all commune-level URLs have not yet been individually inventoried.

## Courts and legal interpretation

| Action | Source | Selection |
| --- | --- | --- |
| Add | [Federal Supreme Court jurisprudence](https://www.bger.ch/jurisdiction-recht) | Relevant published decisions on residence, settlement, family, integration, refusal and revocation. |
| Add | [Federal Administrative Court decisions](https://www.bvger.ch/de/rechtsprechung/entscheiddatenbank) | Relevant federal migration decisions. The official court page links its externally operated decision database. |
| Add; canton-level discovery required | Administrative-court decisions through each canton's official judicial website | Select relevant published local decisions; exact court/database URLs remain to be inventoried for all cantons. |

This layer is part of the full source map, but can follow the first procedural MVP release.
Select decisions cited by current directives first. Preserve court, decision date,
case number, cited provision and case-specific context; a judgment is not a
general-purpose application checklist. Court-database pages were located; individual
judgments were not selected in this step.

## Existing adjacent sources

Keep the existing BAG health-insurance source where evidence of insurance is
relevant to a residence route. Keep BSV material only for permit-relevant financial
or benefit questions. Defer general BAZG moving/customs, BWO housing and ESTV tax
content from the initial permit corpus. These remain useful for a broader
"moving to Switzerland" domain, but do not fill the permit-source gaps above.

## Superseded staged acquisition proposal

The following 2026-09-10 staging proposal is superseded by the nationwide,
all-published-languages instruction above. It is retained as history, not an active
restriction on acquisition or semantic extraction.

Start with the current federal legal foundations, selected SEM directive sections
and FAQs, ch.ch summaries, and complete procedural material for Zurich plus one
French-speaking and one Italian-speaking canton (Vaud and Ticino are already
seeded). Add the relevant city/commune instructions for the MVP scenarios.
Treat all other cantons as the documented expansion inventory until their material
is acquired and reviewed. This is the suggested MVP acquisition sequence, not a reduction of
the nationwide source inventory.

For every chosen source document record its URL, publisher, jurisdiction, language,
title, retrieval date, visible revision date, effective dates where stated, document
type, relevant nationality/status/purpose and exact section/page citation. Store
the original alongside the curated text. Keep official source-language evidence
when producing English answers; translations are not automatically equivalent.

Check the selected set against these question groups before publishing it through
MCP: eligibility; documents; authority/application channel; timing; fees; renewal;
family; work rights; study/non-working residence; settlement/language; moving;
absence/re-entry; expiry/refusal/revocation; protection and special regimes. Mark
uncovered combinations of canton and route explicitly.

## Acquisition implications and remaining inventory work

The existing registry's `ready` status means eligible for a scan, not acquired
knowledge. Its small scan budgets and HTML topic paths do not ensure capture of
linked PDFs, sibling work pages or separate legal-publication hosts. In particular,
the current SEM directive entry does not allow its `/dam/` attachment paths.

Before acquisition, resolve D-marked destinations, enumerate the selected public
attachments and language variants, and add precise source definitions/allowlists.
Acquire Fedlex's actual dated legal texts rather than its JavaScript shell. Keep
current and historical publications distinguishable, including dated quota and
transitional-rule material.

To reach an exhaustive document inventory, remaining discovery must enumerate:
all relevant municipal pages; national-visa instructions for every representation;
the applicable cantonal laws/directives/fees; additional bilateral/legal provisions;
and selected relevant judgments. This review establishes where those source
families belong and identifies concrete seeds, but does not count uninspected
documents as covered.

The next MVP step is to select and acquire the initial corpus from this plan,
then curate it for MCP retrieval. Further extractor tuning is not a prerequisite.

## Maintaining this catalogue

Edit the source plan above directly. The marked registry section below is generated
from `hackathon.sources.json`; `scripts/catalogs/refresh_hackathon.py` refreshes only
that section and preserves the curated plan. See the [catalogue maintenance
instructions](README.md#maintain-the-catalogue) for registry updates and validation.

<!-- BEGIN GENERATED SOURCE REGISTRY -->

## Registered seed index

Operator-authored source references only. Discovery dates and references are recorded
per source in the registry. Authority discovery includes the
[SEM cantonal authority directory](https://www.sem.admin.ch/sem/de/home/sem/kontakt/kantonale_behoerden/adressen_kantone_und.html).
These are future scan targets, not legal evidence or confirmed crawler coverage.

The machine-readable [registry](hackathon.sources.json) contains exact allowlists,
discovery references, topic hints, scan sets, limits and per-source caveats.
`ready` means eligible for a test; access and robots policy are checked at run time.

German is preferred when selecting a single version for a limited run. Every selected
language version is retained; German seeds run first. Parallel page groups are candidates
for later alignment, not verified content equivalence or shared evidence identity.

| ID | Official source | Jurisdiction | Seed language hint | Priority | Scan status | Candidate parallel page group |
| --- | --- | --- | --- | --- | --- | --- |
| `ag-residence` | [Aargau - residence and migration](https://www.ag.ch/de/themen/migration-integration) | CH-AG | de | P1 | ready | - |
| `ai-residence` | [Appenzell Innerrhoden - residence and migration](https://www.ai.ch/themen/auslaender/einreise-und-aufenthalt/gesuchformulare-merkblaetter-einreise-und-aufenthalt) | CH-AI | de | P1 | needs_access_review | - |
| `ar-residence` | [Appenzell Ausserrhoden - residence and migration](https://ar.ch/verwaltung/departement-inneres-und-sicherheit/amt-fuer-inneres/) | CH-AR | de | P1 | ready | - |
| `be-residence` | [Bern - residence and migration](https://www.migration.sid.be.ch/de/start.html) | CH-BE | de | P0 | ready | - |
| `bl-residence` | [Basel-Landschaft - residence and migration](https://www.baselland.ch/politik-und-behorden/direktionen/sicherheitsdirektion/amt_fuer_migration) | CH-BL | de | P1 | ready | - |
| `bs-residence` | [Basel-Stadt - residence and migration](https://www.bs.ch/jsd/bdm/migrationsamt) | CH-BS | de | P1 | ready | - |
| `ch-bag-health-insurance` | [Health insurance for persons resident in Switzerland](https://www.bag.admin.ch/de/krankenversicherung-versicherungspflicht-fuer-in-der-schweiz-wohnhafte-versicherte) | CH | de | P0 | ready | - |
| `ch-bazg-moving` | [Moving to Switzerland: customs procedure](https://www.bazg.admin.ch/de/vorgehen-umzug-in-die-schweiz) | CH | de | P1 | ready | - |
| `ch-bsv-ahv` | [Old-age and survivors insurance (AHV) overview](https://www.bsv.admin.ch/de/ahv-uebersicht) | CH | de | P1 | ready | - |
| `ch-bwo-housing` | [Housing in Switzerland - official brochure index](https://www.bwo.admin.ch/de/broschuere-wohnen-in-der-schweiz) | CH | de | P2 | ready | - |
| `ch-chch-family` | [Family reunification](https://www.ch.ch/de/auslander-in-der-schweiz/einreise-in-die-schweiz/familiennachzug/) | CH | de | P1 | ready | - |
| `ch-chch-permits` | [Residence permits: application and renewal](https://www.ch.ch/de/auslander-in-der-schweiz/einreise-in-die-schweiz/aufenthaltsbewilligung/) | CH | de | P1 | ready | - |
| `ch-chch-work` | [Working in Switzerland as a foreign national](https://www.ch.ch/de/auslander-in-der-schweiz/in-der-schweiz-arbeiten/) | CH | de | P1 | ready | - |
| `ch-estv-tax-at-source` | [Swiss tax at source](https://www.estv.admin.ch/de/quellensteuer) | CH | de | P2 | ready | - |
| `ch-fedlex-aig` | [Foreign Nationals and Integration Act (AIG/LEI), SR 142.20](https://www.fedlex.admin.ch/eli/cc/2007/758/de) | CH | de | P1 | manual_adapter_required | - |
| `ch-fedlex-fza` | [Agreement on the Free Movement of Persons, SR 0.142.112.681](https://www.fedlex.admin.ch/eli/cc/2002/243/de) | CH | de | P1 | manual_adapter_required | - |
| `ch-fedlex-vzae` | [Admission, Residence and Employment Ordinance (VZAE/OASA), SR 142.201](https://www.fedlex.admin.ch/eli/cc/2007/759/de) | CH | de | P1 | manual_adapter_required | - |
| `ch-sem-authorities` | [Cantonal immigration and employment authorities](https://www.sem.admin.ch/sem/de/home/sem/kontakt/kantonale_behoerden/adressen_kantone_und.html) | CH | de | P0 | ready | - |
| `ch-sem-biometric-documents` | [Biometric residence permits](https://www.sem.admin.ch/sem/de/home/themen/aufenthalt/biometr_auslaenderausweis.html) | CH | de | P0 | ready | - |
| `ch-sem-directives` | [SEM directives - foreign nationals](https://www.sem.admin.ch/sem/de/home/publiservice/weisungen-kreisschreiben/auslaenderbereich.html) | CH | de | P1 | ready | - |
| `ch-sem-entry` | [Entry and visa information](https://www.sem.admin.ch/sem/de/home/themen/einreise.html) | CH | de | P0 | ready | - |
| `ch-sem-entry-faq` | [Entry FAQ](https://www.sem.admin.ch/sem/de/home/themen/einreise/faq.html) | CH | de | P0 | ready | - |
| `ch-sem-eu-efta` | [Residence permits for EU/EFTA nationals](https://www.sem.admin.ch/sem/de/home/themen/aufenthalt/eu_efta.html) | CH | de | P0 | ready | - |
| `ch-sem-free-movement-faq` | [Free movement of persons FAQ](https://www.sem.admin.ch/sem/de/home/themen/fza_schweiz-eu-efta/eu-efta_buerger_schweiz/faq.html) | CH | de | P0 | ready | - |
| `ch-sem-residence-de` | [SEM residence overview (de)](https://www.sem.admin.ch/sem/de/home/themen/aufenthalt.html) | CH | de | P0 | ready | ch-sem-residence-overview |
| `ch-sem-residence-en` | [SEM residence overview (en)](https://www.sem.admin.ch/sem/en/home/themen/aufenthalt.html) | CH | en | P0 | ready | ch-sem-residence-overview |
| `ch-sem-residence-fr` | [SEM residence overview (fr)](https://www.sem.admin.ch/sem/fr/home/themen/aufenthalt.html) | CH | fr | P0 | ready | ch-sem-residence-overview |
| `ch-sem-residence-it` | [SEM residence overview (it)](https://www.sem.admin.ch/sem/it/home/themen/aufenthalt.html) | CH | it | P0 | ready | ch-sem-residence-overview |
| `ch-sem-third-country` | [Residence permits for non-EU/EFTA nationals](https://www.sem.admin.ch/sem/de/home/themen/aufenthalt/nicht_eu_efta.html) | CH | de | P0 | ready | - |
| `ch-sem-work-third-country` | [Admission to work for non-EU/EFTA nationals](https://www.sem.admin.ch/sem/de/home/themen/arbeit/nicht-eu_efta-angehoerige.html) | CH | de | P0 | ready | - |
| `fr-residence` | [Fribourg - residence and migration](https://www.fr.ch/de/sjsd/bma) | CH-FR | de | P1 | ready | - |
| `ge-residence` | [Geneva - residence and migration](https://www.ge.ch/organisation/office-cantonal-population-migrations-ocpm) | CH-GE | fr | P1 | ready | - |
| `gl-residence` | [Glarus - residence and migration](https://www.gl.ch/verwaltung/sicherheit-und-justiz/justiz/migration.html/1215) | CH-GL | de | P1 | ready | - |
| `gr-residence` | [Graubunden - residence and migration](https://www.gr.ch/DE/institutionen/verwaltung/djsg/afm/dienstleistungen/Einreise_Aufenthalt/NAA/Seiten/default.aspx) | CH-GR | de | P0 | ready | - |
| `ju-residence` | [Jura - residence and migration](https://www.jura.ch/fr/Autorites/Administration/DSJP/SPOP/Police-des-etrangers/Police-des-etrangers.html) | CH-JU | fr | P1 | ready | - |
| `lu-residence` | [Lucerne - residence and migration](https://migration.lu.ch/) | CH-LU | de | P1 | ready | - |
| `ne-residence` | [Neuchatel - residence and migration](https://www.ne.ch/themes/migration-et-integration/sejour-et-etablissement/permis-de-sejour) | CH-NE | fr | P1 | ready | - |
| `nw-residence` | [Nidwalden - residence and migration](https://integration.nw.ch/aufenthalt/) | CH-NW | de | P1 | needs_access_review | - |
| `ow-residence` | [Obwalden - residence and migration](https://www.ow.ch/fachbereiche/1822) | CH-OW | de | P1 | ready | - |
| `sg-residence` | [St Gallen - residence and migration](https://www.sg.ch/sicherheit/einreise-aufenthalt-ausreise.html) | CH-SG | de | P1 | ready | - |
| `sh-residence` | [Schaffhausen - residence and migration](https://sh.ch/CMS/Webseite/Kanton-Schaffhausen/Beh-rde/Verwaltung/Departement-des-Innern/Migrationsamt-und-Passb-ro-3454-DE.html) | CH-SH | de | P1 | ready | - |
| `so-residence` | [Solothurn - residence and migration](https://so.ch/verwaltung/departement-des-innern/migrationsamt/aufenthalt-und-integration/bewilligungen/) | CH-SO | de | P1 | ready | - |
| `sz-residence` | [Schwyz - residence and migration](https://www.sz.ch/behoerden/verwaltung/volkswirtschaftsdepartement/amt-fuer-migration.html/8756-8758-8802-10373-10961) | CH-SZ | de | P1 | ready | - |
| `tg-residence` | [Thurgau - residence and migration](https://www.migrationsamt.tg.ch/) | CH-TG | de | P1 | needs_access_review | - |
| `ti-residence` | [Ticino - residence and migration](https://www4.ti.ch/di/spop/stranieri) | CH-TI | it | P0 | ready | - |
| `ur-residence` | [Uri - residence and migration](https://www.ur.ch/unterinstanzen/907) | CH-UR | de | P1 | ready | - |
| `vd-residence` | [Vaud - residence and migration](https://www.vd.ch/population/population-etrangere/entree-et-sejour) | CH-VD | fr | P0 | ready | - |
| `vs-residence` | [Valais - residence and migration](https://www.vs.ch/de/web/spm/) | CH-VS | de | P1 | ready | - |
| `zg-residence` | [Zug - residence and migration](https://zg.ch/de/migration-integration/einreise-und-aufenthalt) | CH-ZG | de | P1 | ready | - |
| `zh-biometric-documents` | [Zurich - Biometric residence documents](https://www.zh.ch/de/migration-integration/aufenthalt/biometrische-auslaenderausweise.html) | CH-ZH | de | P0 | ready | - |
| `zh-eu-efta` | [Zurich - Residence for EU/EFTA nationals](https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-fuer-euefta-staatsangehoerige.html) | CH-ZH | de | P0 | ready | - |
| `zh-family` | [Zurich - Family reunification for third-country nationals](https://www.zh.ch/de/migration-integration/aufenthalt/familiennachzug-von-drittstaatsangehoerigen.html) | CH-ZH | de | P0 | ready | - |
| `zh-integration` | [Zurich - integration](https://www.zh.ch/de/migration-integration/integration.html) | CH-ZH | de | P1 | ready | - |
| `zh-no-employment` | [Zurich - Residence without employment for third-country nationals](https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-ohne-erwerbstaetigkeit-fuer-drittstaatsangehoerige.html) | CH-ZH | de | P0 | ready | - |
| `zh-overview` | [Zurich - Residence overview](https://www.zh.ch/de/migration-integration/aufenthalt.html) | CH-ZH | de | P0 | ready | - |
| `zh-settlement` | [Zurich - settlement permit](https://www.zh.ch/de/migration-integration/niederlassungsbewilligung.html) | CH-ZH | de | P0 | ready | - |
| `zh-welcome-residence` | [Zurich - residence and family reunification for newcomers](https://www.zh.ch/de/migration-integration/willkommen/deutsch/aufenthalt-und-familiennachzug.html) | CH-ZH | de | P1 | ready | - |
| `zh-work-third-country` | [Zurich - Residence with employment for third-country nationals](https://www.zh.ch/de/migration-integration/aufenthalt/aufenthalt-mit-erwerbstaetigkeit-fuer-drittstaatsangehoerige.html) | CH-ZH | de | P0 | ready | - |
| `zurich-city-arrival` | [City of Zurich - registering an arrival](https://www.stadt-zuerich.ch/de/lebenslagen/einwohner-services/umziehen-melden/zuzug.html) | CH-ZH / city Zurich | de | P0 | ready | - |
<!-- END GENERATED SOURCE REGISTRY -->
