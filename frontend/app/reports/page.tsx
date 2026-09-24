"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/dashboard";

type Breakdown = { label: string; count: number };
type EmploymentReport = {
  as_of: string;
  population_total: number;
  employed_total: number;
  employment_rate_total: number | null;
  work_capable_total: number;
  work_capable_employed: number;
  employment_rate_capable: number | null;
  work_capacity_unknown: number;
  education: Breakdown[];
  qualification: Breakdown[];
  penitentiary_education: Breakdown[];
};

function BreakdownPanel({ title, hint, rows }: { title: string; hint: string; rows: Breakdown[] }) {
  const maximum = Math.max(1, ...rows.map((row) => row.count));
  return <section className="surface-panel report-breakdown">
    <div className="panel-heading"><div><h2>{title}</h2><p>{hint}</p></div></div>
    <div className="report-breakdown-list">
      {rows.map((row) => <div className="report-breakdown-row" key={row.label}>
        <div><span>{row.label}</span><strong>{row.count}</strong></div>
        <div className="report-bar" aria-hidden="true"><span style={{ width: `${row.count / maximum * 100}%` }} /></div>
      </div>)}
      {rows.length === 0 && <p className="empty-state">Данных пока нет</p>}
    </div>
  </section>;
}

export default function ReportsPage() {
  const [dateInput, setDateInput] = useState("");
  const [report, setReport] = useState<EmploymentReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(asOf?: string) {
    setLoading(true);
    setError("");
    try {
      const params = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
      const result = await api<EmploymentReport>(`/reports/employment/${params}`);
      setReport(result);
      setDateInput(result.as_of);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось загрузить отчёт");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(task);
  }, []);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (dateInput) void load(dateInput);
  }

  return <>
    <div className="page-heading"><div><p className="page-kicker">Аналитика</p><h1>Отчётность по трудозанятости</h1><p>Сводка для руководства Еңбек по осуждённым и действующим трудовым договорам.</p></div></div>
    <form className="surface-panel report-filter" onSubmit={submit}>
      <label htmlFor="report-date">На дату</label>
      <input id="report-date" type="date" required value={dateInput} onChange={(event) => setDateInput(event.target.value)} />
      <button className="md-button primary" type="submit" disabled={loading || !dateInput}>Сформировать</button>
      {report && <span>Данные на {formatDate(report.as_of)}</span>}
    </form>
    {error && <p className="error" role="alert">{error}</p>}
    {loading && !report ? <div className="portal-loading inline"><span className="loader" />Формирование отчёта…</div> : report && <>
      <section className="report-metrics" aria-label="Показатели трудозанятости">
        <article className="surface-panel report-metric"><small>Трудоустроены на дату</small><strong>{report.employed_total}</strong><span>человек с действующим подписанным договором</span></article>
        <article className="surface-panel report-metric"><small>Рейтинг от фактической численности</small><strong>{report.employment_rate_total === null ? "—" : `${report.employment_rate_total}%`}</strong><span>{report.employed_total} занятых / {report.population_total} осуждённых</span></article>
        <article className="surface-panel report-metric"><small>Рейтинг от трудоспособной численности</small><strong>{report.employment_rate_capable === null ? "—" : `${report.employment_rate_capable}%`}</strong><span>{report.work_capable_employed} занятых трудоспособных / {report.work_capable_total} трудоспособных</span></article>
      </section>
      {report.work_capacity_unknown > 0 && <p className="report-note">Трудоспособность не установлена: {report.work_capacity_unknown}. Эти карточки не входят во второй знаменатель.</p>}
      <div className="report-breakdown-grid">
        <BreakdownPanel title="Образование" hint="Уровень образования по карточкам" rows={report.education} />
        <BreakdownPanel title="Квалификация" hint="Подтверждённая квалификация по карточкам" rows={report.qualification} />
        <BreakdownPanel title="Обучение в УИС" hint="Записи о пройденном обучении и отсутствии обучения" rows={report.penitentiary_education} />
      </div>
      <p className="report-method">Методика: численность определяется по срокам наказания в карточках; без указанных дат карточки включаются в реестр. Занятым считается осуждённый с договором, действующим на выбранную дату и подписанным всеми тремя сторонами не позже этой даты. Один человек учитывается один раз. Трудоспособность, образование и квалификация берутся из текущих карточек: исторические снимки этих сведений пока не ведутся.</p>
    </>}
  </>;
}
