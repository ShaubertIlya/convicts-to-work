"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useDashboardUser } from "@/components/dashboard-user";
import { ScreeningReviewForm } from "@/components/screening-review-form";
import { api } from "@/lib/api";
import { Screening } from "@/lib/applications";
import { formatDate } from "@/lib/dashboard";
import { mediaPath } from "@/lib/prisoners";

const resultNames: Record<string, string> = {
  PENDING: "Ожидает заключения",
  APPROVED: "Положительное заключение",
  REJECTED: "Отрицательное заключение",
};

export default function ClinicalScreeningDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const user = useDashboardUser();
  const [screening, setScreening] = useState<Screening | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const row = await api<Screening>(`/applications/screenings/${id}/`);
      setScreening(row);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Назначение не найдено");
    }
  }, [id]);

  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(task);
  }, [load]);

  if (!screening) return <><Link className="back-link" href="/applications">← К назначениям</Link>{error ? <p className="error" role="alert">{error}</p> : <div className="portal-loading inline"><span className="loader" />Загрузка назначения…</div>}</>;

  const kindName = user.role === "MEDIC" ? "Медицинское освидетельствование" : "Психологическое обследование";

  return <>
    <Link className="back-link" href="/applications">← К назначениям</Link>
    <div className="page-heading application-heading"><div><p className="page-kicker">Назначение #{screening.id.slice(0, 8)}</p><h1>{kindName}</h1><p>{screening.prisoner_name} · назначено {formatDate(screening.created_at)}</p></div><span className={`status-chip status-${screening.result.toLowerCase()}`}>{resultNames[screening.result] ?? screening.result}</span></div>
    {error && <p className="error" role="alert">{error}</p>}
    <section className="surface-panel application-overview">
      <div><small>Кандидат</small><strong>{screening.prisoner_name}</strong></div>
      <div><small>Организация</small><strong>{screening.organization_name}</strong></div>
      <div><small>Специальность</small><strong>{screening.skill_name_ru}</strong></div>
      <div><small>Место работы</small><strong>{screening.workplace_address}</strong></div>
      <div><small>График</small><strong>{screening.schedule}</strong></div>
    </section>
    {screening.result === "PENDING" ? <section className="surface-panel screening-panel"><div className="panel-heading"><div><h2>Заключение</h2><p>Укажите решение, комментарий и приложите PDF.</p></div></div><ScreeningReviewForm screening={screening} onReviewed={load} /></section> : <section className="surface-panel screening-panel"><div className="panel-heading"><div><h2>Заключение</h2><p>Решение по обследованию зафиксировано.</p></div></div><div className="application-overview"><div><small>Результат</small><strong>{resultNames[screening.result] ?? screening.result}</strong></div><div><small>Специалист</small><strong>{screening.reviewer_name || "—"}</strong></div><div><small>Дата</small><strong>{screening.reviewed_at ? formatDate(screening.reviewed_at) : "—"}</strong></div><div className="span-2"><small>Комментарий</small><strong>{screening.comment || "—"}</strong></div>{screening.conclusion_document && <div className="span-2"><a className="text-button" href={mediaPath(screening.conclusion_document)} target="_blank" rel="noreferrer">Открыть заключение PDF →</a></div>}</div></section>}
  </>;
}
