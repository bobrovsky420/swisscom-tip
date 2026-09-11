"""Assistant-authored semantic selections from the frozen 2026-09-10 corpus.

Statements, scope and evidence ranges were chosen by reading the sources.
This module contains data; it never asks a model to extract or generate claims.
Block numbers address the validated intermediate v1 dataset.
"""

AIG = 'doc-18355c7dc9a45a38b413'
SEM = 'doc-02369c71495279e06a62'
WORK = 'doc-d7e5fa9b1ea72ea04a52'
NOTIFY = 'doc-9b1cdec8a0d1eb938c6c'
BIO = 'doc-026495cd7a981ddc2584'
FAQ = 'doc-e4faac52bfd9dc95c90f'
FZA_FAQ = 'doc-094ef42324485ec86493'
ZH = 'doc-6fc4e12e684157ef4978'
ZH_RETIRED = 'doc-3198cb2abda7d67422f7'
CITY = 'doc-34ef0ec737a996b68d08'
BAG = 'doc-f09ebbb4481ad243ff38'
DIRECTORY = 'doc-c9b704219cdcddd9107e'


def claim(statement, document, first, last=None):
    return dict(statement=statement, document_id=document, first_block=first, last_block=last or first)


def concept(key, label, claims, *, canton=None, municipality=None, selector=None, intent='requirements', notes=None,
            validity=None):
    """One curated operation.

    `validity` holds a source-cited commencement or expiry (`valid_from`,
    `valid_through`). Omitted bounds are unbounded: the knowledge base carries
    no date limit unless the cited page states one.
    """
    return dict(key=key, label=label, claims=claims, canton=canton, municipality=municipality,
                selector=selector, intent=intent, notes=notes or [], validity=dict(validity or {}))


CONCEPTS = [
    concept('permit-authority', 'Authority issuing residence permits', [
        claim('Residence permits are issued by the cantonal migration offices.', SEM, 77),
    ]),
    concept('aig-short-stay', 'AIG baseline for stays without work', [
        claim('AIG Article 10(1) states that a stay without gainful employment of up to three months does not require a residence permit; a shorter duration specified in the visa prevails.', AIG, 192, 194),
        claim('For a planned longer stay without work, AIG Article 10(2) requires a permit application before entry to the authority at the intended place of residence, subject to Article 17(2).', AIG, 194),
    ], notes=['Describes AIG Article 10, not visa eligibility or all Schengen entry conditions.']),
    concept('aig-work-permit', 'AIG employment permit procedure', [
        claim('Under AIG Article 11(1), a foreign national intending to work in Switzerland needs a permit irrespective of the duration of stay and applies to the authority at the intended place of work.', AIG, 195, 196),
        claim('AIG Article 11(2) includes activities normally performed for remuneration even when performed without pay; for employment, Article 11(3) assigns the permit application to the employer.', AIG, 197, 198),
    ], selector=('population', 'third_country'), notes=['Treaty-based EU/EFTA notification and other special routes are separate concepts.']),
    concept('aig-registration', 'Registration under AIG Article 12', [
        claim('Persons needing a short-stay, residence or settlement permit must register with the authority at their Swiss residence before the permit-free stay expires or before starting work.', AIG, 199, 200),
        claim('AIG Article 12 requires registration with the authority at the new residence when moving to another municipality or canton; federal regulations determine the registration deadlines.', AIG, 201, 202),
    ]),
    concept('permit-l', 'Short-stay permit: AIG Article 32', [
        claim('AIG Article 32 describes the short-stay permit as covering a fixed stay of up to one year, issued for a specified purpose and potentially subject to additional conditions.', AIG, 386, 388),
        claim('Under AIG Article 32(3)-(4), a short-stay permit may be extended up to two years; changing jobs requires important reasons, and a new grant requires an appropriate interruption of the Swiss stay.', AIG, 389, 390),
    ], notes=['Statutory AIG baseline; EU/EFTA employment-specific guidance is exposed separately.']),
    concept('permit-b', 'Residence permit: AIG Article 33', [
        claim('AIG Article 33 defines the residence permit for stays longer than one year. It is purpose-bound, may carry additional conditions, and is time-limited.', AIG, 391, 394),
        claim('A residence permit may be renewed if no revocation grounds under Article 62(1) exist. Integration is considered when setting its duration, and a special integration need can lead to an integration agreement.', AIG, 394, 396),
    ]),
    concept('permit-c', 'Settlement permit: AIG Article 34', [
        claim('The settlement permit is issued for an unlimited period and without conditions under AIG Article 34(1).', AIG, 400, 401),
        claim('AIG Article 34(2) allows settlement after at least ten years with short-stay or residence permits, including the last five years continuously with a residence permit, provided the specified revocation grounds are absent and integration requirements are met. Paragraphs 3 and 4 provide shorter-stay routes, so ten years is not a universal waiting period.', AIG, 402, 410),
        claim('For the continuous five-year period, temporary stays do not count. Education stays count when followed by two uninterrupted years with a residence permit for a durable stay, as specified by AIG Article 34(5).', AIG, 411),
    ]),
    concept('aig-study', 'Study admission under AIG Article 27', [
        claim('AIG Article 27 allows admission for education or further training when the school confirms admission, suitable accommodation and necessary funds are available, and the personal and educational prerequisites are met. Care must be ensured for minors.', AIG, 314, 324),
        claim('After education is completed or discontinued, a further Swiss stay is governed by the AIG general admission conditions.', AIG, 325),
    ], selector=('population', 'third_country')),
    concept('integration-criteria', 'Integration criteria and personal circumstances', [
        claim('AIG Article 58a lists respect for public security and order, respect for Federal Constitution values, language skills, and participation in economic life or education as integration criteria.', AIG, 668, 677),
        claim('Disability, illness or other weighty personal circumstances that prevent or hinder meeting the language and economic-participation or education criteria must be appropriately taken into account.', AIG, 678),
    ]),
    concept('family-swiss', 'Family reunification with a Swiss sponsor: Article 42(1)', [
        claim('Under AIG Article 42(1), foreign spouses and unmarried children under 18 of Swiss citizens are entitled to a residence permit and its renewal if they live with the Swiss family member.', AIG, 474, 475),
    ], selector=('sponsor_status', 'swiss'), notes=['Only Article 42(1) baseline; Article 42(2) and other special entitlements are not modelled.']),
    concept('family-c', 'Family reunification with a settlement-permit sponsor', [
        claim('AIG Article 43(1) provides an entitlement for the foreign spouse and unmarried children under 18 of a settlement-permit holder if they live together, have suitable housing, do not depend on social assistance, meet the language condition, and the sponsor neither receives nor would become eligible for the specified annual supplementary benefits because of reunification.', AIG, 484, 495),
        claim('For initial issuance under Article 43, enrolment in a language-support programme suffices instead of the language ability condition. That condition does not apply to unmarried children under 18.', AIG, 496, 497),
    ], selector=('sponsor_status', 'c')),
    concept('family-b', 'Family reunification with a residence-permit sponsor', [
        claim('AIG Article 44(1) permits, rather than itself guarantees, issuance and renewal for the foreign spouse and unmarried children under 18 of a residence-permit holder if they live together, have suitable housing, do not depend on social assistance, meet the language condition, and the sponsor neither receives nor would become eligible for the specified annual supplementary benefits because of reunification.', AIG, 503, 514),
        claim('For initial issuance under Article 44, language-course enrolment can replace the language ability condition. The condition does not apply to unmarried children under 18.', AIG, 515, 516),
    ], selector=('sponsor_status', 'b')),
    concept('family-deadlines', 'AIG family-reunification deadlines', [
        claim('AIG Article 47 sets a five-year deadline to claim family reunification, shortened to twelve months for children over twelve. These deadlines do not apply to the Article 42(2) route.', AIG, 539, 541),
        claim('For Swiss family members under Article 42(1), the deadline starts with their entry or creation of the family relationship. For foreign sponsors, it starts with grant of the residence or settlement permit or creation of the family relationship.', AIG, 542, 546),
        claim('Late family reunification is approved only when important family reasons are invoked. Children over fourteen are heard where necessary.', AIG, 547),
    ], notes=['AIG Article 47 scope only; no automatic calculation or EU/EFTA deadline inference.']),
    concept('family-separation', 'Residence after dissolution of family life', [
        claim('For the family-based routes listed in AIG Article 50(1), continued permission after dissolution is based on either a marital union lasting at least three years together with fulfilment of integration criteria, or important personal reasons requiring continued residence. The alternatives must not be collapsed into a universal three-year requirement.', AIG, 563, 568),
    ], notes=['The pilot does not assess individual important personal reasons or domestic-violence evidence.']),
    concept('canton-change', 'Change of canton under AIG Article 37', [
        claim('Under AIG Article 37(1), short-stay and residence-permit holders must request permission from the new canton before moving their residence there.', AIG, 425, 426),
        claim('Article 37 grants residence-permit holders a right to change canton if they are not unemployed and the specified revocation grounds are absent. Settlement-permit holders have that right if Article 63 revocation grounds are absent; a temporary stay in another canton needs no permit.', AIG, 427, 429),
    ], selector=('population', 'third_country'), notes=['EU/EFTA geographical-mobility rules are not determined by this AIG-only operation.']),
    concept('third-country-work', 'Third-country employment admission', [
        claim('SEM describes ordinary third-country employment admission as restricted to well-qualified people, including managers, specialists and other qualified workers, primarily graduates with several years of professional experience. For a stay of several years, integration criteria are also considered.', WORK, 74, 76),
        claim('The prospective employer must show that no suitable person is available in the domestic and EU/EFTA labour markets. Pay, social-insurance contributions and working conditions must match Swiss local, occupational and industry standards.', WORK, 77),
    ], selector=('population', 'third_country'), notes=['Baseline criteria only; quotas, exceptions and final admission decisions are not computed.']),
    concept('eu-short-employment', 'EU/EFTA short employment: notification', [
        claim('For EU/EFTA nationals taking employment with an employer in Switzerland for up to three months within a calendar year, the electronic notification procedure applies. Employment longer than three months requires a residence permit or, where its conditions are met, a cross-border commuter permit.', NOTIFY, 92, 100),
        claim('For employment with a Swiss employer under a contract lasting up to three months, notification must be made no later than the day before work starts.', NOTIFY, 93),
    ], selector=('population', 'eu_efta'), notes=['Three months of Swiss employment and 90 effective service-provision workdays are distinct measures.']),
    concept('notification-responsibility', 'Who submits a short-work notification', [
        claim('Employers notify posted employees and EU/EFTA nationals taking employment in Switzerland; self-employed service providers must notify themselves.', NOTIFY, 104),
    ]),
    concept('posted-service-notification', 'Cross-border services: duration and notification timing', [
        claim('The free-movement arrangement liberalises cross-border services for up to 90 effective working days per calendar year; the limit applies to both the posting enterprise and the posted person. Service provision exceeding 90 days needs a work permit and has no automatic entitlement.', NOTIFY, 89, 91),
        claim('When notification is required for posted workers or self-employed service providers, it must normally be made at least eight days before work begins. The cited emergency exception requires both prevention of further damage following sudden damage and an assignment starting no later than three days after the damage, including Sundays and holidays.', NOTIFY, 117, 120),
    ], notes=['Service-provider eligibility and sector-specific first-day obligations require the full source; no blanket eight-day exemption is asserted.']),
    concept('uk-new-employment', 'New short-term employment by UK nationals', [
        claim('UK nationals taking a Swiss job for up to three months cannot use the short-employment notification route; a work permit under the AIG is required.', NOTIFY, 181, 182),
        claim('The Swiss employer must submit that work-permit application to the competent cantonal authority.', NOTIFY, 181, 183),
        claim('SEM states that after the United Kingdom left the EU, the free-movement agreement stopped applying to Switzerland-UK relations at the end of the transition period on 31 December 2020, and that since 1 January 2021 UK nationals no longer count as EU citizens; the separate temporary services-mobility agreement has applied since 1 January 2021 and remains valid until 31 December 2029.', NOTIFY, 176, 177),
    ], selector=('population', 'uk_new'), validity=dict(valid_from='2021-01-01'),
       notes=['New Swiss employment only; acquired rights and cross-border service agreements are separate.',
              'Source-stated commencement: applies since 1 January 2021, the end of the Brexit transition period. The 31 December 2029 expiry cited for the services-mobility agreement does not limit this employment rule.']),
    concept('biometric-permit', 'Biometric residence-card data and issuance', [
        claim('SEM states that the biometric residence-card chip stores two digital fingerprints and a facial image. The data are retained for five years for reissuance without collecting them again.', BIO, 90),
        claim('The canton of residence sets the application and issuance procedure and collects the biometric data using the national passport for identification. Charges are separated into the permit procedure, card production and biometric-data collection.', BIO, 92),
    ]),
    concept('language-evidence', 'Evidence of language skills', [
        claim('SEM normally requires an accepted language certificate. Exemptions include proving that the local language is the mother tongue, at least three years of compulsory schooling in it, or upper-secondary or tertiary education in that language.', FAQ, 157),
        claim('SEM states that disability, learning, reading or writing difficulties, or other weighty personal circumstances can justify dispensing with the sufficient-language-skills requirement.', FAQ, 154),
    ], notes=['Required proficiency level depends on the permit; this operation does not assign a universal CEFR level.']),
    concept('social-assistance-review', 'Social assistance and permit consequences', [
        claim('SEM states that receipt of social assistance can have immigration consequences but does not cause them automatically. The cantonal migration authority decides individually and proportionately.', FAQ, 220, 223),
    ]),
    concept('zh-eu-registration', 'Zurich registration for EU/EFTA nationals', [
        claim('Zurich states that EU/EFTA nationals entering Switzerland need a valid passport or identity card. After entry they apply personally through the residents registration office for the longer stays described on the page; the office forwards the application to the cantonal migration office.', ZH, 63, 66),
        claim('For EU/EFTA nationals wishing to work in Switzerland for longer than 90 days, Zurich specifies personal registration with the municipality within fourteen days. The page also describes an alternative three-month stay to look for work without a permit.', ZH, 75),
    ], canton='CH-ZH', selector=('population', 'eu_efta')),
    concept('zh-eu-l', 'Zurich EU/EFTA short-stay employment permit', [
        claim('Zurich describes an EU/EFTA L permit for an employment contract lasting more than three months but less than one year, with average working time above fifteen hours per week.', ZH, 81, 82),
    ], canton='CH-ZH', selector=('population', 'eu_efta')),
    concept('zh-eu-b', 'Zurich EU/EFTA residence employment permit', [
        claim('Zurich describes an EU/EFTA B permit for an indefinite employment contract or one lasting longer than a year, with average working time above fifteen hours per week.', ZH, 85, 86),
    ], canton='CH-ZH', selector=('population', 'eu_efta')),
    concept('zh-eu-self-employment', 'Zurich EU/EFTA self-employment documentation', [
        claim('For assessment of self-employment, Zurich requires evidence of a Swiss business or establishment with active business activity, recognition by the cantonal social-insurance institution, and income and asset evidence. The residence application is submitted to the municipality.', ZH, 95, 100),
    ], canton='CH-ZH', selector=('population', 'eu_efta')),
    concept('zh-eu-nonworking', 'Zurich EU/EFTA residence without employment', [
        claim('Zurich lists students, retirees, jobseekers and other non-working EU/EFTA nationals as possible applicants. Sufficient funds and adequate health and accident insurance must be demonstrated; further requirements depend on the purpose of stay.', ZH, 103, 110),
    ], canton='CH-ZH', selector=('population', 'eu_efta')),
    concept('zh-eu-family-documents', 'Zurich EU/EFTA family-reunification documents', [
        claim('Zurich lists proof of the family relationship, custody or foster-care evidence where applicable, sufficient funds for non-working sponsors, evidence of maintenance and former shared residence where applicable, and a rental agreement for suitable housing among the family-reunification documents.', ZH, 118, 123),
    ], canton='CH-ZH', selector=('population', 'eu_efta'), notes=['Document checklist only; does not determine which relatives qualify.']),
    concept('zh-third-country-retirement', 'Zurich third-country retirement applications', [
        claim('Zurich states that retired third-country nationals have no entitlement to a permit. Applications are examined when the applicant is at least 55, has special personal ties to Switzerland and sufficient funds, and performs no gainful activity abroad except managing their own assets.', ZH_RETIRED, 50, 56),
    ], canton='CH-ZH', selector=('population', 'third_country')),
    concept('city-zurich-arrival', 'City of Zurich: registering arrival from abroad', [
        claim('For arrival from abroad, the City of Zurich requires an appointment and personal registration at Personenmeldeamt Zurich Sud. Without an appointment registration is not possible; for family registration every family member must attend in person.', CITY, 31, 33),
    ], canton='CH-ZH', municipality='261', selector=('arrival_origin', 'abroad')),
    concept('city-zurich-arrival-documents', 'City of Zurich: documents for arrival from abroad', [
        claim('The City of Zurich lists a passport (an identity card suffices for EU/EFTA nationals), rental or housing documentation, permit assurance and visa authorisation if available, an employment contract or study confirmation, applicable migration fees, and original civil-status documents for registration from abroad.', CITY, 34, 42),
    ], canton='CH-ZH', municipality='261', selector=('arrival_origin', 'abroad')),
    concept('eu-employment-registration-deadline', 'EU/EFTA employment: municipal registration deadline after arrival', [
        claim('SEM states that EU/EFTA nationals taking up employment of more than three months must register with their municipality of residence and apply for a residence permit within 14 days of their arrival in Switzerland and before starting work. A valid identity card or passport and the employer\'s written confirmation of employment (for example the contract with its duration and workload) must be presented; the contract duration determines whether a short-stay permit L or a residence permit B is issued.', FZA_FAQ, 98, 99),
        claim('SEM states that the steps needed to obtain the residence permit can be completed after arrival in Switzerland.', FZA_FAQ, 100),
    ], selector=('population', 'eu_efta'), notes=['Both limits apply together: the 14-day period is counted from the arrival in Switzerland, not from the first working day, and registration must precede the start of work.']),
    concept('health-insurance-enrolment', 'Compulsory health-insurance enrolment timing', [
        claim('Where Swiss compulsory health insurance applies, enrolment must occur within three months of the start of the obligation and is retroactive to that date, including the premiums.', BAG, 45, 46),
        claim('With late enrolment, coverage starts only on joining; an inexcusable delay incurs a premium surcharge.', BAG, 47, 48),
    ], selector=('insurance_obligation', 'applies'), notes=['Whether the insurance obligation applies, including international-coordination exceptions, is not decided here.']),
]

# Explicitly reviewed migration-office rows in the SEM directory. Labour offices,
# Liechtenstein and separate municipal offices are not mistaken for cantonal rows.
CONTACT_ROWS = [
    ('AG', 'Aargau', 79, 80), ('AI', 'Appenzell Innerrhoden', 84, 85),
    ('AR', 'Appenzell Ausserrhoden', 89, 90), ('BE', 'Bern', 94, 95),
    ('BL', 'Basel-Landschaft', 108, 109), ('BS', 'Basel-Stadt', 113, 114),
    ('FR', 'Fribourg', 123, 124), ('GE', 'Geneva', 128, 129),
    ('GL', 'Glarus', 133, 134), ('GR', 'Graubunden', 138, 139),
    ('JU', 'Jura', 143, 144), ('LU', 'Lucerne', 148, 149),
    ('NE', 'Neuchatel', 153, 154), ('NW', 'Nidwalden', 158, 159),
    ('OW', 'Obwalden', 163, 164), ('SG', 'St Gallen', 168, 169),
    ('SH', 'Schaffhausen', 175, 176), ('SO', 'Solothurn', 180, 181),
    ('SZ', 'Schwyz', 185, 186), ('TG', 'Thurgau', 190, 191),
    ('TI', 'Ticino', 195, 196), ('UR', 'Uri', 200, 201),
    ('VD', 'Vaud', 205, 206), ('VS', 'Valais', 213, 214),
    ('ZG', 'Zug', 218, 219), ('ZH', 'Zurich', 223, 223),
]

SELECTOR_VALUES = {
    'population': ['eu_efta', 'third_country', 'uk_new', 'uk_acquired'],
    'sponsor_status': ['swiss', 'b', 'c', 'other'],
    'arrival_origin': ['abroad', 'within_switzerland'],
    'insurance_obligation': ['applies', 'exempt', 'unknown'],
}
