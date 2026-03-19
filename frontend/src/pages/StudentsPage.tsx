import { useCallback, useEffect, useState } from "react";
import type {
  StudentListResponse,
  StudentResponse,
  StudentCreate,
  StudentUpdate,
  TestResponse,
  TestSessionResponse,
  LookupRegionResponse,
  LookupZoneResponse,
  SmenaResponse,
} from "../interfaces";
import {
  getStudentsApi,
  getStudentApi,
  createStudentApi,
  updateStudentApi,
  deleteStudentApi,
  fetchGtspImageApi,
  getTestsLookupApi,
  getTestSessionsApi,
  getRegionsListApi,
  getZonesByRegionApi,
  getSmenasLookupApi,
} from "../api";
import PageLoader from "../components/PageLoader";
import Pagination from "../components/Pagination";
import { extractErrorMessage } from "../utils/errorMessage";

const emptyForm: Record<string, any> = {
  session_smena_id: 0,
  zone_id: 0,
  last_name: "",
  first_name: "",
  middle_name: "",
  imei: "",
  gr_n: 0,
  sp_n: 0,
  s_code: 0,
  e_date: new Date().toISOString().slice(0, 16),
  subject_id: 0,
  subject_name: "",
  lang_id: 0,
  level_id: 0,
};

export default function StudentsPage() {
  const [data, setData] = useState<StudentListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [error, setError] = useState("");

  // Filters
  const [filterTestId, setFilterTestId] = useState<string>("");
  const [filterRegionId, setFilterRegionId] = useState<string>("");
  const [filterSmenaId, setFilterSmenaId] = useState<string>("");
  const [filterGrN, setFilterGrN] = useState<string>("");
  const [filterDateFrom, setFilterDateFrom] = useState<string>("");
  const [filterDateTo, setFilterDateTo] = useState<string>("");
  const [filterEntered, setFilterEntered] = useState<string>("");
  const [filterCheating, setFilterCheating] = useState<string>("");
  const [filterBlacklist, setFilterBlacklist] = useState<string>("");
  const [filterFace, setFilterFace] = useState<string>("");
  const [filterImage, setFilterImage] = useState<string>("");
  const [filterReady, setFilterReady] = useState<string>("");
  const [showFilters, setShowFilters] = useState(false);

  // Lookup data
  const [tests, setTests] = useState<TestResponse[]>([]);
  const [regions, setRegions] = useState<LookupRegionResponse[]>([]);
  const [smenas, setSmenas] = useState<SmenaResponse[]>([]);

  // Detail panel
  const [selected, setSelected] = useState<StudentResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [fetchingGtsp, setFetchingGtsp] = useState(false);

  // Modal
  const [showModal, setShowModal] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<Record<string, any>>({ ...emptyForm });
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  // Modal: region → zone cascade
  const [modalRegionId, setModalRegionId] = useState<string>("");
  const [modalZones, setModalZones] = useState<LookupZoneResponse[]>([]);
  const [modalZonesLoading, setModalZonesLoading] = useState(false);

  // Modal: test session → session smena cascade
  const [testSessions, setTestSessions] = useState<TestSessionResponse[]>([]);
  const [modalTestSessionId, setModalTestSessionId] = useState<string>("");

  // Delete confirmation modal
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; name: string } | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Load lookup data
  useEffect(() => {
    getTestsLookupApi().then(setTests).catch(() => {});
    getRegionsListApi().then(setRegions).catch(() => {});
    getSmenasLookupApi().then(setSmenas).catch(() => {});
    getTestSessionsApi({ per_page: 100 }).then((r) => setTestSessions(r.items)).catch(() => {});
  }, []);

  // Load zones when modal region changes
  useEffect(() => {
    if (!modalRegionId) {
      setModalZones([]);
      return;
    }
    setModalZonesLoading(true);
    getZonesByRegionApi(Number(modalRegionId))
      .then(setModalZones)
      .catch(() => setModalZones([]))
      .finally(() => setModalZonesLoading(false));
  }, [modalRegionId]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number | boolean> = { page, per_page: 20 };
      if (search) params.search = search;
      if (filterTestId) params.test_id = Number(filterTestId);
      if (filterRegionId) params.region_id = Number(filterRegionId);
      if (filterSmenaId) params.smena_id = Number(filterSmenaId);
      if (filterGrN) params.gr_n = Number(filterGrN);
      if (filterDateFrom) params.e_date_from = filterDateFrom;
      if (filterDateTo) params.e_date_to = filterDateTo;
      if (filterEntered === "true") params.is_entered = true;
      if (filterEntered === "false") params.is_entered = false;
      if (filterCheating === "true") params.is_cheating = true;
      if (filterCheating === "false") params.is_cheating = false;
      if (filterBlacklist === "true") params.is_blacklist = true;
      if (filterBlacklist === "false") params.is_blacklist = false;
      if (filterFace === "true") params.is_face = true;
      if (filterFace === "false") params.is_face = false;
      if (filterImage === "true") params.is_image = true;
      if (filterImage === "false") params.is_image = false;
      if (filterReady === "true") params.is_ready = true;
      if (filterReady === "false") params.is_ready = false;
      const result = await getStudentsApi(params);
      setData(result);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [
    page, search, filterTestId, filterRegionId, filterSmenaId, filterGrN,
    filterDateFrom, filterDateTo, filterEntered, filterCheating,
    filterBlacklist, filterFace, filterImage, filterReady,
  ]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSearch = () => { setPage(1); setSearch(searchInput); };

  const resetFilters = () => {
    setSearchInput(""); setSearch(""); setFilterTestId(""); setFilterRegionId("");
    setFilterSmenaId(""); setFilterGrN(""); setFilterDateFrom(""); setFilterDateTo("");
    setFilterEntered(""); setFilterCheating(""); setFilterBlacklist("");
    setFilterFace(""); setFilterImage(""); setFilterReady(""); setPage(1);
  };

  const hasFilters =
    search || filterTestId || filterRegionId || filterSmenaId || filterGrN ||
    filterDateFrom || filterDateTo || filterEntered || filterCheating ||
    filterBlacklist || filterFace || filterImage || filterReady;

  const activeFilterCount = [
    filterTestId, filterRegionId, filterSmenaId, filterGrN,
    filterDateFrom, filterDateTo, filterEntered, filterCheating,
    filterBlacklist, filterFace, filterImage, filterReady,
  ].filter(Boolean).length;

  const handleRowClick = async (s: StudentResponse) => {
    if (selected?.id === s.id) { setSelected(null); return; }
    setSelected(s);
    setDetailLoading(true);
    try { setSelected(await getStudentApi(s.id)); } catch { /* keep list version */ }
    finally { setDetailLoading(false); }
  };

  const openCreate = () => {
    setEditId(null);
    setForm({ ...emptyForm });
    setModalRegionId("");
    setModalZones([]);
    setModalTestSessionId("");
    setFormError("");
    setShowModal(true);
  };

  const openEdit = async (s: StudentResponse) => {
    setEditId(s.id);
    // Fetch full detail to get ps_data
    let full = s;
    try { full = await getStudentApi(s.id); } catch { /* use what we have */ }
    setForm({
      session_smena_id: full.session_smena_id,
      zone_id: full.zone_id,
      last_name: full.last_name,
      first_name: full.first_name,
      middle_name: full.middle_name || "",
      imei: full.imei || "",
      gr_n: full.gr_n,
      sp_n: full.sp_n,
      s_code: full.s_code,
      e_date: full.e_date ? full.e_date.slice(0, 16) : "",
      subject_id: full.subject_id,
      subject_name: full.subject_name || "",
      lang_id: full.lang_id,
      level_id: full.level_id,
      is_ready: full.is_ready,
      is_face: full.is_face,
      is_image: full.is_image,
      is_cheating: full.is_cheating,
      is_blacklist: full.is_blacklist,
      is_entered: full.is_entered,
      // ps_data fields
      ps_ser: full.ps_data?.ps_ser || "",
      ps_num: full.ps_data?.ps_num || "",
      ps_phone: full.ps_data?.phone || "",
      ps_img: full.ps_data?.ps_img || "",
      ps_embedding: full.ps_data?.embedding || "",
    });
    // Find region for this zone to prefill cascade select
    const matchedRegion = regions.find((r) => r.name === full.region_name);
    if (matchedRegion) {
      setModalRegionId(String(matchedRegion.id));
    } else {
      setModalRegionId("");
    }
    // Find test session for this session_smena_id
    const matchedSession = testSessions.find((ts) =>
      ts.smenas.some((sm) => sm.id === full.session_smena_id)
    );
    setModalTestSessionId(matchedSession ? String(matchedSession.id) : "");
    setFormError("");
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.last_name || !form.first_name) {
      setFormError("Familiya va ism majburiy");
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      if (editId) {
        const updateData: StudentUpdate = {
          session_smena_id: form.session_smena_id,
          zone_id: form.zone_id,
          last_name: form.last_name,
          first_name: form.first_name,
          middle_name: form.middle_name || null,
          imei: form.imei || null,
          gr_n: form.gr_n,
          sp_n: form.sp_n,
          s_code: form.s_code,
          e_date: form.e_date,
          subject_id: form.subject_id,
          subject_name: form.subject_name || null,
          lang_id: form.lang_id,
          level_id: form.level_id,
          is_ready: form.is_ready,
          is_face: form.is_face,
          is_image: form.is_image,
          is_cheating: form.is_cheating,
          is_blacklist: form.is_blacklist,
          is_entered: form.is_entered,
        };
        // Include ps_data if any field was filled
        if (form.ps_ser || form.ps_num || form.ps_phone || form.ps_img || form.ps_embedding) {
          updateData.ps_data = {
            ps_ser: form.ps_ser || null,
            ps_num: form.ps_num || null,
            phone: form.ps_phone || null,
            ps_img: form.ps_img || null,
            embedding: form.ps_embedding || null,
          };
        }
        await updateStudentApi(editId, updateData);
        if (selected?.id === editId) {
          setSelected(await getStudentApi(editId));
        }
      } else {
        const createData: StudentCreate = {
          session_smena_id: form.session_smena_id,
          zone_id: form.zone_id,
          last_name: form.last_name,
          first_name: form.first_name,
          middle_name: form.middle_name || null,
          imei: form.imei || null,
          gr_n: form.gr_n,
          sp_n: form.sp_n,
          s_code: form.s_code,
          e_date: form.e_date,
          subject_id: form.subject_id,
          subject_name: form.subject_name || null,
          lang_id: form.lang_id,
          level_id: form.level_id,
        };
        await createStudentApi(createData);
      }
      setShowModal(false);
      await fetchData();
    } catch (err: any) {
      setFormError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const confirmDelete = (id: number, name: string) => {
    setDeleteTarget({ id, name });
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await deleteStudentApi(deleteTarget.id);
      if (selected?.id === deleteTarget.id) setSelected(null);
      setDeleteTarget(null);
      await fetchData();
    } catch (err: any) {
      setError(extractErrorMessage(err));
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  };

  const setField = (key: string, value: any) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const formatDate = (d: string) => {
    try {
      return new Date(d).toLocaleDateString("uz-UZ", {
        year: "numeric", month: "2-digit", day: "2-digit",
      });
    } catch { return d || "—"; }
  };

  return (
    <div className="flex gap-0">
      {/* Main content */}
      <div className={`transition-all duration-300 ${selected ? "flex-1 min-w-0" : "w-full"}`}>
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="section-title">Studentlar</h2>
            <p className="section-subtitle">Studentlar ro'yxati va pasport ma'lumotlari</p>
          </div>
          <button onClick={openCreate} className="btn-primary flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Yangi student
          </button>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded-xl text-sm">
            {error}
            <button onClick={() => setError("")} className="ml-auto underline text-xs">Yopish</button>
          </div>
        )}

        {/* Search + Filters */}
        <div className="glass-card p-4 mb-4">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-[220px]">
              <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">Qidirish</label>
              <div className="relative">
                <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text" value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  placeholder="Familiya, ism yoki PINFL..."
                  className="input-field !py-2 !pl-9 !text-sm w-full"
                />
              </div>
            </div>
            <button onClick={handleSearch} className="btn-primary !py-2 text-sm">Qidirish</button>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`btn-secondary !py-2 text-sm flex items-center gap-1.5 ${showFilters ? "ring-2 ring-primary-300 dark:ring-primary-600" : ""}`}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
              </svg>
              Filterlar
              {activeFilterCount > 0 && (
                <span className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold bg-primary-500 text-white rounded-full">
                  {activeFilterCount}
                </span>
              )}
            </button>
            {hasFilters && <button onClick={resetFilters} className="btn-secondary !py-2 text-sm">Tozalash</button>}
            {data && (
              <span className="text-xs text-gray-400 dark:text-slate-500 ml-auto self-center">
                Jami: <span className="font-semibold text-gray-600 dark:text-slate-300">{data.total}</span> ta
              </span>
            )}
          </div>

          {showFilters && (
            <div className="mt-4 pt-4 border-t border-gray-100 dark:border-slate-700">
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                <FilterSelect label="Test" value={filterTestId} onChange={(v) => { setFilterTestId(v); setPage(1); }}
                  options={tests.map((t) => ({ value: String(t.id), label: t.name }))} />
                <FilterSelect label="Viloyat" value={filterRegionId} onChange={(v) => { setFilterRegionId(v); setPage(1); }}
                  options={regions.map((r) => ({ value: String(r.id), label: r.name }))} />
                <FilterSelect label="Smena" value={filterSmenaId} onChange={(v) => { setFilterSmenaId(v); setPage(1); }}
                  options={smenas.map((s) => ({ value: String(s.id), label: s.name }))} />
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">Guruh</label>
                  <input type="number" value={filterGrN} onChange={(e) => { setFilterGrN(e.target.value); setPage(1); }}
                    placeholder="Raqam" className="input-field !py-1.5 !text-sm w-full" />
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">Sana (dan)</label>
                  <input type="date" value={filterDateFrom} onChange={(e) => { setFilterDateFrom(e.target.value); setPage(1); }}
                    className="input-field !py-1.5 !text-sm w-full" />
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">Sana (gacha)</label>
                  <input type="date" value={filterDateTo} onChange={(e) => { setFilterDateTo(e.target.value); setPage(1); }}
                    className="input-field !py-1.5 !text-sm w-full" />
                </div>
                <FilterSelect label="Kirgan" value={filterEntered} onChange={(v) => { setFilterEntered(v); setPage(1); }}
                  options={[{ value: "true", label: "Ha" }, { value: "false", label: "Yo'q" }]} />
                <FilterSelect label="Cheating" value={filterCheating} onChange={(v) => { setFilterCheating(v); setPage(1); }}
                  options={[{ value: "true", label: "Ha" }, { value: "false", label: "Yo'q" }]} />
                <FilterSelect label="Qora ro'yxat" value={filterBlacklist} onChange={(v) => { setFilterBlacklist(v); setPage(1); }}
                  options={[{ value: "true", label: "Ha" }, { value: "false", label: "Yo'q" }]} />
                <FilterSelect label="Yuz (Face)" value={filterFace} onChange={(v) => { setFilterFace(v); setPage(1); }}
                  options={[{ value: "true", label: "Ha" }, { value: "false", label: "Yo'q" }]} />
                <FilterSelect label="Rasm (Image)" value={filterImage} onChange={(v) => { setFilterImage(v); setPage(1); }}
                  options={[{ value: "true", label: "Ha" }, { value: "false", label: "Yo'q" }]} />
                <FilterSelect label="Tayyor (Ready)" value={filterReady} onChange={(v) => { setFilterReady(v); setPage(1); }}
                  options={[{ value: "true", label: "Ha" }, { value: "false", label: "Yo'q" }]} />
              </div>
            </div>
          )}
        </div>

        {/* Table */}
        <div className="glass-card overflow-hidden">
          {loading ? (
            <PageLoader />
          ) : !data || data.items.length === 0 ? (
            <div className="text-center py-16">
              <svg className="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <p className="text-gray-400 dark:text-slate-500 text-sm">Ma'lumot topilmadi</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50/80 dark:bg-slate-800/80 border-b border-gray-200 dark:border-slate-700">
                    <TH>ID</TH>
                    <TH>Test</TH>
                    <TH>Sessiya</TH>
                    <TH>Viloyat</TH>
                    <TH>Familiya</TH>
                    <TH>Ism</TH>
                    <TH>Otasining ismi</TH>
                    <TH>PINFL</TH>
                    <TH>Sana</TH>
                    <TH>Smena</TH>
                    <TH>Guruh</TH>
                    <TH align="center">CH</TH>
                    <TH align="center">EN</TH>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((s) => (
                    <tr
                      key={s.id}
                      onClick={() => handleRowClick(s)}
                      className={`border-b border-gray-50 dark:border-slate-700/40 cursor-pointer transition-all duration-150 ${
                        selected?.id === s.id
                          ? "bg-primary-50/70 dark:bg-primary-900/15 shadow-[inset_3px_0_0_0] shadow-primary-500"
                          : "hover:bg-gray-50/70 dark:hover:bg-slate-800/40"
                      }`}
                    >
                      <TD className="text-gray-400 dark:text-slate-500 font-mono">{s.id}</TD>
                      <TD className="text-gray-600 dark:text-slate-400">{s.test_name || "—"}</TD>
                      <TD className="font-mono text-gray-500 dark:text-slate-400">{s.test_session_id ?? "—"}</TD>
                      <TD className="text-gray-600 dark:text-slate-400">{s.region_name || "—"}</TD>
                      <TD className="font-semibold text-gray-800 dark:text-slate-200">{s.last_name}</TD>
                      <TD className="font-medium text-gray-700 dark:text-slate-300">{s.first_name}</TD>
                      <TD className="text-gray-500 dark:text-slate-400">{s.middle_name || "—"}</TD>
                      <TD className="font-mono text-gray-500 dark:text-slate-400">{s.imei || "—"}</TD>
                      <TD className="text-gray-500 dark:text-slate-400 whitespace-nowrap">{formatDate(s.e_date)}</TD>
                      <TD className="text-gray-600 dark:text-slate-400">{s.smena_name || "—"}</TD>
                      <TD className="font-mono text-gray-600 dark:text-slate-400">{s.gr_n || "—"}</TD>
                      <TD align="center"><StatusDot active={s.is_cheating} color="orange" title="Cheating" /></TD>
                      <TD align="center"><StatusDot active={s.is_entered} color="green" title="Kirgan" /></TD>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {data && <Pagination page={data.page} pages={data.pages} onPageChange={setPage} />}
      </div>

      {/* ===== Detail slide-out panel ===== */}
      <div className={`detail-panel-wrapper flex-shrink-0 ${selected ? "open" : "closed"}`}>
        {selected && (
          <div className="w-[460px] animate-slide-in-right" key={selected.id}>
            <div className="glass-card overflow-hidden sticky top-4">
              {/* Header with photo */}
              <div className="relative bg-gradient-to-br from-primary-600 to-primary-700 dark:from-primary-700 dark:to-primary-800 px-6 pt-5 pb-5">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 detail-photo-animate">
                    {selected.ps_data?.ps_img ? (
                      <img
                        src={selected.ps_data.ps_img.startsWith("data:") ? selected.ps_data.ps_img : `data:image/jpeg;base64,${selected.ps_data.ps_img}`}
                        alt="Pasport rasmi"
                        className="w-20 h-24 rounded-xl object-cover border-2 border-white/30 shadow-lg"
                      />
                    ) : (
                      <div className="w-20 h-24 rounded-xl bg-white/10 border-2 border-white/20 flex items-center justify-center">
                        <svg className="w-8 h-8 text-white/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0 detail-header-text">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-primary-200">ID: {selected.id}</span>
                      <button onClick={() => setSelected(null)} className="text-primary-200 hover:text-white transition-colors p-0.5">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                    <h3 className="text-lg font-bold text-white leading-tight mt-1">
                      {selected.last_name} {selected.first_name}
                    </h3>
                    {selected.middle_name && (
                      <p className="text-sm text-primary-100 mt-0.5">{selected.middle_name}</p>
                    )}
                    {selected.subject_name && (
                      <p className="text-sm text-primary-200 mt-2 truncate" title={selected.subject_name}>{selected.subject_name}</p>
                    )}
                  </div>
                </div>
                {detailLoading && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-white/10 overflow-hidden">
                    <div className="h-full w-1/3 bg-white/50 animate-pulse rounded" />
                  </div>
                )}
              </div>

              <div className="max-h-[calc(100vh-16rem)] overflow-y-auto">
                {/* Status badges */}
                <div className="detail-section px-5 py-4 border-b border-gray-100 dark:border-slate-700">
                  <SectionLabel>Holat</SectionLabel>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    <Badge label="Qora ro'yxat" active={selected.is_blacklist} on="bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" />
                    <Badge label="Cheating" active={selected.is_cheating} on="bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400" />
                    <Badge label="Kirgan" active={selected.is_entered} on="bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" />
                    <Badge label="Tayyor" active={selected.is_ready} on="bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" />
                    <Badge label="Yuz" active={selected.is_face} on="bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400" />
                    <Badge label="Rasm" active={selected.is_image} on="bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400" />
                  </div>
                </div>

                {/* Personal */}
                <div className="detail-section px-5 py-4 border-b border-gray-100 dark:border-slate-700">
                  <SectionLabel>Shaxsiy ma'lumotlar</SectionLabel>
                  <div className="mt-2.5 space-y-2">
                    <DetailRow label="Familiya" value={selected.last_name} />
                    <DetailRow label="Ism" value={selected.first_name} />
                    <DetailRow label="Otasining ismi" value={selected.middle_name} />
                    <DetailRow label="PINFL (IMEI)" value={selected.imei} mono />
                  </div>
                </div>

                {/* Test info */}
                <div className="detail-section px-5 py-4 border-b border-gray-100 dark:border-slate-700">
                  <SectionLabel>Test ma'lumotlari</SectionLabel>
                  <div className="mt-2.5 space-y-2">
                    <DetailRow label="Test" value={selected.test_name} />
                    <DetailRow label="Sessiya ID" value={selected.test_session_id ? String(selected.test_session_id) : null} mono />
                    <DetailRow label="Smena" value={selected.smena_name} />
                    <DetailRow label="Viloyat" value={selected.region_name} />
                    <DetailRow label="Bino" value={selected.zone_name} />
                    <DetailRow label="Test sanasi" value={formatDate(selected.e_date)} />
                    <DetailRow label="Guruh / Joy" value={`${selected.gr_n || "—"} / ${selected.sp_n || "—"}`} mono />
                    <DetailRow label="S-kod" value={selected.s_code ? String(selected.s_code) : null} mono />
                    <DetailRow label="Fan" value={selected.subject_name} />
                    {selected.lang_id > 0 && (
                      <DetailRow label="Til / Daraja" value={`${selected.lang_id} / ${selected.level_id}`} mono />
                    )}
                  </div>
                </div>

                {/* Passport data */}
                <div className="detail-section px-5 py-4 border-b border-gray-100 dark:border-slate-700">
                  <SectionLabel>Pasport ma'lumotlari</SectionLabel>
                  {selected.ps_data ? (
                    <div className="mt-2.5 space-y-2">
                      <DetailRow label="Seriya" value={selected.ps_data.ps_ser} mono bold />
                      <DetailRow label="Raqam" value={selected.ps_data.ps_num} mono bold />
                      <DetailRow label="Telefon" value={selected.ps_data.phone} />
                      <DetailRow label="Jinsi" value={selected.ps_data.gender_name} />
                      <div className="mt-2.5">
                        <p className="text-xs text-gray-400 dark:text-slate-500 mb-1">Embedding</p>
                        {selected.ps_data.embedding ? (
                          <>
                            <div className="bg-gray-50 dark:bg-slate-800 rounded-lg px-3 py-2 max-h-16 overflow-hidden relative">
                              <p className="text-[10px] font-mono text-gray-500 dark:text-slate-400 leading-tight break-all line-clamp-3">
                                [{selected.ps_data.embedding.length > 200 ? selected.ps_data.embedding.slice(0, 200) + "..." : selected.ps_data.embedding}]
                              </p>
                              <div className="absolute bottom-0 left-0 right-0 h-4 bg-gradient-to-t from-gray-50 dark:from-slate-800 to-transparent" />
                            </div>
                            <p className="text-[10px] text-gray-400 dark:text-slate-500 mt-1">
                              {selected.ps_data.embedding.split(",").length} o'lcham
                            </p>
                          </>
                        ) : (
                          <span className="text-sm text-gray-400 dark:text-slate-500 italic">Yo'q</span>
                        )}
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-gray-400 dark:text-slate-500 italic mt-2.5">Pasport ma'lumotlari mavjud emas</p>
                  )}
                </div>

                {/* Actions */}
                <div className="detail-section px-5 py-4 flex gap-2">
                  <button
                    onClick={async (e) => {
                      e.stopPropagation();
                      setFetchingGtsp(true);
                      try {
                        const updated = await fetchGtspImageApi(selected.id);
                        setSelected(updated);
                        // Ro'yxatni ham yangilash
                        setData((prev) => prev ? {
                          ...prev,
                          items: prev.items.map((s) => s.id === updated.id ? { ...s, ...updated } : s),
                        } : prev);
                      } catch (err) {
                        alert(extractErrorMessage(err));
                      } finally {
                        setFetchingGtsp(false);
                      }
                    }}
                    disabled={fetchingGtsp}
                    className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 text-sm font-medium text-teal-700 dark:text-teal-400 bg-teal-50 dark:bg-teal-900/20 hover:bg-teal-100 dark:hover:bg-teal-900/30 rounded-lg transition-colors disabled:opacity-50"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    {fetchingGtsp ? "Yuklanmoqda..." : "GTSP rasm"}
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); openEdit(selected); }}
                    className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2.5 text-sm font-medium text-primary-700 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 hover:bg-primary-100 dark:hover:bg-primary-900/30 rounded-lg transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    Tahrirlash
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); confirmDelete(selected.id, `${selected.last_name} ${selected.first_name}`); }}
                    className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    O'chirish
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ===== Delete Confirmation Modal ===== */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/40 dark:bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
            <div className="p-6 text-center">
              <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                <svg className="w-7 h-7 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">Studentni o'chirish</h3>
              <p className="text-sm text-gray-500 dark:text-slate-400">
                <span className="font-semibold text-gray-700 dark:text-slate-300">{deleteTarget.name}</span> studentini va unga tegishli barcha ma'lumotlarni (pasport, loglar) o'chirmoqchimisiz?
              </p>
              <p className="text-xs text-red-500 dark:text-red-400 mt-2">Bu amalni qaytarib bo'lmaydi!</p>
            </div>
            <div className="px-6 py-4 bg-gray-50 dark:bg-slate-700/50 flex justify-end gap-3">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-400 hover:text-gray-800 dark:hover:text-white transition-colors"
              >
                Bekor qilish
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors disabled:opacity-50"
              >
                {deleting ? "O'chirilmoqda..." : "Ha, o'chirish"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ===== Create/Edit Modal ===== */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 dark:bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
            <div className="px-6 py-5 border-b border-gray-200 dark:border-slate-700 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {editId ? "Studentni tahrirlash" : "Yangi student"}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-300">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="px-6 py-5 overflow-y-auto">
              {formError && (
                <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-xl text-sm">{formError}</div>
              )}

              {/* Basic fields */}
              <p className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-3">Asosiy ma'lumotlar</p>
              <div className="grid grid-cols-2 gap-4">
                <ModalField label="Familiya *">
                  <input type="text" value={form.last_name} onChange={(e) => setField("last_name", e.target.value)} className="input-field w-full" />
                </ModalField>
                <ModalField label="Ism *">
                  <input type="text" value={form.first_name} onChange={(e) => setField("first_name", e.target.value)} className="input-field w-full" />
                </ModalField>
                <ModalField label="Otasining ismi">
                  <input type="text" value={form.middle_name || ""} onChange={(e) => setField("middle_name", e.target.value)} className="input-field w-full" />
                </ModalField>
                <ModalField label="IMEI (PINFL)">
                  <input type="text" value={form.imei || ""} onChange={(e) => setField("imei", e.target.value)} className="input-field w-full" />
                </ModalField>

                {/* Region → Zone cascade */}
                <ModalField label="Viloyat (Region)">
                  <select
                    value={modalRegionId}
                    onChange={(e) => {
                      setModalRegionId(e.target.value);
                      setField("zone_id", 0);
                    }}
                    className="input-field w-full"
                  >
                    <option value="">Tanlang...</option>
                    {regions.map((r) => (
                      <option key={r.id} value={String(r.id)}>{r.name}</option>
                    ))}
                  </select>
                </ModalField>
                <ModalField label="Bino (Zone)">
                  <select
                    value={form.zone_id || ""}
                    onChange={(e) => setField("zone_id", Number(e.target.value))}
                    className="input-field w-full"
                    disabled={!modalRegionId || modalZonesLoading}
                  >
                    <option value="0">{modalZonesLoading ? "Yuklanmoqda..." : modalRegionId ? "Tanlang..." : "Avval viloyatni tanlang"}</option>
                    {modalZones.map((z) => (
                      <option key={z.id} value={z.id}>{z.name}</option>
                    ))}
                  </select>
                </ModalField>

                <ModalField label="Test sessiya">
                  <select
                    value={modalTestSessionId}
                    onChange={(e) => {
                      setModalTestSessionId(e.target.value);
                      setField("session_smena_id", 0);
                    }}
                    className="input-field w-full"
                  >
                    <option value="">Tanlang...</option>
                    {testSessions.map((ts) => (
                      <option key={ts.id} value={String(ts.id)}>
                        {ts.name} ({ts.test?.name || "—"})
                      </option>
                    ))}
                  </select>
                </ModalField>
                <ModalField label="Sessiya smena">
                  <select
                    value={form.session_smena_id || ""}
                    onChange={(e) => setField("session_smena_id", Number(e.target.value))}
                    className="input-field w-full"
                    disabled={!modalTestSessionId}
                  >
                    <option value="0">{modalTestSessionId ? "Tanlang..." : "Avval sessiyani tanlang"}</option>
                    {modalTestSessionId && testSessions
                      .find((ts) => ts.id === Number(modalTestSessionId))
                      ?.smenas.map((sm) => (
                        <option key={sm.id} value={sm.id}>
                          {sm.smena?.name || `Smena #${sm.number}`} — {sm.day}
                        </option>
                      ))}
                  </select>
                </ModalField>
                <ModalField label="Test sanasi">
                  <input type="datetime-local" value={form.e_date} onChange={(e) => setField("e_date", e.target.value)} className="input-field w-full" />
                </ModalField>
                <ModalField label="Fan nomi">
                  <input type="text" value={form.subject_name || ""} onChange={(e) => setField("subject_name", e.target.value)} className="input-field w-full" />
                </ModalField>
                <ModalField label="Guruh raqami">
                  <input type="number" value={form.gr_n} onChange={(e) => setField("gr_n", Number(e.target.value))} className="input-field w-full" />
                </ModalField>
                <ModalField label="Joy raqami">
                  <input type="number" value={form.sp_n} onChange={(e) => setField("sp_n", Number(e.target.value))} className="input-field w-full" />
                </ModalField>
                <ModalField label="S-kod">
                  <input type="number" value={form.s_code} onChange={(e) => setField("s_code", Number(e.target.value))} className="input-field w-full" />
                </ModalField>
                <ModalField label="Fan ID">
                  <input type="number" value={form.subject_id} onChange={(e) => setField("subject_id", Number(e.target.value))} className="input-field w-full" />
                </ModalField>
                <ModalField label="Til ID">
                  <input type="number" value={form.lang_id} onChange={(e) => setField("lang_id", Number(e.target.value))} className="input-field w-full" />
                </ModalField>
                <ModalField label="Daraja ID">
                  <input type="number" value={form.level_id} onChange={(e) => setField("level_id", Number(e.target.value))} className="input-field w-full" />
                </ModalField>
              </div>

              {/* Boolean flags — only for edit mode */}
              {editId && (
                <>
                  <p className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mt-6 mb-3">Holat bayroqlari</p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    <ToggleField label="Tayyor (Ready)" checked={!!form.is_ready} onChange={(v) => setField("is_ready", v)} />
                    <ToggleField label="Yuz (Face)" checked={!!form.is_face} onChange={(v) => setField("is_face", v)} />
                    <ToggleField label="Rasm (Image)" checked={!!form.is_image} onChange={(v) => setField("is_image", v)} />
                    <ToggleField label="Cheating" checked={!!form.is_cheating} onChange={(v) => setField("is_cheating", v)} color="orange" />
                    <ToggleField label="Qora ro'yxat" checked={!!form.is_blacklist} onChange={(v) => setField("is_blacklist", v)} color="red" />
                    <ToggleField label="Kirgan (Entered)" checked={!!form.is_entered} onChange={(v) => setField("is_entered", v)} color="green" />
                  </div>
                </>
              )}

              {/* PS Data — only for edit mode */}
              {editId && (
                <>
                  <p className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mt-6 mb-3">Pasport ma'lumotlari</p>
                  <div className="grid grid-cols-2 gap-4">
                    <ModalField label="Pasport seriyasi">
                      <input type="text" value={form.ps_ser || ""} onChange={(e) => setField("ps_ser", e.target.value)} placeholder="AA" maxLength={5} className="input-field w-full" />
                    </ModalField>
                    <ModalField label="Pasport raqami">
                      <input type="text" value={form.ps_num || ""} onChange={(e) => setField("ps_num", e.target.value)} placeholder="1234567" maxLength={10} className="input-field w-full" />
                    </ModalField>
                    <ModalField label="Telefon raqami">
                      <input type="text" value={form.ps_phone || ""} onChange={(e) => setField("ps_phone", e.target.value)} placeholder="+998901234567" maxLength={13} className="input-field w-full" />
                    </ModalField>
                  </div>
                  <div className="mt-4 space-y-4">
                    <ModalField label="Rasm (Base64)">
                      <textarea
                        value={form.ps_img || ""}
                        onChange={(e) => setField("ps_img", e.target.value)}
                        placeholder="data:image/jpeg;base64,..."
                        rows={3}
                        className="input-field w-full font-mono text-[11px] resize-y"
                      />
                      {form.ps_img && (
                        <div className="mt-2 flex items-center gap-3">
                          <img
                            src={form.ps_img.startsWith("data:") ? form.ps_img : `data:image/jpeg;base64,${form.ps_img}`}
                            alt="Preview"
                            className="w-12 h-14 rounded-lg object-cover border border-gray-200 dark:border-slate-600"
                            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                          />
                          <span className="text-[10px] text-gray-400 dark:text-slate-500">
                            {(form.ps_img.length / 1024).toFixed(1)} KB
                          </span>
                        </div>
                      )}
                    </ModalField>
                    <ModalField label="Embedding">
                      <textarea
                        value={form.ps_embedding || ""}
                        onChange={(e) => setField("ps_embedding", e.target.value)}
                        placeholder="0.0123, -0.0456, ..."
                        rows={3}
                        className="input-field w-full font-mono text-[11px] resize-y"
                      />
                      {form.ps_embedding && (
                        <p className="text-[10px] text-gray-400 dark:text-slate-500 mt-1">
                          {form.ps_embedding.split(",").length} o'lcham
                        </p>
                      )}
                    </ModalField>
                  </div>
                </>
              )}
            </div>
            <div className="px-6 py-4 border-t border-gray-200 dark:border-slate-700 flex justify-end gap-3">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-400 hover:text-gray-800 dark:hover:text-white transition-colors">
                Bekor qilish
              </button>
              <button onClick={handleSave} disabled={saving} className="btn-primary">
                {saving ? "Saqlanmoqda..." : "Saqlash"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- Reusable components ---- */

function FilterSelect({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div>
      <label className="block text-[10px] uppercase tracking-wider text-gray-500 dark:text-slate-400 mb-1 font-semibold">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="input-field !py-1.5 !text-sm w-full">
        <option value="">Barchasi</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

function TH({ children, align = "left" }: { children: React.ReactNode; align?: "left" | "center" }) {
  return (
    <th className={`px-3 py-3 font-semibold text-[11px] uppercase tracking-wider text-gray-400 dark:text-slate-500 whitespace-nowrap ${align === "center" ? "text-center" : "text-left"}`}>
      {children}
    </th>
  );
}

function TD({ children, className = "", align = "left" }: { children: React.ReactNode; className?: string; align?: "left" | "center" }) {
  return (
    <td className={`px-3 py-2.5 whitespace-nowrap ${align === "center" ? "text-center" : "text-left"} ${className}`}>
      {children}
    </td>
  );
}

function StatusDot({ active, color, title }: { active: boolean; color: string; title?: string }) {
  const colors: Record<string, string> = { orange: "bg-orange-500", green: "bg-emerald-500" };
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full transition-colors ${active ? colors[color] || "bg-gray-500" : "bg-gray-200 dark:bg-slate-700"}`}
      title={title ? `${title}: ${active ? "Ha" : "Yo'q"}` : undefined}
    />
  );
}

function Badge({ label, active, on }: { label: string; active: boolean; on: string }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium ${active ? on : "bg-gray-50 text-gray-400 dark:bg-slate-700/50 dark:text-slate-500"}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${active ? "bg-current" : "bg-gray-300 dark:bg-slate-500"}`} />
      {label}
    </span>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p className="text-xs uppercase tracking-wider font-semibold text-gray-400 dark:text-slate-500">{children}</p>;
}

function DetailRow({ label, value, mono, bold }: { label: string; value: string | null | undefined; mono?: boolean; bold?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 py-0.5">
      <span className="text-xs text-gray-400 dark:text-slate-500 flex-shrink-0">{label}</span>
      <span
        className={`text-sm text-right truncate max-w-[220px] ${bold ? "font-bold text-gray-900 dark:text-white" : "font-medium text-gray-700 dark:text-slate-300"} ${mono ? "font-mono" : ""}`}
        title={value || undefined}
      >
        {value || "—"}
      </span>
    </div>
  );
}

function ModalField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">{label}</label>
      {children}
    </div>
  );
}

function ToggleField({ label, checked, onChange, color = "primary" }: {
  label: string; checked: boolean; onChange: (v: boolean) => void; color?: "primary" | "red" | "orange" | "green";
}) {
  const colorMap: Record<string, string> = { primary: "bg-primary-500", red: "bg-red-500", orange: "bg-orange-500", green: "bg-emerald-500" };
  return (
    <label className="flex items-center gap-2.5 cursor-pointer p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700/30 transition-colors">
      <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 flex-shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ${checked ? colorMap[color] : "bg-gray-200 dark:bg-slate-600"}`}>
        <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform duration-200 ${checked ? "translate-x-4" : "translate-x-0"}`} />
      </button>
      <span className="text-xs font-medium text-gray-700 dark:text-slate-300">{label}</span>
    </label>
  );
}
