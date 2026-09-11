# OpenCode caller test: Chinese question on third-country work admission - 11 September 2026

Second standing caller integration case, after the
[Zurich registration case](2026-09-11-opencode-real-mcp-caller-test.md). Two
things are new: the user writes in a language the release does not contain
(Chinese; the release serves German and English sources and publishes no term
routes), and the question is a third-country admission question, so the caller
has to pick the `third_country` population and leave out everything that only
applies to EU/EFTA nationals.

The MCP server never sees the question. It receives identifiers, a jurisdiction, a
population value and a date; the caller reads the facts and German excerpts and
renders the answer in Chinese. The test therefore checks the caller's cross-lingual
discovery, its choice of concepts and context, whether it keeps to the served facts,
and whether it avoids the one server-side language path (`retrieval_terms` and
`source_languages` tagged `zh`).

## Question

English source: "I'm chinese citizen, an I allowed to work in Switzerland? What
are conditions to get the work and residence permit?"

Sent verbatim in Chinese:

> 我是中国公民，我可以在瑞士工作吗？获得工作许可和居留许可需要哪些条件？

Follow-up in the same session (scenario `qualified-employee`):

> 我有硕士学位和六年软件工程师工作经验。苏黎世的一家公司想聘用我，合同是无固定期限的。

## Expected answer

Prepared before the run from the facts pilot release v2 serves; nothing else
counts as supported. The caller should answer in Chinese and cite the SEM and
Fedlex URLs below.

**Turn 1 must say:**

1. 可以，但有条件。作为非欧盟/欧洲自由贸易联盟（第三国）公民，只有具备良好资质的人才能获准在瑞士工作：管理人员、专家和其他合格的专业人员，主要是拥有高校或应用科学大学学位并有多年工作经验的人。多年居留时还会考虑融入标准（职业和社会适应能力、语言能力、年龄）。
   Source: `mvp-fact-third-country-work-1`, SEM "Nicht-EU/EFTA-Angehörige",
   <https://www.sem.admin.ch/sem/de/home/themen/arbeit/nicht-eu_efta-angehoerige.html>.
2. 雇主必须证明在瑞士国内劳动力市场和欧盟/欧洲自由贸易联盟国家的劳动力市场上找不到适合该职位的人（本国和欧盟/EFTA 优先）。工资、社会保险缴费和工作条件必须符合瑞士当地、行业和职业的通常标准。
   Source: `mvp-fact-third-country-work-2`, same page.
3. 无论停留时间长短，在瑞士工作都需要许可。对于受雇工作，许可由雇主向工作地点的主管机关申请，不是由本人申请。
   Source: `mvp-fact-aig-work-permit-1`, `mvp-fact-aig-work-permit-2`, AIG Art. 11,
   <https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/2007/758/20260612/de/html/fedlex-data-admin-ch-eli-cc-2007-758-20260612-de-html-3.html>.
4. 居留许可由州移民局签发。
   Source: `mvp-fact-permit-authority-1`, SEM "Residence" (en).

**Turn 1 should also say (present in the release, lower priority):**

5. 许可类型：短期居留许可 L（最长一年，限定目的）或居留许可 B（一年以上，限定目的，有期限，可延期）。
   Source: `mvp-fact-permit-l-1`, `mvp-fact-permit-b-1`, AIG Art. 32 and 33.
6. 抵达后须在免许可停留期届满前或开始工作前，向瑞士居住地的主管机关登记。
   Source: `mvp-fact-aig-registration-1`, AIG Art. 12.
7. 限制说明：知识库不包含配额、签证程序、具体申请文件和处理时间；这些应向雇主所在州的移民局或 SEM 确认。

**Turn 2 must say:** the profile (master's degree, six years of experience) matches
the "well-qualified" description, but admission is not automatic: the Zurich
employer must file the application and show that no suitable candidate is
available in Switzerland or the EU/EFTA, and pay and conditions must match local
standards. With an open-ended contract the permit type is the B residence permit
(stay longer than one year). The employer's canton, Zurich, decides. Registration
with the municipality happens before starting work. A supported answer does not
promise approval or name a processing time.

**Tool use expected:** discovery without arguments, the pinned release, the topic
listing, then `resolve` for `residence-third-country-work` with
`population: third_country`, plus `residence-aig-work-permit` (also
`population: third_country`); optionally `residence-permit-authority`,
`residence-permit-b`, `residence-permit-l`, `residence-aig-registration`. All with
`country_code: CH` only, `scope_mode: exact`, `as_of` 2026-09-10 or 2026-09-11,
`retrieval_terms` empty, `source_languages` unset.

## Failure signatures

- `retrieval_terms` or `source_languages` tagged `zh` (server answers
  `UNSUPPORTED_LANGUAGE` or `OUT_OF_COVERAGE`; the query language never implies a
  source-language filter).
- `population: eu_efta`, or facts that only apply to EU/EFTA nationals (14-day
  registration, notification procedure, free movement) presented as applying to a
  Chinese citizen.
- "No, you cannot work in Switzerland" or "Yes" without the qualification and
  employer conditions.
- Details from model knowledge presented as served facts: quota numbers, salary
  thresholds, visa steps, processing times, permit validity in years, the
  employer's documents list.
- Answer composed while `resolve` returned no supported fact (the release
  contains the two SEM sentences; if they are not in the answer, the concept was
  not resolved).
- Answering in English or German rather than Chinese is a usability note, not a
  correctness failure.

## Run

`run-20260911-212740-real-chinese-work-permit` (Git-ignored transcripts and
`summary.json` under `.local/mock-mcp/runs/`). OpenCode 1.18.29, model
`opencode/ling-3.0-flash-fin-free`, the same `residence-assistant` agent, system
prompt and tool-output cap as the Zurich case, pilot release v2 through the real
server. One run, one scenario, two turns.

| Turn | Tool calls | Outcome |
| --- | --- | --- |
| 1 (Chinese question) | 12 calls, 40 s: root, knowledge space, one error (child listing without `release_id`), topic listing (121 KB), `residence-third-country-work` supported with `population: third_country`, `residence-aig-work-permit` supported, three errors (`context` omitted; `topic_id` omitted twice), `residence-permit-b` and `residence-permit-authority` supported, `get_evidence` for the four SEM and AIG excerpts | Answer in Chinese with every expected point 1 to 4, the B permit, and the coverage limitation; see comparison |
| 2 (profile supplied) | 5 calls, 20 s: topic listing again, `residence-integration-criteria` supported, `residence-permit-b` with `canton_code: CH-ZH` `OUT_OF_COVERAGE`, `residence-language-evidence` supported, `residence-city-zurich-arrival` supported (municipality 261) | B permit, employer files, market test, pay, canton Zurich issues, no promise of approval; plus an over-applied language section and two sentences of model knowledge; see comparison |

No retrieval term or source filter was tagged `zh`; the server returned no
`UNSUPPORTED_LANGUAGE`. The four typed `INVALID_ARGUMENT` errors were each
corrected on the next call. All heuristic checks of the harness passed.

## Comparison with the expected answer

**Turn 1.** Points 1 to 4 are present and faithful to the served facts: the
SEM qualification sentence (managers, specialists, graduates with several years
of experience) with the integration criteria for multi-year stays; the employer's
proof that nobody suitable is available in Switzerland or the EU/EFTA, with pay,
social insurance and working conditions at local standards; AIG Article 11
(permit regardless of duration, application at the place of work, filed by the
employer); permits issued by the cantonal migration offices. Both SEM URLs and
the Fedlex URL are cited. Point 5 is half present: the B permit from Article 33
including renewal and the integration agreement (fact `mvp-fact-permit-b-2`), no L
permit because `residence-permit-l` was not resolved. Point 6 (registration
before starting work, Article 12) is missing from turn 1; turn 2 gives the City of
Zurich appointment instead. Point 7 is present: quotas, exceptions and the final
decision are named as outside the data, with the snapshot date and the "no legal
review" label quoted, and SEM plus the cantonal office recommended.

One simplification: the answer presents "work permit" and "residence permit B" as
two sequential applications. For a third-country employee they are one permit
for gainful employment; no served fact says so, and the model followed the
wording of the question.

**Turn 2.** The expected core is there: the profile matches "well qualified", the
employer files and must pass the labour-market test, pay at local standards, B
permit for the open-ended contract, Zurich as the issuing canton, the City of
Zurich appointment (served fact), and no promise of approval. Deviations:

- Model knowledge as guidance: "an open-ended contract is usually more favourable
  for approval than a fixed-term one". Not served.
- Over-applied fact: `residence-language-evidence` (SEM FAQ: language skills are
  proven with an accepted certificate, with exemptions) was turned into "Step 4:
  language requirement, you need a recognised German certificate" for the work
  permit. The served fact carries no applicability condition and the model
  attached it to the wrong permit. The exemption list also drifted: "studied at a
  Swiss university in German for at least three years" merges two separate
  exemptions (three years of compulsory school; upper-secondary or tertiary
  education in the language).
- Integration criteria from AIG Article 58a are served; "no criminal record" is
  the model's gloss of "public security and order".
- The annual-quota sentence is model knowledge, but it is placed under "not in the
  data", which is the right label. Goethe-Zertifikat and TestDaF are model
  suggestions, labelled as advice.
- An unsourced URL: the cantonal contact concept was not resolved, and the model
  supplied a zh.ch address from memory.
- `residence-permit-b` with `canton_code: CH-ZH` returned `OUT_OF_COVERAGE` (exact
  jurisdiction matching, as in the Zurich case); the model reused its turn 1
  result.

Verdict: pass on the standing case. The question in a language the release does
not hold changed nothing on the server side, and the caller kept to the served
facts in turn 1. The turn 2 deviations are the known caller pattern: once the
served facts run out, the model fills in from memory and applies general facts
beyond their scope.

## Findings for the service

- **Language independence confirmed.** Chinese in, Chinese out, German and English
  facts in between, no language field touched. The one server-side language path
  (term routes) was never entered because the tool description says to leave
  `retrieval_terms` empty.
- **`context` should default to an empty object.** The model omitted `context` on a
  profile whose schema has no fields and got `INVALID_ARGUMENT: context missing`.
- **All three scope IDs.** `topic_id` was dropped twice when the model rewrote a
  request. The resolve description could state that `knowledge_space_id`,
  `domain_id` and `topic_id` are all required.
- **Applicability conditions on facts.** The language-certificate fact was applied
  to a work permit. `applicability_conditions` exists on published facts and is
  empty in the pilot release; filling it (which permits or procedures the fact
  belongs to) would give the caller the boundary it lacked.
- **Missing fact.** For third-country employees the employment permit and the L/B
  residence permit are the same permit. Without a fact stating this, the caller
  described two applications.
- **Unresolved concepts invite invented URLs.** When a concept exists in the
  catalog but is not resolved, the caller may still supply an address from
  memory. A cheap "contact" concept resolve, or a caller instruction to cite only
  returned URLs, would avoid this.

## Limitations

- One model, one question, one scenario, one run. Not a qualification of Ling,
  the contract or the release.
- The Chinese question and the expected answer were written by the assistant that
  curated the release; no native-speaker or legal review.
- The harness assessment is keyword matching on the Chinese answer; the
  transcript below is the evidence.

## Reproduce

```shell
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --server real --case chinese-work-permit --check-connection
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --server real --case chinese-work-permit --live
```

## Full message exchange

Final assistant texts only; tool calls are summarised in the run table.

### Turn 1

User: 我是中国公民，我可以在瑞士工作吗？获得工作许可和居留许可需要哪些条件？

Assistant:

根据我从 SwissTIP（瑞士官方移民信息系统的数据快照）中查询到的官方信息，以下是关于中国公民在瑞士工作的综合回答：

---

## 中国公民可以在瑞士工作吗？

**可以，但条件严格。** 中国属于"非欧盟/EFTA国家"（Nicht-EU/EFTA-Staat），因此适用瑞士针对第三国国民的严格工作许可制度。

---

## 核心法律依据

根据《外国人和融合法》（AIG/LEI/FNIA，SR 142.20）：

> **AIG 第11条第1款**：任何想在瑞士从事有偿工作的外国人，**无论停留时间长短**，都需要获得许可（Bewilligung）。申请须在计划工作地点的主管机关提出。
>
> **AIG 第11条第3款**：对于受雇（unselbständige）工作，**由雇主**（而非雇员本人）提出许可申请。

来源：[Fedlex - AIG/LEI/FNIA, SR 142.20](https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/2007/758/20260612/de/html/fedlex-data-admin-ch-eli-cc-2007-758-20260612-de-html-3.html)

---

## 第三国国民获得工作许可的条件

根据瑞士联邦移民局（SEM）的规定：

### 1. 资质要求（Qualifikation）
- 仅允许**"充分合格"**（gut qualifiziert）的人员入境工作。
- "充分合格"指：**管理人员**（Führungskräfte）、**专业人员**（Spezialistinnen und Spezialisten）及其他合格劳动力。
- 主要标准是：**拥有大学或应用科学大学（Hochschule/Fachhochschule）学位**，并具备**数年职业经验**。

### 2. 劳动力市场测试（Arbeitsmarktprüfung）
- 雇主必须证明：**在瑞士国内市场**和**欧盟/EFTA国家劳动力市场**上，**没有合适的人员**可以胜任该职位。
- 工资、社会保险缴费和工作条件必须符合**瑞士当地、职业和行业的惯例标准**。

### 3. 融合标准（Integrationskriterien）
- 对于**长期居留**，还会考虑融合因素：
  - 职业和社会适应能力
  - 语言能力
  - 年龄（是否能预期在瑞士劳动力市场和社会环境中长期融入）

来源：[SEM - Nicht-EU/EFTA-Angehörige](https://www.sem.admin.ch/sem/de/home/themen/arbeit/nicht-eu_efta-angehoerige.html)

---

## 居留许可（Aufenthaltsbewilligung）

### 许可类型
根据AIG第33条：
- **许可B（Permit B）**：适用于停留超过一年的情况。它是**有目的限制的**（für einen bestimmten Aufenthaltszweck），可附带额外条件，且**有期限**（befristet）。
- 如果没有撤销理由（Art. 62 Abs. 1），许可可以**续期**。
- 续期时考虑融合因素；如存在特殊融合需求，可能需要签署**融合协议**（Integrationsvereinbarung）。

### 发证机关
居留许可由**各州移民局**（Cantonal Migration Offices）签发。

来源：[SEM - Residence](https://www.sem.admin.ch/sem/en/home/themen/aufenthalt.html)

---

## 总结：申请流程概要

1. **找到瑞士雇主**，雇主需通过劳动力市场测试。
2. **雇主向主管州移民局提交**工作许可申请（Art. 11(3)）。
3. 移民局审核：资质、劳动力市场空缺情况、薪资/工作条件是否符合标准。
4. 获得工作许可后，申请**居留许可B**（如停留超过一年）。
5. 居留许可由**所在州的移民局**签发，需满足融合相关要求。

---

## 重要提醒

⚠️ **本数据来源说明**：以上信息来自 SwissTIP 系统的实验性数据快照（版本日期 2026-09-11），该系统明确声明为"助理策展的实验性MVP数据；未经独立法律审查"，且为"冻结快照测试窗口；瑞士法律覆盖不完整"。配额、例外情况和最终准入决定不在本数据计算范围内。

**建议您在采取任何行动前，查阅以下官方渠道获取最新和完整的信息：**
- 瑞士联邦移民局（SEM）：[https://www.sem.admin.ch](https://www.sem.admin.ch)
- 瑞士联邦法律汇编（Fedlex）：[https://fedlex.data.admin.ch](https://fedlex.data.admin.ch)
- 您计划定居所在州的移民局网站

### Turn 2

User: 我有硕士学位和六年软件工程师工作经验。苏黎世的一家公司想聘用我，合同是无固定期限的。

Assistant:

综合所有查询结果，以下是针对您个人情况的完整分析：

---

## 您的情况评估：非常有利 ✅

| 条件 | 您的情况 | 官方要求 | 评估 |
|------|---------|---------|------|
| 学历 | 硕士学位 | Hochschul-/Fachhochschulabschluss | ✅ 满足 |
| 经验 | 6年软件工程师 | "mehrjährige Berufserfahrung" | ✅ 满足 |
| 合同 | 无固定期限 | 长期就业 | ✅ 稳定 |
| 工作地 | 苏黎世 | — | ✅ 州级可办理 |

根据 SEM 的官方定义，您**完全符合"充分合格"（gut qualifiziert）**的标准——拥有大学学位加上多年专业经验的管理人员/专业人员。

---

## 具体申请流程与条件

### 第一步：雇主申请工作许可（Bewilligung）

根据 **AIG 第11条**（来源：[Fedlex](https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/2007/758/20260612/de/html/fedlex-data-admin-ch-eli-cc-2007-758-20260612-de-html-3.html)）：

1. **雇主**（不是您本人）向**工作所在地的主管机关**提出申请（AIG Art. 11(3)）
2. **劳动力市场测试**：雇主必须证明在**瑞士国内市场**和**欧盟/EFTA国家劳动力市场**上没有合适的候选人可以填补该职位
3. **薪资与工作条件**必须符合瑞士当地、职业和行业的标准

> ⚠️ 您的无固定期限合同是一个积极因素——它表明长期稳定的就业关系，通常比固定期限合同更有利于通过审批。

### 第二步：获得许可后的居留许可（B）

由于您计划在瑞士停留超过一年，将适用 **AIG 第33条**：

- **许可B（Aufenthaltsbewilligung）**：有目的限制（因工作），可附带条件，有期限，可续期
- 续期条件：无撤销理由（AIG Art. 62(1)）
- 居留许可由**苏黎世州移民局**（Kantonales Migrationsamt Zürich）签发

### 第三步：整合标准（Integrationskriterien）

由于您申请的是长期居留，根据 **AIG 第58a条**，以下整合标准将被考虑：

| 标准 | 说明 |
|------|------|
| **公共安全与秩序** | 无犯罪记录 |
| **宪法价值观** | 尊重瑞士法律体系 |
| **语言能力** | 见下文详述 |
| **经济参与/教育** | 就业本身即满足此条 |

### 第四步：语言要求

根据 SEM 的官方 FAQ（[来源](https://www.sem.admin.ch/sem/de/home/themen/aufenthalt/faq.html)）：

- 需要**认可的德语（或法语/意大利语）语言证书**
- **可能的豁免条件**（您可能符合其中一项或多项）：
  - ✅ 在瑞士**大学（高等教育）**用德语学习至少3年
  - ✅ 已完成**高等教育**（硕士）且教学语言为德语
  - ✅ 在瑞士完成**义务教育3年以上**
- 残障、学习困难或其他重大个人情况可豁免语言要求

> **重要提示**：所需的确切语言水平取决于许可类型和州，SEM 不设定统一的 CEFR 级别。建议向苏黎世州移民局确认具体要求。

### 第五步：苏黎世市注册

抵达苏黎世后，根据苏黎世市人口办公室的规定（[来源](https://www.stadt-zuerich.ch/de/lebenslagen/einwohner-services/umziehen-melden/zuzug.html)）：

- **必须预约**并亲自前往 **Personenmeldeamt Zürich Sud** 办理登记
- **无预约不可登记**
- 家属登记时，所有家庭成员须亲自到场

---

## 苏黎世州移民局联系方式

根据覆盖数据，苏黎世州的移民局联系信息可通过各州移民局名录查询。您可以搜索：
- **Kantonales Migrationsamt Zürich**（苏黎世州移民局）
- 官方网站：[https://www.zh.ch/de/themen/buerger-und-auslaenderrecht.html](https://www.zh.ch/de/themen/buerger-und-auslaenderrecht.html)

---

## 重要限制与免责

⚠️ 本数据来自 SwissTIP 实验性快照（2026-09-11），以下事项**不在数据覆盖范围内**：
- **配额制度**（Kontingent）：第三国国民工作许可受年度配额限制
- **例外情况**和**最终准入决定**
- 完整的申请文件清单

**建议行动步骤**：

1. **与雇主确认**：由雇主启动工作许可申请流程
2. **联系苏黎世州移民局**：确认具体文件要求和语言水平要求
3. **准备语言证书**：如未满足豁免条件，尽早准备德语考试（如Goethe-Zertifikat, TestDaF等）
4. **访问官方网站获取最新完整信息**：
   - [SEM - Nicht-EU/EFTA-Arbeitnehmer](https://www.sem.admin.ch/sem/de/home/themen/arbeit/nicht-eu_efta-angehoerige.html)
   - [Fedlex - AIG/LEI/FNIA, SR 142.20](https://fedlex.data.admin.ch)
   - [苏黎世市 - 移居登记](https://www.stadt-zuerich.ch/de/lebenslagen/einwohner-services/umziehen-melden/zuzug.html)
