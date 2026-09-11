import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Badge,
  Button,
  Checkbox,
  FileButton,
  Group,
  Loader,
  Modal,
  Paper,
  ScrollArea,
  Select,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import {
  IconArrowRight,
  IconBook2,
  IconCheck,
  IconDatabase,
  IconFileText,
  IconLayersIntersect,
  IconPlayerPlay,
  IconSearch,
  IconUpload,
  IconWorld,
} from "@tabler/icons-react";
import * as api from "./api/sdk.gen";
import { client } from "./api/client.gen";
import type { Asset, Job, JobRequest, ReviewRequest } from "./api/types.gen";

client.setConfig({ baseUrl: "", headers: { "X-Swisstip-Local": "1" } });
async function unwrap<T>(
  promise: Promise<{ data?: T; error?: unknown }>,
): Promise<T> {
  const response = await promise;
  if (response.error || response.data === undefined) {
    const error = response.error as { detail?: unknown } | undefined;
    throw new Error(
      typeof error?.detail === "string"
        ? error.detail
        : JSON.stringify(
            error?.detail || "The service could not complete this request.",
          ),
    );
  }
  return response.data;
}
function download(value: unknown, name: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
const formatDate = (date: string) => new Date(date).toLocaleString();
const extractionLabel = (profile?: string) =>
  profile === "concept_extraction_v3"
    ? "V3 concepts and evidence"
    : profile === "concept_extraction_v4"
      ? "V4 structured claims"
      : profile || "Configured extraction";
const statusColor = (status: string) =>
  ({
    completed: "teal",
    running: "blue",
    queued: "gray",
    needs_attention: "orange",
    failed: "red",
    cancelled: "gray",
    interrupted: "orange",
  })[status] || "gray";
type Candidate = {
  candidate_id: string;
  preferred_label: string;
  description: string;
  scope?: string;
  user_questions?: string[];
  structured_claims?: {
    claim_id: string;
    statement: string;
    conditions?: { text: string }[];
  }[];
  evidence?: {
    section_id?: string;
    quote?: string;
    excerpt?: string;
    text?: string;
  }[];
};
type Report = {
  title?: string;
  prompt_profile?: string;
  candidates?: Candidate[];
  warnings?: string[];
  source_inventory?: unknown[];
};

export function App() {
  const cache = useQueryClient();
  const [tab, setTab] = useState("sources");
  const [search, setSearch] = useState("");
  const [sources, setSources] = useState<string[] | undefined>();
  const [selectedAssets, setSelectedAssets] = useState<string[]>([]);
  const [corpusId, setCorpusId] = useState<string | null>(null);
  const [profile, setProfile] = useState<string | null>(null);
  const [previewAsset, setPreviewAsset] = useState<Asset | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [releaseId, setReleaseId] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<JobRequest | null>(null);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadSource, setUploadSource] = useState<string | null>(
    "ch-sem-residence-en",
  );
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const catalog = useQuery({
    queryKey: ["catalog"],
    queryFn: () => unwrap(api.getCatalog()),
  });
  const assets = useQuery({
    queryKey: ["assets", corpusId],
    queryFn: () => unwrap(api.getAssets({ query: { corpus_id: corpusId } })),
    refetchInterval: tab === "pages" ? 5000 : false,
  });
  const corpora = useQuery({
    queryKey: ["corpora"],
    queryFn: () => unwrap(api.getCorpora()),
    refetchInterval: tab === "pages" ? 5000 : false,
  });
  const jobs = useQuery({
    queryKey: ["jobs"],
    queryFn: () => unwrap(api.getJobs()),
    refetchInterval: 2000,
  });
  const releases = useQuery({
    queryKey: ["releases"],
    queryFn: () => unwrap(api.getReleases()),
  });
  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => unwrap(api.getJob({ path: { identifier: jobId! } })),
    enabled: !!jobId,
    refetchInterval: (query) =>
      !query.state.data ||
      ["queued", "running"].includes(query.state.data.status)
        ? 1500
        : false,
  });
  const preview = useQuery({
    queryKey: ["preview", previewAsset?.asset_id],
    queryFn: () =>
      unwrap(
        api.previewAsset({ path: { identifier: previewAsset!.asset_id } }),
      ),
    enabled: !!previewAsset,
  });
  const evidence = useQuery({
    queryKey: ["evidence", releaseId],
    queryFn: () =>
      unwrap(api.getReleaseEvidence({ path: { identifier: releaseId! } })),
    enabled: !!releaseId,
  });

  useEffect(() => {
    if (catalog.data && sources === undefined)
      setSources(
        catalog.data.sources.filter((s) => s.selected).map((s) => s.source_id),
      );
  }, [catalog.data, sources]);
  useEffect(() => {
    if (catalog.data && profile === null)
      setProfile(catalog.data.profiles.find((p) => p.selected)?.name || null);
  }, [catalog.data, profile]);
  useEffect(() => {
    if (releases.data?.length && !releaseId)
      setReleaseId(releases.data[0].release_id);
  }, [releases.data, releaseId]);
  const create = useMutation({
    mutationFn: (body: JobRequest) => unwrap(api.createJob({ body })),
    onSuccess: (data) => {
      setJobId(data.job_id);
      setTab("builds");
      setConfirmation(null);
      setError("");
      void cache.invalidateQueries({ queryKey: ["jobs"] });
    },
    onError: (e: Error) => setError(e.message),
  });
  const loadPilot = useMutation({
    mutationFn: () => unwrap(api.loadPilotAssets({ body: {} })),
    onSuccess: async (data) => {
      setNotice(data.message);
      setTab("pages");
      setCorpusId("__legacy__");
      await cache.invalidateQueries({ queryKey: ["assets"] });
      const saved = await unwrap(api.getAssets({ query: { corpus_id: "__legacy__" } }));
      const defaults = new Set(
        catalog.data?.sources.filter((s) => s.selected).map((s) => s.source_id),
      );
      const chosen: string[] = [];
      for (const asset of saved) {
        if (defaults.delete(asset.source_id)) chosen.push(asset.asset_id);
      }
      setSelectedAssets(chosen);
    },
    onError: (e: Error) => setError(e.message),
  });

  async function upload(file: File | null) {
    if (!file || !uploadSource) return;
    try {
      if (file.size > 2_000_000)
        throw new Error("Choose a page smaller than 2 MB.");
      const text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(
        await file.arrayBuffer(),
      );
      const response = await unwrap(
        api.uploadAsset({
          body: { source_id: uploadSource, filename: file.name, text },
        }),
      );
      setNotice(response.message);
      setUploadOpen(false);
      await cache.invalidateQueries({ queryKey: ["assets"] });
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const begin = (kind: "plan" | "extract") => {
    const body: JobRequest = {
      kind,
      asset_ids: selectedAssets,
      source_ids: [],
      profile: profile!,
    };
    if (kind === "plan") create.mutate(body);
    else setConfirmation(body);
  };
  const toggle = (
    id: string,
    values: string[],
    change: (value: string[]) => void,
  ) =>
    change(
      values.includes(id) ? values.filter((v) => v !== id) : [...values, id],
    );
  const visibleSources =
    catalog.data?.sources.filter((s) =>
      `${s.title} ${s.language} ${s.source_id}`
        .toLowerCase()
        .includes(search.toLowerCase()),
    ) || [];
  const tabs = [
    { id: "sources", label: "Sources", icon: IconWorld },
    { id: "pages", label: "Saved pages", icon: IconFileText },
    { id: "builds", label: "Builds & review", icon: IconLayersIntersect },
    { id: "corpus", label: "Stored knowledge", icon: IconDatabase },
  ];
  const titles: Record<string, [string, string]> = {
    sources: [
      "Start with the source.",
      "Choose official pages to bring into your knowledge workspace.",
    ],
    pages: [
      "See what the parser sees.",
      "Inspect saved text, plan a run, then extract candidate concepts.",
    ],
    builds: [
      "Follow every build.",
      "Progress, evidence and review history in one place.",
    ],
    corpus: [
      "Explore your evidence.",
      "Browse the exact excerpts retained in PostgreSQL.",
    ],
  };
  const anyError =
    error ||
    catalog.error?.message ||
    assets.error?.message ||
    jobs.error?.message ||
    releases.error?.message;
  return (
    <div className="studio">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">+</span>
          <div>
            SwissTIP<small>KNOWLEDGE STUDIO</small>
          </div>
        </div>
        <div className="workspace">
          <span className="workspace-dot" /> Hackathon workspace
          <Badge color="teal" variant="light" size="xs">
            LOCAL
          </Badge>
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={tab === id ? "active" : ""}
              onClick={() => {
                setTab(id);
                setError("");
              }}
            >
              <Icon size={20} />
              {label}
              {tab === id && <IconArrowRight size={16} />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <IconBook2 size={22} />
          <strong>Evidence comes first.</strong>
          <p>Keep the source, inspect the extraction, record your review.</p>
          <span>Experimental workspace</span>
        </div>
        <div className="sidebar-footer">
          Swisscom Trusted Information Platform
        </div>
      </aside>
      <main>
        <header className="topbar">
          <span>
            Workspace <span className="slash">/</span>{" "}
            {tabs.find((t) => t.id === tab)?.label}
          </span>
          <Badge variant="dot" color="teal">
            Local pilot
          </Badge>
        </header>
        <div className="content">
          <div className="page-title">
            <div>
              <div className="eyebrow">KNOWLEDGE OPERATIONS</div>
              <h1>{titles[tab][0]}</h1>
              <p>{titles[tab][1]}</p>
            </div>
            <Button
              variant="default"
              leftSection={<IconUpload size={17} />}
              onClick={() => {
                setTab("pages");
                setUploadOpen(true);
              }}
            >
              Upload a page
            </Button>
          </div>
          {anyError && (
            <Alert
              color="red"
              title="Action could not complete"
              mb="md"
              withCloseButton
              onClose={() => setError("")}
            >
              {anyError}
            </Alert>
          )}
          {notice && (
            <Alert
              color="teal"
              mb="md"
              withCloseButton
              onClose={() => setNotice("")}
            >
              {notice}
            </Alert>
          )}
          {catalog.isLoading ? (
            <Loader />
          ) : (
            <>
              {tab === "sources" && (
                <>
                  <div className="hero">
                    <div>
                      <Badge color="lime" variant="light">
                        DEMO STARTER
                      </Badge>
                      <h2>Swiss residence, from source to evidence.</h2>
                      <p>
                        Start with SEM in German and English, plus Zurich
                        EU/EFTA guidance. The saved pilot pages are ready to
                        explore without a fresh crawl.
                      </p>
                      <Button
                        color="dark"
                        rightSection={<IconArrowRight size={17} />}
                        loading={loadPilot.isPending}
                        onClick={() => loadPilot.mutate()}
                      >
                        Load saved pilot pages
                      </Button>
                    </div>
                    <div className="hero-diagram">
                      <span>
                        <IconWorld /> Official sources
                      </span>
                      <i />
                      <span>
                        <IconFileText /> Readable sections
                      </span>
                      <i />
                      <span>
                        <IconDatabase /> Traceable evidence
                      </span>
                    </div>
                  </div>
                  <div className="section-heading">
                    <div>
                      <h2>
                        Source catalog{" "}
                        <span>{catalog.data?.sources.length}</span>
                      </h2>
                      <p>A bounded starting point across Switzerland.</p>
                    </div>
                    <TextInput
                      aria-label="Search sources"
                      w={280}
                      placeholder="Search sources or languages"
                      leftSection={<IconSearch size={16} />}
                      value={search}
                      onChange={(e) => setSearch(e.currentTarget.value)}
                    />
                  </div>
                  <Paper withBorder className="table-card">
                    <Table.ScrollContainer minWidth={600}>
                      <Table verticalSpacing="md" horizontalSpacing="lg">
                        <Table.Thead>
                          <Table.Tr>
                            <Table.Th w={44} />
                            <Table.Th>Source</Table.Th>
                            <Table.Th>Language</Table.Th>
                            <Table.Th>Availability</Table.Th>
                          </Table.Tr>
                        </Table.Thead>
                        <Table.Tbody>
                          {visibleSources.map((source) => (
                            <Table.Tr key={source.source_id}>
                              <Table.Td>
                                <Checkbox
                                  aria-label={`Select ${source.source_id}`}
                                  checked={
                                    sources?.includes(source.source_id) || false
                                  }
                                  disabled={source.scan_status !== "ready"}
                                  onChange={() =>
                                    toggle(
                                      source.source_id,
                                      sources || [],
                                      setSources,
                                    )
                                  }
                                />
                              </Table.Td>
                              <Table.Td>
                                <Text fw={550} size="sm">
                                  {source.title}
                                </Text>
                                <a
                                  href={source.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="source-url"
                                >
                                  {new URL(source.url).hostname} <span>↗</span>
                                </a>
                              </Table.Td>
                              <Table.Td>
                                <Badge variant="light" color="gray">
                                  {source.language.toUpperCase()}
                                </Badge>
                              </Table.Td>
                              <Table.Td>
                                <Badge
                                  variant="dot"
                                  color={
                                    source.scan_status === "ready"
                                      ? "teal"
                                      : "orange"
                                  }
                                >
                                  {source.scan_status === "ready"
                                    ? "Ready to crawl"
                                    : "Access review needed"}
                                </Badge>
                              </Table.Td>
                            </Table.Tr>
                          ))}
                        </Table.Tbody>
                      </Table>
                    </Table.ScrollContainer>
                  </Paper>
                  <div className="actionbar">
                    <Text size="sm">
                      <b>{sources?.length || 0}</b> sources selected{" "}
                      <span className="muted">/ maximum 10 per run</span>
                    </Text>
                    <Button
                      disabled={!sources?.length || sources.length > 10}
                      rightSection={<IconArrowRight size={16} />}
                      onClick={() =>
                        setConfirmation({
                          kind: "crawl",
                          source_ids: sources!,
                          asset_ids: [],
                          profile: profile!,
                        })
                      }
                    >
                      Review crawl
                    </Button>
                  </div>
                </>
              )}
              {tab === "pages" && (
                <>
                  <div className="workflow">
                    <span className="current">01 &nbsp; Inspect pages</span>
                    <IconArrowRight size={16} />
                    <span>02 &nbsp; Preview extraction plan</span>
                    <IconArrowRight size={16} />
                    <span>03 &nbsp; Extract & review</span>
                  </div>
                  <Paper withBorder p="lg" mb="lg">
                    <Group justify="space-between">
                      <div>
                        <Title order={4}>Extraction model</Title>
                        <Text size="sm" c="dimmed">
                          {extractionLabel(catalog.data?.extraction_profile)}.
                          Model outputs remain experimental.
                        </Text>
                      </div>
                      <Select
                        aria-label="Extraction model"
                        w={320}
                        value={profile}
                        onChange={setProfile}
                        allowDeselect={false}
                        data={
                          catalog.data?.profiles.map((p) => ({
                            value: p.name,
                            label: `${p.name}${p.credential_ready ? "" : " (key missing)"}`,
                          })) || []
                        }
                      />
                    </Group>
                    <Text size="xs" c="dimmed" mt="sm">
                      {
                        catalog.data?.profiles.find((p) => p.name === profile)
                          ?.model
                      }{" "}
                      · Up to {catalog.data?.max_requests} model attempts per
                      extraction run · No automatic provider retries
                    </Text>
                  </Paper>
                  <Select
                    label="Corpus"
                    placeholder="All saved pages"
                    clearable
                    value={corpusId}
                    onChange={(value) => {
                      setCorpusId(value);
                      setSelectedAssets([]);
                    }}
                    data={[
                      ...(corpora.data || []).map((corpus) => ({
                        value: corpus.corpus_id,
                        label: `${corpus.title} (${corpus.corpus_id})`,
                      })),
                      { value: "__legacy__", label: "Earlier attempts / ungrouped pages" },
                    ]}
                  />
                  {corpusId && corpusId !== "__legacy__" && (
                    <Text size="sm" c="dimmed">
                      {assets.data?.length || 0} saved files in this corpus. Archive-only
                      files are retained but cannot be selected for extraction.
                    </Text>
                  )}
                  {!assets.data?.length ? (
                    <Empty
                      title="Your saved pages will appear here."
                      text="Load the pilot archive, upload a downloaded page, or crawl selected sources."
                      action={
                        <Button
                          onClick={() => loadPilot.mutate()}
                          loading={loadPilot.isPending}
                        >
                          Load saved pilot pages
                        </Button>
                      }
                    />
                  ) : (
                    <div className="page-grid">
                      {assets.data.map((asset) => (
                        <Paper
                          withBorder
                          p="lg"
                          key={asset.asset_id}
                          className="page-card"
                        >
                          <Group justify="space-between">
                            <div className="file-icon">
                              <IconFileText size={23} />
                            </div>
                            <Checkbox
                              aria-label={`Select page ${asset.source_id}`}
                              disabled={!asset.processing_eligible}
                              checked={selectedAssets.includes(asset.asset_id)}
                              onChange={() =>
                                toggle(
                                  asset.asset_id,
                                  selectedAssets,
                                  setSelectedAssets,
                                )
                              }
                            />
                          </Group>
                          <h3>{asset.title || asset.source_id}</h3>
                          <Badge variant="light" style={{ maxWidth: "100%" }}>
                            {asset.corpus_id || "Earlier / ungrouped"}
                          </Badge>
                          <Text size="xs" c="dimmed" mt="xs">
                            {asset.filename.split(".").pop()?.toUpperCase()}
                            {!asset.processing_eligible && " - Archive only"}
                          </Text>
                          {!asset.processing_eligible && (
                            <Text size="xs" c="orange">
                              {asset.processing_reason === "javascript_application_shell"
                                ? "Application shell; use the resolved document."
                                : asset.processing_reason === "archived_format_without_text_extractor"
                                  ? "This file format has no text extractor yet."
                                  : asset.processing_reason}
                            </Text>
                          )}
                          <Text size="xs" c="dimmed">
                            {(asset.size / 1024).toFixed(1)} KB ·{" "}
                            {formatDate(asset.created_at)}
                          </Text>
                          <Text size="xs" c="dimmed" mt="xs" lineClamp={1}>
                            {asset.origin}
                          </Text>
                          <Button
                            variant="light"
                            fullWidth
                            mt="lg"
                            onClick={() => setPreviewAsset(asset)}
                            disabled={!asset.processing_eligible}
                          >
                            Inspect parsed text
                          </Button>
                        </Paper>
                      ))}
                    </div>
                  )}
                  <div className="actionbar">
                    <Text size="sm">
                      <b>{selectedAssets.length}</b> pages selected{" "}
                      <span className="muted">
                        / maximum {catalog.data?.max_pages}
                      </span>
                    </Text>
                    <Group>
                      <Button
                        variant="default"
                        disabled={
                          !selectedAssets.length ||
                          selectedAssets.length >
                            (catalog.data?.max_pages || 10)
                        }
                        loading={create.isPending}
                        onClick={() => begin("plan")}
                      >
                        Preview extraction plan
                      </Button>
                      <Button
                        leftSection={<IconPlayerPlay size={16} />}
                        disabled={
                          !selectedAssets.length ||
                          selectedAssets.length >
                            (catalog.data?.max_pages || 10)
                        }
                        onClick={() => begin("extract")}
                      >
                        Run extraction
                      </Button>
                    </Group>
                  </div>
                </>
              )}
              {tab === "builds" && (
                <div className="build-layout">
                  <Paper withBorder p="md">
                    <Text className="eyebrow" mb="md">
                      RECENT BUILDS
                    </Text>
                    {!jobs.data?.length && (
                      <Text size="sm" c="dimmed">
                        Start with a saved page to create your first build.
                      </Text>
                    )}
                    {jobs.data?.map((item) => (
                      <button
                        key={item.job_id}
                        className={`job-item ${jobId === item.job_id ? "selected" : ""}`}
                        onClick={() => setJobId(item.job_id)}
                      >
                        <Group justify="space-between">
                          <strong>
                            {item.kind === "plan"
                              ? "Extraction plan"
                              : item.kind === "crawl"
                                ? "Source crawl"
                                : "Concept extraction"}
                          </strong>
                          <Badge size="xs" color={statusColor(item.status)}>
                            {item.status.replaceAll("_", " ")}
                          </Badge>
                        </Group>
                        <small>{formatDate(item.created_at)}</small>
                        {Array.isArray(item.request.corpus_ids) && item.request.corpus_ids.length > 0 && (
                          <Text size="xs" c="dimmed">{item.request.corpus_ids.join(", ")}</Text>
                        )}
                      </button>
                    ))}
                  </Paper>
                  <div>
                    {jobId && job.data ? (
                      <JobView
                        key={job.data.job_id}
                        job={job.data}
                        onCancel={async () => {
                          try {
                            await unwrap(
                              api.cancelJob({
                                path: { identifier: jobId },
                                body: {},
                              }),
                            );
                            await cache.invalidateQueries({
                              queryKey: ["job", jobId],
                            });
                          } catch (e) {
                            setError((e as Error).message);
                          }
                        }}
                      />
                    ) : job.error ? (
                      <Alert color="red">{job.error.message}</Alert>
                    ) : (
                      <Empty
                        title="A clear record of every run."
                        text="Select a build to inspect its progress, result and candidate evidence."
                      />
                    )}
                  </div>
                </div>
              )}
              {tab === "corpus" && (
                <>
                  <Paper p="lg" withBorder mb="lg">
                    <Group justify="space-between">
                      <div>
                        <Title order={4}>Retained releases</Title>
                        <Text size="sm" c="dimmed">
                          Original excerpts and citations. Experimental releases
                          contain no published facts.
                        </Text>
                      </div>
                      <Select
                        aria-label="Stored release"
                        w={380}
                        value={releaseId}
                        onChange={setReleaseId}
                        allowDeselect={false}
                        data={
                          releases.data?.map((r) => ({
                            value: r.release_id,
                            label: `${r.release_id.startsWith("zh") ? "Zurich EU/EFTA" : "SEM residence"} · ${r.evidence_count} excerpts`,
                          })) || []
                        }
                      />
                    </Group>
                  </Paper>
                  {evidence.error && (
                    <Alert color="red">{evidence.error.message}</Alert>
                  )}
                  <div className="evidence-grid">
                    {evidence.data?.map((e) => (
                      <Paper p="lg" withBorder key={e.evidence_id}>
                        <Group justify="space-between">
                          <Text size="sm" fw={600}>
                            {e.evidence_id}
                          </Text>
                          <Badge color="gray" variant="light">
                            {e.language}
                          </Badge>
                        </Group>
                        <blockquote>{e.original_excerpt}</blockquote>
                        {/^https?:\/\//.test(e.citation_url) && (
                          <a
                            className="citation"
                            href={e.citation_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {e.source_id} ↗
                          </a>
                        )}
                      </Paper>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
          <footer>
            Experimental knowledge workspace{" "}
            <span>
              Source preservation · Explicit review · Traceable builds
            </span>
          </footer>
        </div>
      </main>
      <Modal
        opened={!!previewAsset}
        onClose={() => setPreviewAsset(null)}
        title="Parsed source preview"
        size="xl"
      >
        <Text size="sm" c="dimmed" mb="md">
          The extraction profile has filtered this source. Review the text
          before extracting concepts.
        </Text>
        {preview.isLoading ? (
          <Loader />
        ) : preview.error ? (
          <Alert color="red">{preview.error.message}</Alert>
        ) : (
          <>
            <Group justify="space-between" mb="md">
              <Title order={3}>{preview.data?.title}</Title>
              <Badge>
                {preview.data?.sections.length} sections ·{" "}
                {preview.data?.characters} characters
              </Badge>
            </Group>
            <Text size="xs" c="dimmed" mb="md">
              {extractionLabel(preview.data?.extraction_profile)}.{" "}
              {preview.data?.excluded_sections} sections excluded by the
              extraction profile.
            </Text>
            <ScrollArea h={500}>
              {preview.data?.sections.map((s) => (
                <div className="preview-section" key={s.section_id}>
                  <Text size="xs" c="teal" fw={600}>
                    {s.section_id}
                  </Text>
                  <p>{s.text}</p>
                </div>
              ))}
            </ScrollArea>
          </>
        )}
      </Modal>
      <Modal
        opened={!!confirmation}
        onClose={() => setConfirmation(null)}
        title={
          confirmation?.kind === "crawl"
            ? "Start a bounded crawl"
            : "Start model extraction"
        }
      >
        <Stack>
          <Text>
            {confirmation?.kind === "crawl"
              ? `Fetch pages from ${confirmation.source_ids?.length} selected official sources using the smoke crawl budget. Each run keeps a new snapshot.`
              : `Send ${selectedAssets.length} saved pages to ${catalog.data?.profiles.find((p) => p.name === profile)?.model} using ${extractionLabel(catalog.data?.extraction_profile)}. The configured ceiling is ${catalog.data?.max_requests} model attempts, including extraction and review.`}
          </Text>
          <Text size="sm" c="dimmed">
            {confirmation?.kind === "crawl"
              ? "Requests follow the existing source allowlists and robots rules."
              : "Inspect parsed text and Preview extraction plan first to check the source and planned requests. Provider availability and output quality may vary."}
          </Text>
          <Text size="sm">
            Results remain drafts. Your existing stored releases stay available.
          </Text>
          {error && <Alert color="red">{error}</Alert>}
          <Button
            loading={create.isPending}
            onClick={() => confirmation && create.mutate(confirmation)}
          >
            Confirm {confirmation?.kind === "crawl" ? "crawl" : "extraction"}
          </Button>
        </Stack>
      </Modal>
      <Modal
        opened={uploadOpen}
        onClose={() => setUploadOpen(false)}
        title="Upload a downloaded page"
      >
        <Stack>
          <Text size="sm">
            Choose a UTF-8 HTML, text or Markdown file, up to 2 MB. The source
            association is your declaration.
          </Text>
          <Select
            label="Source"
            searchable
            value={uploadSource}
            onChange={setUploadSource}
            data={
              catalog.data?.sources.map((s) => ({
                value: s.source_id,
                label: s.title,
              })) || []
            }
          />
          <FileButton onChange={upload} accept=".html,.htm,.txt,.md,.markdown">
            {(props) => (
              <Button {...props} disabled={!uploadSource}>
                Choose file
              </Button>
            )}
          </FileButton>
          {error && <Alert color="red">{error}</Alert>}
        </Stack>
      </Modal>
    </div>
  );
}

function Empty({
  title,
  text,
  action,
}: {
  title: string;
  text: string;
  action?: React.ReactNode;
}) {
  return (
    <Paper withBorder p="xl" className="empty">
      <IconLayersIntersect size={35} stroke={1.4} />
      <h3>{title}</h3>
      <p>{text}</p>
      {action}
    </Paper>
  );
}

function JobView({ job, onCancel }: { job: Job; onCancel: () => void }) {
  const [reviewer, setReviewer] = useState("");
  const [notes, setNotes] = useState("");
  const [reviewTarget, setReviewTarget] = useState<{
    candidate: Candidate;
    decision: "needs_changes" | "reject";
    resultSha256: string;
  } | null>(null);
  const [comment, setComment] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const cache = useQueryClient();
  const reviews = useQuery({
    queryKey: ["reviews", job.job_id],
    queryFn: () => unwrap(api.getReviews({ path: { identifier: job.job_id } })),
  });
  const mutation = useMutation({
    mutationFn: (body: ReviewRequest) =>
      unwrap(api.addReview({ path: { identifier: job.job_id }, body })),
    onMutate: () => {
      setMessage("");
      setError("");
    },
    onSuccess: (data, body) => {
      setMessage(data.message);
      setError("");
      setReviewTarget(null);
      setComment("");
      if (body.decision === "accept_draft") setNotes("");
      void cache.invalidateQueries({ queryKey: ["reviews", job.job_id] });
    },
    onError: (e: Error) => setError(e.message),
  });
  const reports = (job.result?.reports || []) as Report[];
  const candidates = reports.flatMap((r) => r.candidates || []);
  const extractionProfile =
    typeof job.result?.prompt_profile === "string"
      ? job.result.prompt_profile
      : reports.find((report) => report.prompt_profile)?.prompt_profile;
  return (
    <Stack>
      <Paper withBorder p="lg">
        <Group justify="space-between">
          <div>
            <Title order={3}>
              {job.kind === "plan"
                ? "Extraction plan"
                : job.kind === "crawl"
                  ? "Source crawl"
                  : "Concept extraction"}
            </Title>
            <Text size="xs" c="dimmed">
              {formatDate(job.created_at)}
            </Text>
            {extractionProfile && (
              <Text size="sm" c="dimmed" mt="xs">
                {extractionLabel(extractionProfile)}
              </Text>
            )}
          </div>
          <Badge color={statusColor(job.status)}>
            {job.status.replaceAll("_", " ")}
          </Badge>
        </Group>
        {["queued", "running"].includes(job.status) && (
          <Button
            mt="md"
            size="xs"
            variant="light"
            color="red"
            disabled={job.cancel_requested}
            onClick={onCancel}
          >
            {job.cancel_requested ? "Stopping..." : "Cancel run"}
          </Button>
        )}
        {job.error && (
          <Alert color="red" mt="md">
            {job.error}
          </Alert>
        )}
        {job.status === "queued" && (
          <Text size="sm" mt="md">
            Waiting for the worker. Jobs run one at a time.
          </Text>
        )}
        {job.status === "needs_attention" && (
          <Alert color="orange" mt="md">
            Inspect the warnings and extraction report. Process completion does
            not mean usable extraction.
          </Alert>
        )}
      </Paper>
      <Paper withBorder p="lg">
        <Group justify="space-between" mb="md">
          <Title order={4}>Progress</Title>
          <Text size="xs" c="dimmed">
            Updates automatically
          </Text>
        </Group>
        <pre className="log">{job.log || "No progress messages yet."}</pre>
      </Paper>
      {job.result && (
        <Paper withBorder p="lg">
          <Group justify="space-between" mb="md">
            <Title order={4}>
              {job.kind === "plan" ? "Plan details" : "Build result"}
            </Title>
            <Button
              variant="default"
              size="xs"
              onClick={() =>
                download(job.result, `${job.kind}-${job.job_id}.json`)
              }
            >
              Download report
            </Button>
          </Group>
          {job.kind === "plan" && (
            <Alert color="teal" mb="md">
              Planned request ceiling:{" "}
              {String(job.result.planned_request_ceiling)}. Model requests sent:{" "}
              {String(job.result.model_requests_sent)}.
            </Alert>
          )}
          {job.kind === "plan" && <PlanInventory result={job.result} />}
          {job.kind === "extract" && (
            <Text size="sm" mb="md">
              {candidates.length} candidate concepts retained. Review source
              support and completeness before accepting a draft.
            </Text>
          )}
          <details>
            <summary>Inspect full report</summary>
            <pre className="json-view">
              {JSON.stringify(job.result, null, 2)}
            </pre>
          </details>
        </Paper>
      )}
      {candidates.length > 0 && (
        <Paper withBorder p="lg">
          <Title order={4} mb="md">
            Candidate review
          </Title>
          <Group grow mb="md">
            <TextInput
              label="Reviewer name"
              value={reviewer}
              maxLength={100}
              disabled={mutation.isPending}
              onChange={(e) => setReviewer(e.currentTarget.value)}
            />
            <Textarea
              label="Acceptance note (optional)"
              value={notes}
              maxLength={4000}
              disabled={mutation.isPending}
              onChange={(e) => setNotes(e.currentTarget.value)}
            />
          </Group>
          {candidates.map((c) => (
            <div className="candidate" key={c.candidate_id}>
              <h3>{c.preferred_label}</h3>
              <Text size="sm">{c.description}</Text>
              <div className="candidate-evidence">
                <div>
                  {c.structured_claims?.length ? (
                    <>
                      <Text fw={600} size="sm">
                        Proposed claims
                      </Text>
                      {c.structured_claims.map((claim) => (
                        <div key={claim.claim_id}>
                          <Text size="sm" mt="sm">
                            {claim.statement}
                          </Text>
                          {!!claim.conditions?.length && (
                            <ul>
                              {claim.conditions.map((condition, index) => (
                                <li key={index}>
                                  <Text size="xs">{condition.text}</Text>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </>
                  ) : (
                    <>
                      <Text fw={600} size="sm">
                        Concept scope
                      </Text>
                      <Text size="sm" mt="sm">
                        {c.scope || "No scope supplied in this report."}
                      </Text>
                      {!!c.user_questions?.length && (
                        <>
                          <Text fw={600} size="sm" mt="md">
                            Questions this concept answers
                          </Text>
                          <ul>
                            {c.user_questions.map((question, index) => (
                              <li key={index}>
                                <Text size="sm">{question}</Text>
                              </li>
                            ))}
                          </ul>
                        </>
                      )}
                    </>
                  )}
                </div>
                <div>
                  <Text fw={600} size="sm">
                    Source evidence
                  </Text>
                  {(c.evidence || []).map((span, index) => (
                    <blockquote key={index}>
                      {span.quote || span.excerpt || span.text}
                      <Text size="xs" c="dimmed" mt="sm">
                        {span.section_id}
                      </Text>
                    </blockquote>
                  ))}
                </div>
              </div>
              <Group>
                {(["accept_draft", "needs_changes", "reject"] as const).map(
                  (decision) => (
                    <Button
                      key={decision}
                      size="xs"
                      variant="light"
                      color={
                        decision === "reject"
                          ? "red"
                          : decision === "needs_changes"
                            ? "orange"
                            : "teal"
                      }
                      disabled={
                        mutation.isPending ||
                        !job.result_sha256 ||
                        (decision === "accept_draft" && !reviewer.trim())
                      }
                      loading={
                        mutation.isPending &&
                        mutation.variables?.candidate_id === c.candidate_id &&
                        mutation.variables.decision === decision
                      }
                      onClick={() => {
                        if (decision === "accept_draft") {
                          mutation.mutate({
                            candidate_id: c.candidate_id,
                            decision,
                            reviewer: reviewer.trim(),
                            notes,
                            result_sha256: job.result_sha256!,
                          });
                        } else {
                          setReviewTarget({
                            candidate: c,
                            decision,
                            resultSha256: job.result_sha256!,
                          });
                          setComment("");
                          setMessage("");
                          setError("");
                        }
                      }}
                    >
                      {decision.replaceAll("_", " ")}
                    </Button>
                  ),
                )}
              </Group>
              {mutation.variables?.candidate_id === c.candidate_id &&
                message && (
                  <Alert color="teal" mt="sm" role="status">
                    {message}
                  </Alert>
                )}
              {mutation.variables?.candidate_id === c.candidate_id &&
                error &&
                !reviewTarget && (
                  <Alert color="red" mt="sm">
                    {error}
                  </Alert>
                )}
            </div>
          ))}
          <Text size="xs" c="dimmed" mt="lg">
            Draft decisions are recorded against this exact result revision.
            They do not publish knowledge.
          </Text>
          <details>
            <summary>Review history ({reviews.data?.length || 0})</summary>
            <pre className="json-view">
              {JSON.stringify(reviews.data || [], null, 2)}
            </pre>
          </details>
        </Paper>
      )}
      <Modal
        opened={reviewTarget !== null}
        onClose={() => {
          if (!mutation.isPending) {
            setReviewTarget(null);
            setComment("");
            setError("");
          }
        }}
        title={
          reviewTarget?.decision === "reject" ? "Reject draft" : "Needs changes"
        }
        centered
        scrollAreaComponent={ScrollArea.Autosize}
        closeOnClickOutside={!mutation.isPending}
        closeOnEscape={!mutation.isPending}
        withCloseButton={!mutation.isPending}
      >
        {reviewTarget && (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (mutation.isPending || !reviewer.trim() || !comment.trim())
                return;
              mutation.mutate({
                candidate_id: reviewTarget.candidate.candidate_id,
                decision: reviewTarget.decision,
                reviewer: reviewer.trim(),
                notes: comment.trim(),
                result_sha256: reviewTarget.resultSha256,
              });
            }}
          >
            <Stack>
              <Text fw={600}>{reviewTarget.candidate.preferred_label}</Text>
              <TextInput
                label="Reviewer name"
                value={reviewer}
                onChange={(event) => setReviewer(event.currentTarget.value)}
                maxLength={100}
                required
                disabled={mutation.isPending}
              />
              <Textarea
                label="Review comment"
                description={
                  reviewTarget.decision === "reject"
                    ? "Explain why this draft should be rejected."
                    : "Describe what needs to change in this draft."
                }
                value={comment}
                onChange={(event) => setComment(event.currentTarget.value)}
                rows={4}
                maxLength={4000}
                required
                data-autofocus
                disabled={mutation.isPending}
              />
              {error && <Alert color="red">{error}</Alert>}
              <Group justify="flex-end">
                <Button
                  variant="default"
                  disabled={mutation.isPending}
                  onClick={() => {
                    setReviewTarget(null);
                    setComment("");
                    setError("");
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  color={reviewTarget.decision === "reject" ? "red" : "orange"}
                  loading={mutation.isPending}
                  disabled={!reviewer.trim() || !comment.trim()}
                >
                  Save review
                </Button>
              </Group>
            </Stack>
          </form>
        )}
      </Modal>
    </Stack>
  );
}

function PlanInventory({ result }: { result: Record<string, unknown> }) {
  type Block = {
    section_id: string;
    status: string;
    reason: string;
    evidence_text: string;
  };
  const pages = (result.pages || []) as {
    source: string;
    source_inventory?: Block[];
    planned_request_ceiling?: number;
  }[];
  if (result.prompt_profile === "concept_extraction_v3") {
    return (
      <Stack mb="md">
        <Text size="sm">
          V3 extracts concepts with source evidence, then reviews each
          extraction. Inspect parsed text in Saved pages to review the source.
        </Text>
        {pages.map((page, index) => (
          <Paper withBorder p="sm" key={page.source}>
            <Text fw={600} size="sm">
              Page {index + 1}: {page.planned_request_ceiling} planned model
              requests
            </Text>
            <Text size="xs" c="dimmed" style={{ overflowWrap: "anywhere" }}>
              {page.source.split(/[\\/]/).pop()}
            </Text>
          </Paper>
        ))}
      </Stack>
    );
  }
  return (
    <Stack>
      {pages.map((page, index) => (
        <details key={page.source} open={index === 0}>
          <summary>
            Page {index + 1}:{" "}
            {
              (page.source_inventory || []).filter(
                (b) => b.status !== "excluded_policy",
              ).length
            }{" "}
            content blocks
          </summary>
          {(page.source_inventory || [])
            .filter((b) => b.status !== "excluded_policy")
            .map((block) => (
              <div className="preview-section" key={block.section_id}>
                <Group justify="space-between">
                  <Text size="xs" fw={600}>
                    {block.section_id}
                  </Text>
                  <Badge color={block.status === "pending" ? "teal" : "orange"}>
                    {block.status === "pending"
                      ? "Eligible"
                      : block.status.replaceAll("_", " ")}
                  </Badge>
                </Group>
                <p>{block.evidence_text}</p>
                {block.status !== "pending" && (
                  <Text size="xs" c="orange">
                    {block.reason}
                  </Text>
                )}
              </div>
            ))}
          <Text size="xs" c="dimmed" mt="sm">
            {
              (page.source_inventory || []).filter(
                (b) => b.status === "excluded_policy",
              ).length
            }{" "}
            navigation/heading blocks excluded. The full report retains every
            block.
          </Text>
        </details>
      ))}
    </Stack>
  );
}
