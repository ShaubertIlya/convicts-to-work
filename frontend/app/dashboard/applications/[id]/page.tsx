"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useDashboardUser } from "@/components/dashboard-user";
import { Pagination } from "@/components/pagination";
import { OrganizationRequisites } from "@/components/organization-requisites";
import { ScreeningReviewForm } from "@/components/screening-review-form";
import { api } from "@/lib/api";
import { Application } from "@/lib/applications";
import { formatDate, formatMoney, Page, statusNames, unwrap } from "@/lib/dashboard";
import { mediaPath, Prisoner, Skill } from "@/lib/prisoners";

type ContractSummary = {
  id: string; number: string; prisoner_name: string; status: string;
  signatures: { party: string }[];
};

function localDate(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function annualEnd(value: string) {
  const start = new Date(`${value}T12:00:00`);
  const end = new Date(start);
  end.setFullYear(start.getFullYear() + 1);
  if (end.getMonth() !== start.getMonth()) end.setDate(0);
  return localDate(end);
}

const candidateStatusNames: Record<string, string> = {
  PROPOSED: "Предложен",
  BUSINESS_ACCEPTED: "Выбран МСБ",
  BUSINESS_REJECTED: "Не выбран МСБ",
  ENBEK_APPROVED: "Согласован Еңбек",
  ENBEK_REJECTED: "Отклонён Еңбек",
  MEDICAL_PENDING: "Ожидает медосмотр",
  MEDICAL_PASSED: "Медосмотр пройден",
  MEDICAL_FAILED: "Медицинский отказ",
  PSYCHOLOGICAL_PENDING: "Ожидает психолога",
  PSYCHOLOGICAL_PASSED: "Психолог пройден",
  PSYCHOLOGICAL_FAILED: "Отказ психолога",
  READY_FOR_CONTRACT: "Готов к договору",
  CONTRACT_CREATED: "Договор создан",
};

const businessAcceptedStatuses = new Set([
  "BUSINESS_ACCEPTED", "ENBEK_APPROVED", "MEDICAL_PENDING", "MEDICAL_PASSED",
  "MEDICAL_FAILED", "PSYCHOLOGICAL_PENDING", "PSYCHOLOGICAL_PASSED",
  "PSYCHOLOGICAL_FAILED", "READY_FOR_CONTRACT", "CONTRACT_CREATED",
]);

function businessDecision(status: string) {
  if (status === "BUSINESS_REJECTED") return { label: "МСБ: не согласован", tone: "rejected" };
  if (businessAcceptedStatuses.has(status)) return { label: "МСБ: согласован", tone: "accepted" };
  return { label: "МСБ: ожидается решение", tone: "pending" };
}

function enbekDecision(status: string) {
  if (status === "ENBEK_REJECTED") return { label: "Еңбек: отклонён", tone: "rejected" };
  if (status === "BUSINESS_REJECTED") return { label: "Еңбек: не рассматривался", tone: "pending" };
  if (["PROPOSED", "BUSINESS_ACCEPTED"].includes(status)) {
    return { label: "Еңбек: ожидается решение", tone: "pending" };
  }
  return { label: "Еңбек: согласован", tone: "accepted" };
}

export default function ApplicationDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const user = useDashboardUser();
  const [application, setApplication] = useState<Application | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [prisoners, setPrisoners] = useState<Prisoner[]>([]);
  const [poolPage, setPoolPage] = useState(1);
  const [poolTotal, setPoolTotal] = useState(0);
  const [selectedPool, setSelectedPool] = useState<string[]>([]);
  const [selectedProposals, setSelectedProposals] = useState<string[]>([]);
  const [selectedMedical, setSelectedMedical] = useState<string[]>([]);
  const [selectedPsychological, setSelectedPsychological] = useState<string[]>([]);
  const [selectedContracts, setSelectedContracts] = useState<string[]>([]);
  const [contracts, setContracts] = useState<ContractSummary[]>([]);
  const [contractTotal, setContractTotal] = useState(0);
  const [businessComment, setBusinessComment] = useState("");
  const [enbekComment, setEnbekComment] = useState("");
  const [contractStartsOn, setContractStartsOn] = useState(() => localDate(new Date()));
  const [contractEndsOn, setContractEndsOn] = useState(() => annualEnd(localDate(new Date())));
  const [query, setQuery] = useState("");
  const [skill, setSkill] = useState("");
  const [rating, setRating] = useState("");
  const [education, setEducation] = useState("");
  const [availability, setAvailability] = useState("available");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [row, skillRows, contractRows] = await Promise.all([
        api<Application>(`/applications/${id}/`), api<Skill[]>("/prisoners/skills/"),
        ["MEDIC", "PSYCHOLOGIST"].includes(user.role)
          ? Promise.resolve({ count: 0, results: [] as ContractSummary[] })
          : api<Page<ContractSummary>>(`/contracts/?application_id=${id}&page_size=50`),
      ]);
      setApplication(row);
      setSkills(skillRows);
      setContracts(unwrap(contractRows));
      setContractTotal(contractRows.count ?? unwrap(contractRows).length);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Заявка не найдена"); }
  }, [id, user.role]);
  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(task);
  }, [load]);

  const applicationStatus = application?.status;
  useEffect(() => {
    if (user.role !== "ENBEK_EXECUTOR" || applicationStatus !== "SUBMITTED") return;
    const task = window.setTimeout(() => {
      const params = new URLSearchParams({ page: String(poolPage) });
      if (query.trim()) params.set("search", query.trim());
      if (skill) params.set("skill", skill);
      if (rating) params.set("rating_min", rating);
      if (education.trim()) params.set("education", education.trim());
      if (availability) params.set("available", availability === "available" ? "true" : "false");
      api<Page<Prisoner>>(`/prisoners/?${params}`)
        .then((result) => { setPrisoners(unwrap(result)); setPoolTotal(result.count ?? unwrap(result).length); })
        .catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить кандидатов"));
    }, 200);
    return () => window.clearTimeout(task);
  }, [applicationStatus, availability, education, poolPage, query, rating, skill, user.role]);

  const filteredPrisoners = prisoners;

  function togglePool(prisoner: Prisoner) {
    if (!application) return;
    const hasRequiredSkill = prisoner.skills.some((item) => item.id === application.skill);
    if (application.skill_requirement === "REQUIRED" && !hasRequiredSkill) {
      setError("Для этой заявки можно выбирать только кандидатов с требуемым навыком.");
      return;
    }
    setError("");
    setSelectedPool((current) => {
      if (current.includes(prisoner.id)) return current.filter((item) => item !== prisoner.id);
      if (current.length >= application.quantity) { setError(`Можно выбрать не более ${application.quantity} кандидатов.`); return current; }
      return [...current, prisoner.id];
    });
  }
  function toggleProposal(candidateId: string) {
    setSelectedProposals((current) => current.includes(candidateId)
      ? current.filter((item) => item !== candidateId)
      : [...current, candidateId]);
  }
  function toggleSelection(candidateId: string, selected: string[], setSelected: (value: string[]) => void) {
    setSelected(selected.includes(candidateId)
      ? selected.filter((id) => id !== candidateId)
      : [...selected, candidateId]);
  }
  async function post(path: string, body: object = {}) {
    setError(""); setSuccess("");
    try { await api(path, { method: "POST", body: JSON.stringify(body) }); await load(); return true; }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Ошибка операции"); return false; }
  }
  async function saveDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      await api(`/applications/${id}/`, { method: "PATCH", body: JSON.stringify({ ...values, quantity: Number(values.quantity), salary: Number(values.salary) }) });
      setSuccess("Черновик сохранён."); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось сохранить черновик"); }
  }
  async function propose() {
    if (await post(`/applications/${id}/propose/`, { prisoner_ids: selectedPool })) {
      setSelectedPool([]); setSuccess("Предложение отправлено организации.");
    }
  }
  async function createContracts() {
    if (!application) return;
    if (contractEndsOn <= contractStartsOn) { setError("Дата окончания договора должна быть позже даты начала."); return; }
    if (await post("/contracts/create-from-application/", { application_id: application.id, candidate_ids: selectedContracts, starts_on: contractStartsOn, ends_on: contractEndsOn })) {
      setSelectedContracts([]);
      setSuccess("Договоры созданы.");
    }
  }

  async function sendBatchToScreening(candidateIds: string[], kind: "MEDICAL" | "PSYCHOLOGICAL") {
    setError(""); setSuccess(""); setBusy(true);
    try {
      for (const candidateId of candidateIds) {
        await api(`/applications/${id}/send-to-screening/`, {
          method: "POST",
          body: JSON.stringify({ candidate_id: candidateId, kind }),
        });
      }
      setSuccess(kind === "MEDICAL" ? "Кандидаты направлены на медицинское обследование." : "Кандидаты направлены на психологическое обследование.");
      if (kind === "MEDICAL") setSelectedMedical([]);
      else setSelectedPsychological([]);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось направить кандидатов на обследование");
      await load();
    } finally {
      setBusy(false);
    }
  }

  if (!application) return <><Link className="back-link" href="/applications">← К заявкам</Link>{error ? <p className="error">{error}</p> : <div className="portal-loading inline"><span className="loader" />Загрузка заявки…</div>}</>;
  const draftEditable = user.role === "BUSINESS_ADMIN" && application.status === "DRAFT";
  const enbekActor = ["ENBEK_MANAGER", "ENBEK_EXECUTOR"].includes(user.role);
  const awaitingMedical = application.candidates.filter((item) => item.status === "ENBEK_APPROVED");
  const awaitingPsychologist = application.candidates.filter((item) => item.status === "MEDICAL_PASSED");
  const readyForContracts = application.candidates.filter((item) => item.status === "READY_FOR_CONTRACT");
  const medicalPending = application.candidates.filter((item) => item.status === "MEDICAL_PENDING").length;
  const psychologicalPending = application.candidates.filter((item) => item.status === "PSYCHOLOGICAL_PENDING").length;
  const canSign = contracts.length > 0;

  return <>
    <Link className="back-link" href="/applications">← К реестру заявок</Link>
    <div className="page-heading application-heading"><div><p className="page-kicker">Заявка #{application.id.slice(0, 8)}</p><h1>{application.skill_name_ru}</h1><p>{application.organization_name} · {application.quantity} чел. · {formatMoney(application.salary)} ₸</p></div><span className={`status-chip status-${application.status.toLowerCase()}`}>{statusNames[application.status] ?? application.status}</span></div>
    {error && <p className="error" role="alert">{error}</p>}{success && <p className="success">{success}</p>}
    <section className="surface-panel application-overview"><div><small>Место работы</small><strong>{application.workplace_address}</strong></div><div><small>График</small><strong>{application.schedule}</strong></div><div><small>Занятость</small><strong>{application.employment_type === "FULL" ? "Полная" : "Частичная"}</strong></div><div><small>Требование</small><strong>{application.skill_requirement === "REQUIRED" ? "Только с навыком" : "Возможно обучение"}</strong></div><div className="span-2"><small>Описание работ</small><strong>{application.activity_description}</strong></div></section>
    {!(["MEDIC", "PSYCHOLOGIST"].includes(user.role)) && <section className="surface-panel requisites-panel"><div className="panel-heading"><div><h2>Реквизиты компании</h2><p>Снимок данных на момент подачи заявки</p></div></div><OrganizationRequisites organization={application.organization_details} expanded /></section>}

    {draftEditable && <section className="surface-panel"><div className="panel-heading"><div><h2>Редактирование черновика</h2><p>После отправки поля будут заблокированы</p></div></div><form className="compact-form" onSubmit={saveDraft}>
      <div className="field"><label htmlFor="edit_quantity">Количество работников</label><input id="edit_quantity" name="quantity" type="number" min="1" max="1000" defaultValue={application.quantity} required /></div>
      <div className="field"><label htmlFor="edit_skill">Специальность</label><select id="edit_skill" name="skill" defaultValue={application.skill} required>{skills.map((item) => <option key={item.id} value={item.id}>{item.name_ru}</option>)}</select></div>
      <div className="field"><label htmlFor="edit_requirement">Требование</label><select id="edit_requirement" name="skill_requirement" defaultValue={application.skill_requirement}><option value="REQUIRED">Только с навыком</option><option value="TRAINING_ALLOWED">Возможно обучение</option></select></div>
      <div className="field"><label htmlFor="edit_address">Место работы</label><input id="edit_address" name="workplace_address" minLength={5} maxLength={500} defaultValue={application.workplace_address} required /></div>
      <div className="field"><label htmlFor="edit_salary">Зарплата, ₸</label><input id="edit_salary" name="salary" type="number" min="1" max="1000000000" step="0.01" defaultValue={application.salary} required /></div>
      <div className="field"><label htmlFor="edit_schedule">График</label><input id="edit_schedule" name="schedule" minLength={2} maxLength={255} defaultValue={application.schedule} required /></div>
      <div className="field"><label htmlFor="edit_employment">Занятость</label><select id="edit_employment" name="employment_type" defaultValue={application.employment_type}><option value="FULL">Полная</option><option value="PART_TIME">Частичная</option></select></div>
      <div className="field span-2"><label htmlFor="edit_description">Описание работ</label><textarea id="edit_description" name="activity_description" minLength={10} maxLength={2000} rows={3} defaultValue={application.activity_description} required /></div>
      <div className="span-2 form-actions"><button className="md-button primary">Сохранить изменения</button></div>
    </form></section>}

    {user.role === "ENBEK_EXECUTOR" && application.status === "SUBMITTED" && <section className="surface-panel candidate-selection"><div className="panel-heading"><div><h2>Формирование предложения</h2><p>Выбрано {selectedPool.length} из {application.quantity} · найдено {poolTotal}</p></div><button className="md-button primary" type="button" disabled={selectedPool.length === 0} onClick={propose}>Отправить предложение</button></div>
      <div className="candidate-filters"><label className="search-control span-2"><span>⌕</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPoolPage(1); }} placeholder="ФИО, ИИН, навык, квалификация или опыт" /></label><select value={skill} onChange={(event) => { setSkill(event.target.value); setPoolPage(1); }}><option value="">Все навыки</option>{skills.map((item) => <option key={item.id} value={item.id}>{item.name_ru}</option>)}</select><select value={rating} onChange={(event) => { setRating(event.target.value); setPoolPage(1); }}><option value="">Любой рейтинг</option><option value="5">5 звёзд</option><option value="4">От 4 звёзд</option><option value="3">От 3 звёзд</option></select><input value={education} onChange={(event) => { setEducation(event.target.value); setPoolPage(1); }} placeholder="Образование" /><select value={availability} onChange={(event) => { setAvailability(event.target.value); setPoolPage(1); }}><option value="">Все</option><option value="available">Доступные</option><option value="busy">Недоступные</option></select></div>
      <div className="proposal-list">{filteredPrisoners.map((item) => { const hasSkill = item.skills.some((row) => row.id === application.skill); const disabled = !item.is_available || (application.skill_requirement === "REQUIRED" && !hasSkill); return <article className={`proposal-card ${selectedPool.includes(item.id) ? "selected" : ""} ${disabled ? "disabled" : ""}`} key={item.id}><label><input type="checkbox" disabled={disabled} checked={selectedPool.includes(item.id)} onChange={() => togglePool(item)} /><span className="prisoner-photo small">{item.photo && <Image unoptimized width={66} height={82} src={mediaPath(item.photo)} alt={`Фото: ${item.full_name}`} />}</span><span className="proposal-main"><strong>{item.full_name}</strong><small>{item.qualification} · стаж {item.total_work_experience_years} лет · ★ {item.rating}</small><span className="skill-chips">{item.skills.map((row) => <span key={row.id}>{row.name_ru}</span>)}</span><small>{item.education} · {item.current_employment}</small>{item.has_active_contracts && <small>Есть действующий договор</small>}{(item.medical_restrictions || item.disciplinary_restrictions) && <small className="restriction">Ограничения: {item.medical_restrictions || item.disciplinary_restrictions}</small>}</span></label><Link className="text-button" href={`/prisoners/${item.id}`}>Личное дело →</Link></article>; })}{filteredPrisoners.length === 0 && <p className="empty-state">Подходящие кандидаты не найдены</p>}</div>
      <Pagination page={Math.min(poolPage, Math.max(1, Math.ceil(poolTotal / 10)))} pageCount={Math.max(1, Math.ceil(poolTotal / 10))} onChange={setPoolPage} />
    </section>}

    {application.candidates.length > 0 && <section className="surface-panel candidates-panel">
      <div className="panel-heading"><div><h2>Кандидаты по заявке</h2><p>{application.candidates.length} человек · решение каждой стороны указано отдельно</p></div></div>
      <div className="proposal-list compact">{application.candidates.map((candidate, index) => {
        const business = businessDecision(candidate.status);
        const enbek = enbekDecision(candidate.status);
        const pendingScreening = candidate.screenings.find((item) => item.result === "PENDING"
          && ((user.role === "MEDIC" && item.kind === "MEDICAL")
            || (user.role === "PSYCHOLOGIST" && item.kind === "PSYCHOLOGICAL")));
        return <article className={`proposal-card decision-${business.tone} ${pendingScreening ? "has-review" : ""} ${selectedProposals.includes(candidate.id) ? "selected" : ""}`} key={candidate.id}>
          <label>
            {user.role === "BUSINESS_ADMIN" && application.status === "PROPOSED" && <input type="checkbox" checked={selectedProposals.includes(candidate.id)} onChange={() => toggleProposal(candidate.id)} />}
            {enbekActor && candidate.status === "ENBEK_APPROVED" && <input type="checkbox" aria-label="Выбрать для медосмотра" checked={selectedMedical.includes(candidate.id)} onChange={() => toggleSelection(candidate.id, selectedMedical, setSelectedMedical)} />}
            {enbekActor && candidate.status === "MEDICAL_PASSED" && <input type="checkbox" aria-label="Выбрать для психолога" checked={selectedPsychological.includes(candidate.id)} onChange={() => toggleSelection(candidate.id, selectedPsychological, setSelectedPsychological)} />}
            {enbekActor && candidate.status === "READY_FOR_CONTRACT" && <input type="checkbox" aria-label="Выбрать для договора" checked={selectedContracts.includes(candidate.id)} onChange={() => toggleSelection(candidate.id, selectedContracts, setSelectedContracts)} />}
            <span className="prisoner-photo small">{candidate.prisoner.photo && <Image unoptimized width={66} height={82} src={mediaPath(candidate.prisoner.photo)} alt="Фото кандидата" />}</span>
            <span className="proposal-main">
              <strong>{candidate.prisoner.full_name ?? `Кандидат №${index + 1}`}</strong>
              <small>★ {candidate.prisoner.rating} · текущий этап: {candidateStatusNames[candidate.status] ?? candidate.status}</small>
              <span className="candidate-decisions"><span className={business.tone}>{business.label}</span><span className={enbek.tone}>{enbek.label}</span></span>
              <span className="skill-chips">{candidate.prisoner.skills.map((row) => <span key={row.id}>{row.name_ru}</span>)}</span>
              {candidate.screenings.filter((item) => item.result !== "PENDING").map((item) => <span className="screening-result" key={item.id}>
                <strong>{item.kind === "MEDICAL" ? "Медицинское" : "Психологическое"} заключение: {item.result === "APPROVED" ? "согласовано" : "отклонено"}</strong>
                {item.reviewed_at && <small>Решение {formatDate(item.reviewed_at)}{item.reviewer_name ? ` · ${item.reviewer_name}` : ""}</small>}
                {item.comment && <small>{item.comment}</small>}
                {item.conclusion_document && <a className="text-button" href={mediaPath(item.conclusion_document)} target="_blank" rel="noreferrer">Открыть заключение PDF →</a>}
              </span>)}
            </span>
          </label>
          {["ENBEK_ADMIN", "ENBEK_MANAGER", "ENBEK_EXECUTOR"].includes(user.role) && <Link className="text-button" href={`/prisoners/${candidate.prisoner.id}`}>Личное дело →</Link>}
          {pendingScreening && <ScreeningReviewForm screening={pendingScreening} onReviewed={load} />}
        </article>;
      })}</div>

      <div className="workflow-panel">
        <div><strong>Дальнейшие действия</strong><small>Медицинское обследование → психологическое обследование → трудовой договор</small></div>
        <div className="workflow-actions">
          {user.role === "BUSINESS_ADMIN" && application.status === "PROPOSED" && <div className="workflow-decision"><label htmlFor="business-comment">Комментарий МСБ</label><textarea id="business-comment" value={businessComment} onChange={(event) => setBusinessComment(event.target.value)} rows={2} maxLength={2000} placeholder="Причина выбора или отказа" /><button className="md-button primary" onClick={() => post(`/applications/${id}/business-response/`, { accepted_candidate_ids: selectedProposals, comment: businessComment })}>Отправить выбор МСБ</button></div>}
          {enbekActor && application.status === "BUSINESS_RESPONDED" && <div className="workflow-decision"><label htmlFor="enbek-comment">Комментарий Еңбек</label><textarea id="enbek-comment" value={enbekComment} onChange={(event) => setEnbekComment(event.target.value)} rows={2} maxLength={2000} placeholder="Основание решения" /><div><button className="md-button primary" onClick={() => post(`/applications/${id}/enbek-decision/`, { approved: true, comment: enbekComment })}>Согласовать выбранных кандидатов</button><button className="md-button danger" onClick={() => post(`/applications/${id}/enbek-decision/`, { approved: false, comment: enbekComment })}>Отклонить заявку</button></div></div>}
          {enbekActor && awaitingMedical.length > 0 && <button className="md-button primary" disabled={busy || selectedMedical.length === 0} onClick={() => sendBatchToScreening(selectedMedical, "MEDICAL")}>Направить на медосмотр ({selectedMedical.length})</button>}
          {enbekActor && awaitingPsychologist.length > 0 && <button className="md-button primary" disabled={busy || selectedPsychological.length === 0} onClick={() => sendBatchToScreening(selectedPsychological, "PSYCHOLOGICAL")}>Направить к психологу ({selectedPsychological.length})</button>}
          {enbekActor && readyForContracts.length > 0 && <div className="workflow-contracts"><label>Начало <input type="date" value={contractStartsOn} onChange={(event) => { setContractStartsOn(event.target.value); if (event.target.value) setContractEndsOn(annualEnd(event.target.value)); }} /></label><label>Окончание (12 месяцев) <input type="date" value={contractEndsOn} readOnly /></label><button className="md-button primary" disabled={busy || selectedContracts.length === 0 || !contractStartsOn} onClick={createContracts}>Создать договоры ({selectedContracts.length})</button></div>}
          {medicalPending > 0 && <span className="workflow-note">Ожидается заключение медика: {medicalPending}</span>}
          {psychologicalPending > 0 && <span className="workflow-note">Ожидается заключение психолога: {psychologicalPending}</span>}
          {!enbekActor && user.role === "BUSINESS_ADMIN" && ["APPROVED", "SCREENING"].includes(application.status) && <span className="workflow-note">Следующий шаг выполняет сотрудник Еңбек.</span>}
        </div>
        {(application.business_comment || application.enbek_comment) && <div className="workflow-comments">{application.business_comment && <p><strong>Комментарий МСБ:</strong> {application.business_comment}</p>}{application.enbek_comment && <p><strong>Комментарий Еңбек:</strong> {application.enbek_comment}</p>}</div>}
      </div>
    </section>}
    {canSign && <section className="surface-panel linked-contracts"><div className="panel-heading"><div><h2>Договоры по заявке</h2><p>{contractTotal} договоров · подписи и текущий статус</p></div><Link className="text-button" href={`/contracts?application_id=${application.id}`}>Все договоры →</Link></div><div className="linked-contract-list">{contracts.map((contract) => <div key={contract.id}><strong>{contract.number} · {contract.prisoner_name}</strong><span>{contract.signatures.length} из 3 подписей · {statusNames[contract.status] ?? contract.status}</span><Link className="text-button" href={`/contracts?number=${encodeURIComponent(contract.number)}`}>Открыть →</Link></div>)}</div></section>}
  </>;
}
