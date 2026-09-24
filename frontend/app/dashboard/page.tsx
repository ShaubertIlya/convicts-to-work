"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useDashboardUser } from "@/components/dashboard-user";
import { api } from "@/lib/api";
import { Screening } from "@/lib/applications";
import { Page, statusNames, unwrap } from "@/lib/dashboard";

type Application = { id: string; status: string; skill_name_ru: string; created_at: string };
type Contract = { id: string; status: string; number: string; created_at: string };
type Notification = { id: string; title_ru: string; read_at: string | null; created_at: string };

export default function DashboardOverview() {
  const user = useDashboardUser();
  const isClinicalRole = user.role === "MEDIC" || user.role === "PSYCHOLOGIST";
  const [applications, setApplications] = useState<Application[]>([]);
  const [screenings, setScreenings] = useState<Screening[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [applicationCount, setApplicationCount] = useState(0);
  const [pendingScreeningCount, setPendingScreeningCount] = useState(0);
  const [contractCount, setContractCount] = useState(0);

  useEffect(() => {
    if (isClinicalRole) {
      api<Page<Screening>>("/applications/screenings/?page_size=5")
        .then((value) => setScreenings(unwrap(value)))
        .catch(() => undefined);
      api<Page<Screening>>("/applications/screenings/?result=PENDING&page_size=1")
        .then((value) => setPendingScreeningCount(value.count ?? unwrap(value).length))
        .catch(() => undefined);
    } else {
      api<Page<Application>>("/applications/").then((value) => {
        const rows = unwrap(value);
        setApplications(rows);
        setApplicationCount(Array.isArray(value) ? rows.length : (value.count ?? rows.length));
      }).catch(() => undefined);
    }
    api<Page<Notification>>("/notifications/")
      .then((value) => setNotifications(unwrap(value)))
      .catch(() => undefined);
    if (!isClinicalRole) api<Page<Contract>>("/contracts/").then((value) => {
      const rows = unwrap(value);
      setContractCount(Array.isArray(value) ? rows.length : (value.count ?? rows.length));
    }).catch(() => undefined);
  }, [isClinicalRole]);

  return <>
    <div className="page-heading">
      <div><p className="page-kicker">Личный кабинет</p><h1>Добро пожаловать, {user.full_name.split(" ")[0]}</h1><p>Краткая сводка по текущим процессам организации.</p></div>
      {user.role === "BUSINESS_ADMIN" && <Link className="md-button primary" href="/applications#new-application">+ Новая заявка</Link>}
    </div>

    <section className="metric-grid">
      <Link className="metric-card" href="/applications"><span className="metric-icon blue">▤</span><div><small>{isClinicalRole ? "Ожидают заключения" : "Всего заявок"}</small><strong>{isClinicalRole ? pendingScreeningCount : applicationCount}</strong></div></Link>
      {!isClinicalRole && <Link className="metric-card" href="/contracts"><span className="metric-icon cyan">▥</span><div><small>Договоров</small><strong>{contractCount}</strong></div></Link>}
      <article className="metric-card"><span className="metric-icon amber">●</span><div><small>Новые уведомления</small><strong>{notifications.filter((item) => !item.read_at).length}</strong></div></article>
    </section>

    <div className="overview-grid">
      <section className="surface-panel">
        <div className="panel-heading"><div><h2>{isClinicalRole ? "Последние назначения" : "Последние заявки"}</h2><p>Актуальные статусы обработки</p></div><Link href="/applications">Все {isClinicalRole ? "назначения" : "заявки"} →</Link></div>
        <div className="compact-list">{isClinicalRole ? <>{screenings.map((item) => <Link href={`/applications/screenings/${item.id}`} key={item.id}><span className="list-symbol">▤</span><div><strong>{item.prisoner_name}</strong><small>{item.kind === "MEDICAL" ? "Медицинское освидетельствование" : "Психологическое обследование"}</small></div><span className={`status-chip status-${item.result.toLowerCase()}`}>{item.result === "PENDING" ? "Ожидает" : item.result === "APPROVED" ? "Согласовано" : "Отклонено"}</span></Link>)}{screenings.length === 0 && <p className="empty-state">Назначений пока нет</p>}</> : <>{applications.slice(0, 5).map((item) => <div key={item.id}><span className="list-symbol">▤</span><div><strong>{item.skill_name_ru}</strong><small>Заявка #{item.id.slice(0, 8)}</small></div><span className={`status-chip status-${item.status.toLowerCase()}`}>{statusNames[item.status] ?? item.status}</span></div>)}{applications.length === 0 && <p className="empty-state">Заявок пока нет</p>}</>}</div>
      </section>
      <section className="surface-panel">
        <div className="panel-heading"><div><h2>Уведомления</h2><p>Последние события системы</p></div></div>
        <div className="compact-list">{notifications.slice(0, 5).map((item) => <div key={item.id}><span className="list-symbol">●</span><div><strong>{item.title_ru}</strong><small>{item.read_at ? "Прочитано" : "Новое"}</small></div></div>)}{notifications.length === 0 && <p className="empty-state">Новых событий нет</p>}</div>
      </section>
    </div>
  </>;
}
