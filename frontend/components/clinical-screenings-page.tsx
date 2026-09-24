"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Pagination } from "@/components/pagination";
import { api } from "@/lib/api";
import { Screening } from "@/lib/applications";
import { formatDate, Page, unwrap } from "@/lib/dashboard";
import { REGISTRY_PAGE_SIZE } from "@/lib/registry";

const resultNames: Record<string, string> = {
  PENDING: "Ожидает заключения",
  APPROVED: "Положительное заключение",
  REJECTED: "Отрицательное заключение",
};

export function ClinicalScreeningsPage({ role }: { role: "MEDIC" | "PSYCHOLOGIST" }) {
  const isMedical = role === "MEDIC";
  const [screenings, setScreenings] = useState<Screening[]>([]);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(REGISTRY_PAGE_SIZE) });
      if (query.trim()) params.set("search", query.trim());
      if (result) params.set("result", result);
      const rows = await api<Page<Screening>>(`/applications/screenings/?${params}`);
      setScreenings(unwrap(rows));
      setTotal(rows.count ?? unwrap(rows).length);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось загрузить назначения");
    }
  }, [page, query, result]);

  useEffect(() => {
    const task = window.setTimeout(() => void load(), query ? 200 : 0);
    return () => window.clearTimeout(task);
  }, [load, query]);

  const pageCount = Math.max(1, Math.ceil(total / REGISTRY_PAGE_SIZE));
  const title = isMedical
    ? "Заявки на медицинское освидетельствование"
    : "Заявки на психологическое обследование";

  return <>
    <div className="page-heading"><div><p className="page-kicker">Назначения</p><h1>{title}</h1><p>Отдельные задания по кандидатам, направленным организацией Еңбек.</p></div></div>
    {error && <p className="error" role="alert">{error}</p>}
    <section className="surface-panel table-panel registry-panel">
      <div className="panel-heading"><div><h2>Реестр обследований</h2><p>{total} назначений · по {REGISTRY_PAGE_SIZE} на странице</p></div></div>
      <div className="filter-bar">
        <label className="search-control"><span>⌕</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Кандидат, организация или место работы" /></label>
        <select aria-label="Результат обследования" value={result} onChange={(event) => { setResult(event.target.value); setPage(1); }}>
          <option value="">Все результаты</option>
          <option value="PENDING">Ожидают заключения</option>
          <option value="APPROVED">Положительные</option>
          <option value="REJECTED">Отрицательные</option>
        </select>
        <button className="text-button" type="button" onClick={() => { setQuery(""); setResult(""); setPage(1); }}>Сбросить</button>
      </div>
      <div className="data-table-wrap registry-table"><table className="data-table"><thead><tr><th>Назначение</th><th>Кандидат</th><th>Организация</th><th>Работа</th><th>Результат</th><th /></tr></thead><tbody>
        {screenings.map((item) => <tr key={item.id}>
          <td><strong>#{item.id.slice(0, 8)}</strong><small>{formatDate(item.created_at)}</small></td>
          <td>{item.prisoner_name}</td>
          <td>{item.organization_name}</td>
          <td><strong>{item.skill_name_ru}</strong><small>{item.workplace_address}</small></td>
          <td><span className={`status-chip status-${item.result.toLowerCase()}`}>{resultNames[item.result] ?? item.result}</span></td>
          <td><Link className="text-button" href={`/applications/screenings/${item.id}`}>{item.result === "PENDING" ? "Оформить заключение" : "Открыть"}</Link></td>
        </tr>)}
        {screenings.length === 0 && <tr><td colSpan={6} className="empty-state">Назначений по заданным фильтрам нет</td></tr>}
      </tbody></table></div>
      <Pagination page={Math.min(page, pageCount)} pageCount={pageCount} onChange={setPage} />
    </section>
  </>;
}
