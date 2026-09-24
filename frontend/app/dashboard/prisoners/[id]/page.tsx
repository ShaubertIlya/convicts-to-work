"use client";

import Image from "next/image";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/dashboard";
import { mediaPath, Prisoner } from "@/lib/prisoners";

function DataRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return <div className="profile-row"><span>{label}</span><strong>{value || value === 0 ? value : "—"}</strong></div>;
}

export default function PrisonerCasePage() {
  const { id } = useParams<{ id: string }>();
  const [prisoner, setPrisoner] = useState<Prisoner | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const task = window.setTimeout(() => {
      api<Prisoner>(`/prisoners/${id}/`).then(setPrisoner)
        .catch((reason) => setError(reason instanceof Error ? reason.message : "Личное дело не найдено"));
    }, 0);
    return () => window.clearTimeout(task);
  }, [id]);

  if (error) return <><Link className="back-link" href="/prisoners">← К реестру</Link><p className="error">{error}</p></>;
  if (!prisoner) return <div className="portal-loading inline"><span className="loader" />Загрузка личного дела…</div>;

  return <>
    <div className="prisoner-case-actions"><Link className="back-link" href="/prisoners">← К реестру осуждённых</Link><Link className="md-button secondary" href={`/prisoners/${prisoner.id}/edit`}>Редактировать</Link></div>
    <div className="case-header surface-panel">
      <div className="case-photo">{prisoner.photo ? <Image unoptimized width={132} height={166} src={mediaPath(prisoner.photo)} alt={`Фото: ${prisoner.full_name}`} /> : "Фото"}</div>
      <div><p className="page-kicker">Личное дело</p><h1>{prisoner.full_name}</h1><p>ИИН {prisoner.iin} · Дата рождения {formatDate(prisoner.birth_date)}</p><div className="skill-chips">{prisoner.skills.map((item) => <span key={item.id}>{item.name_ru}</span>)}</div></div>
      <div className="case-status"><strong>★ {prisoner.rating}</strong><span className={`status-chip ${prisoner.is_available ? "status-active" : "status-draft"}`}>{prisoner.is_available ? "Доступен" : "Недоступен"}</span>{prisoner.has_active_contracts && <small>Есть действующий договор</small>}</div>
    </div>
    <div className="case-grid">
      <section className="surface-panel"><div className="panel-heading"><div><h2>Основные данные</h2><p>Отбывание наказания</p></div></div><DataRow label="Статья УК РК" value={prisoner.criminal_article} /><DataRow label="Срок наказания" value={prisoner.sentence_term} /><DataRow label="Начало срока" value={formatDate(prisoner.sentence_start || "")} /><DataRow label="Окончание срока" value={formatDate(prisoner.sentence_end || "")} /></section>
      <section className="surface-panel"><div className="panel-heading"><div><h2>Образование и квалификация</h2><p>Профессиональная подготовка</p></div></div><DataRow label="Образование" value={prisoner.education} /><DataRow label="Квалификация" value={prisoner.qualification} /><DataRow label="Обучение в УИС" value={prisoner.penitentiary_education} /><DataRow label="Навыки" value={prisoner.skills.map((item) => item.name_ru).join(", ")} /></section>
      <section className="surface-panel"><div className="panel-heading"><div><h2>Трудовой опыт</h2><p>До и во время заключения</p></div></div><DataRow label="Опыт до заключения" value={prisoner.pre_prison_experience} /><DataRow label="Стаж до заключения" value={`${prisoner.pre_prison_experience_years} лет`} /><DataRow label="Общий стаж" value={`${prisoner.total_work_experience_years} лет`} /><DataRow label="Текущая занятость" value={prisoner.current_employment} /></section>
      <section className="surface-panel"><div className="panel-heading"><div><h2>Здоровье и ограничения</h2><p>Сведения для допуска к работам</p></div></div><DataRow label="Состояние здоровья" value={prisoner.health_status} /><DataRow label="Трудоспособность" value={prisoner.work_capacity_label} /><DataRow label="Инвалидность" value={prisoner.disability_status_label} /><DataRow label="Мед. ограничения" value={prisoner.medical_restrictions || "Нет"} /><DataRow label="Пенсионный статус" value={prisoner.pension_status_label} /></section>
      <section className="surface-panel"><div className="panel-heading"><div><h2>Безопасность и дисциплина</h2><p>Допуски и ограничения</p></div></div><DataRow label="Дисциплинарные ограничения" value={prisoner.disciplinary_restrictions || "Нет"} /><DataRow label="Инструктажи по ТБ" value={prisoner.safety_briefing_info} /></section>
      <section className="surface-panel history-panel"><div className="panel-heading"><div><h2>История изменений</h2><p>Квалификация, здоровье и занятость</p></div></div><div className="history-list">{prisoner.change_history.map((item) => <article key={item.id}><time>{formatDate(item.effective_date)}</time><div><strong>{item.change_type_label}</strong><p><span>{item.previous_value || "—"}</span> → {item.new_value}</p><small>{item.note}</small></div></article>)}{prisoner.change_history.length === 0 && <p className="empty-state">Изменений пока нет</p>}</div></section>
    </div>
  </>;
}
