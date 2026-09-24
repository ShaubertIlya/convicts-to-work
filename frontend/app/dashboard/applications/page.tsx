"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useDashboardUser } from "@/components/dashboard-user";
import { ClinicalScreeningsPage } from "@/components/clinical-screenings-page";
import { Pagination } from "@/components/pagination";
import { api } from "@/lib/api";
import { Application, applicationStatuses } from "@/lib/applications";
import { formatDate, formatMoney, Page, statusNames, unwrap } from "@/lib/dashboard";
import { Skill } from "@/lib/prisoners";
import { REGISTRY_PAGE_SIZE } from "@/lib/registry";


export default function ApplicationsPage() {
  const user = useDashboardUser();
  if (user.role === "MEDIC" || user.role === "PSYCHOLOGIST") {
    return <ClinicalScreeningsPage role={user.role} />;
  }
  return <JobApplicationsPage />;
}

function JobApplicationsPage() {
  const user = useDashboardUser();
  const [applications, setApplications] = useState<Application[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(REGISTRY_PAGE_SIZE) });
      if (query.trim()) params.set("search", query.trim());
      if (status) params.set("status", status);
      const [applicationRows, skillRows] = await Promise.all([
        api<Page<Application>>(`/applications/?${params}`), api<Skill[]>("/prisoners/skills/"),
      ]);
      setApplications(unwrap(applicationRows));
      setTotal(applicationRows.count ?? unwrap(applicationRows).length);
      setSkills(skillRows);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось загрузить заявки");
    }
  }, [page, query, status]);

  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(task);
  }, [load]);

  const pageCount = Math.max(1, Math.ceil(total / REGISTRY_PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const rows = applications;

  async function action(path: string, body: object = {}) {
    setError("");
    try { await api(path, { method: "POST", body: JSON.stringify(body) }); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Ошибка операции"); }
  }

  async function createApplication(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    try {
      await api("/applications/", { method: "POST", body: JSON.stringify({ ...values, quantity: Number(values.quantity), salary: Number(values.salary) }) });
      form.reset();
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Ошибка создания заявки"); }
  }

  return <>
    <div className="page-heading"><div><p className="page-kicker">Рабочий процесс</p><h1>Заявки</h1><p>Создание, подбор кандидатов и прохождение согласований.</p></div></div>
    {error && <p className="error" role="alert">{error}</p>}
    {user.role === "BUSINESS_ADMIN" && <details className="surface-panel create-panel" id="new-application">
      <summary><span><strong>Новая заявка</strong><small>Заполните потребность в работниках</small></span><span className="md-button primary">+ Создать</span></summary>
      <form className="compact-form" onSubmit={createApplication}>
        <div className="field"><label htmlFor="quantity">Количество работников</label><input id="quantity" name="quantity" type="number" min="1" max="1000" step="1" required /></div>
        <div className="field"><label htmlFor="skill">Специальность</label><select id="skill" name="skill" required><option value="">Выберите</option>{skills.map((item) => <option value={item.id} key={item.id}>{item.name_ru}</option>)}</select></div>
        <div className="field"><label htmlFor="skill_requirement">Требование</label><select id="skill_requirement" name="skill_requirement"><option value="REQUIRED">Только с навыком</option><option value="TRAINING_ALLOWED">Возможно обучение</option></select></div>
        <div className="field"><label htmlFor="workplace_address">Место работы</label><input id="workplace_address" name="workplace_address" minLength={5} maxLength={500} required /></div>
        <div className="field"><label htmlFor="salary">Зарплата, ₸</label><input id="salary" name="salary" type="number" min="1" max="1000000000" step="0.01" required /></div>
        <div className="field"><label htmlFor="schedule">График</label><input id="schedule" name="schedule" minLength={2} maxLength={255} placeholder="5/2, 09:00–17:00" required /></div>
        <div className="field"><label htmlFor="employment_type">Занятость</label><select id="employment_type" name="employment_type"><option value="FULL">Полная</option><option value="PART_TIME">Частичная</option></select></div>
        <div className="field"><label>Срок</label><input value="12 месяцев" readOnly /></div>
        <div className="field span-2"><label htmlFor="activity_description">Описание работ</label><textarea id="activity_description" name="activity_description" minLength={10} maxLength={2000} rows={3} required /></div>
        <div className="span-2 form-actions"><button className="md-button primary">Сохранить черновик</button></div>
      </form>
    </details>}
    <section className="surface-panel table-panel registry-panel applications-registry">
      <div className="panel-heading"><div><h2>Реестр заявок</h2><p>{total} заявок · по {REGISTRY_PAGE_SIZE} на странице</p></div></div>
      <div className="filter-bar"><label className="search-control"><span>⌕</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Поиск по компании, специальности или адресу" /></label><select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">Все статусы</option>{applicationStatuses.map((item) => <option value={item} key={item}>{statusNames[item]}</option>)}</select><button className="text-button" type="button" onClick={() => { setQuery(""); setStatus(""); setPage(1); }}>Сбросить</button></div>
      <div className="data-table-wrap registry-table"><table className="data-table"><thead><tr><th>Заявка</th><th>Компания</th><th>Специальность</th><th>Количество</th><th>Условия</th><th>Статус</th><th /></tr></thead><tbody>
        {rows.map((application) => <tr key={application.id}><td><strong>#{application.id.slice(0, 8)}</strong><small>{formatDate(application.created_at)}</small></td><td><strong>{application.organization_name}</strong><small>БИН {application.organization_details.bin}</small></td><td>{application.skill_name_ru}</td><td>{application.quantity}</td><td><strong>{formatMoney(application.salary)} ₸</strong><small>{application.schedule}</small></td><td><span className={`status-chip status-${application.status.toLowerCase()}`}>{statusNames[application.status] ?? application.status}</span></td><td><div className="table-actions"><Link className="text-button" href={`/applications/${application.id}`}>{application.status === "DRAFT" && user.role === "BUSINESS_ADMIN" ? "Редактировать" : "Открыть"}</Link>{user.role === "BUSINESS_ADMIN" && application.status === "DRAFT" && <button className="text-button" type="button" onClick={() => action(`/applications/${application.id}/submit/`)}>Подать</button>}{user.role === "BUSINESS_ADMIN" && ["DRAFT", "SUBMITTED"].includes(application.status) && <button className="text-button danger-text" type="button" onClick={() => action(`/applications/${application.id}/withdraw/`)}>Отозвать</button>}</div></td></tr>)}
        {rows.length === 0 && <tr><td colSpan={7} className="empty-state">По заданным фильтрам заявок нет</td></tr>}
      </tbody></table></div>
      <Pagination page={currentPage} pageCount={pageCount} onChange={setPage} />
    </section>
  </>;
}
