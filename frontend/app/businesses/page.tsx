"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useDashboardUser } from "@/components/dashboard-user";
import { Pagination } from "@/components/pagination";
import { api } from "@/lib/api";
import { formatDate, Page } from "@/lib/dashboard";
import { Organization } from "@/lib/organizations";
import { REGISTRY_PAGE_SIZE } from "@/lib/registry";


export default function BusinessesPage() {
  const user = useDashboardUser();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [count, setCount] = useState(0);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const params = new URLSearchParams({ kind: "BUSINESS", ordering: "name", page: String(page), page_size: String(REGISTRY_PAGE_SIZE) });
    if (query.trim()) params.set("search", query.trim());
    try {
      const result = await api<Page<Organization>>(`/organizations/?${params}`);
      setOrganizations(result.results);
      setCount(result.count ?? result.results.length);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось загрузить организации");
    }
  }, [page, query]);

  useEffect(() => {
    const task = window.setTimeout(() => void load(), 250);
    return () => window.clearTimeout(task);
  }, [load]);

  if (user.role === "BUSINESS_ADMIN") return <p className="error">Раздел доступен только сотрудникам Еңбек.</p>;
  const pageCount = Math.max(1, Math.ceil(count / REGISTRY_PAGE_SIZE));

  return <>
    <div className="page-heading"><div><p className="page-kicker">Контрагенты платформы</p><h1>Организации МСБ</h1><p>Зарегистрированные компании и их участие в трудоустройстве.</p></div></div>
    {error && <p className="error" role="alert">{error}</p>}
    <section className="surface-panel table-panel registry-panel">
      <div className="panel-heading"><div><h2>Реестр организаций</h2><p>{count} зарегистрированных МСБ · по {REGISTRY_PAGE_SIZE} на странице</p></div></div>
      <div className="filter-bar"><label className="search-control"><span>⌕</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Название, БИН, ОКЭД, руководитель или деятельность" /></label><button className="text-button" type="button" onClick={() => { setQuery(""); setPage(1); }}>Сбросить</button></div>
      <div className="data-table-wrap registry-table"><table className="data-table"><thead><tr><th>Организация</th><th>Деятельность</th><th>Руководитель</th><th>Штат</th><th>Заявки</th><th>Договоры</th><th /></tr></thead><tbody>
        {organizations.map((organization) => <tr key={organization.id}><td><strong>{organization.name}</strong><small>БИН {organization.bin} · с {formatDate(organization.created_at)}</small></td><td><strong>{organization.activity_type}</strong><small>ОКЭД {organization.oked_code} · {organization.oked_name_ru}</small></td><td><strong>{organization.director_full_name}</strong><small>{organization.director_position}</small></td><td>{organization.staff_count}</td><td>{organization.applications_count}</td><td>{organization.contracts_count}</td><td><Link className="text-button" href={`/businesses/${organization.id}`}>Открыть</Link></td></tr>)}
        {organizations.length === 0 && <tr><td colSpan={7} className="empty-state">Организации не найдены</td></tr>}
      </tbody></table></div>
      <Pagination page={page} pageCount={pageCount} onChange={setPage} />
    </section>
  </>;
}
