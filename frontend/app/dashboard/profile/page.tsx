"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Page, unwrap } from "@/lib/dashboard";

type Organization = {
  id: string; name: string; bin: string; activity_type: string; staff_count: number;
  legal_address: string; actual_address: string; oked_code: string; oked_name_ru: string;
  bank_name: string | null; bik: string | null; kbe: string; iik: string; licenses: string;
  director_full_name: string; director_iin: string; director_position: string;
  director_email: string; director_phone: string;
};

function DataRow({ label, value }: { label: string; value: string | number | null }) {
  return <div className="profile-row"><span>{label}</span><strong>{value || "—"}</strong></div>;
}

export default function ProfilePage() {
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Page<Organization>>("/organizations/")
      .then((rows) => setOrganization(unwrap(rows)[0] ?? null))
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить профиль"));
  }, []);

  return <>
    <div className="page-heading"><div><p className="page-kicker">Карточка юридического лица</p><h1>Профиль организации</h1><p>Актуальные сведения, используемые в новых заявках и договорах.</p></div></div>
    {error && <p className="error">{error}</p>}
    {!organization ? <section className="surface-panel"><p className="empty-state">Загрузка профиля…</p></section> : <div className="profile-grid">
      <section className="surface-panel"><div className="panel-heading"><div><h2>Юридическое лицо</h2><p>Регистрационные сведения</p></div></div><DataRow label="Наименование" value={organization.name} /><DataRow label="БИН" value={organization.bin} /><DataRow label="Вид деятельности" value={organization.activity_type} /><DataRow label="Штат" value={organization.staff_count} /><DataRow label="ОКЭД" value={`${organization.oked_code} · ${organization.oked_name_ru}`} /><DataRow label="Юридический адрес" value={organization.legal_address} /><DataRow label="Фактический адрес" value={organization.actual_address} /></section>
      <section className="surface-panel"><div className="panel-heading"><div><h2>Банковские реквизиты</h2><p>Структурированные данные</p></div></div><DataRow label="Банк" value={organization.bank_name} /><DataRow label="БИК" value={organization.bik} /><DataRow label="КБЕ" value={organization.kbe} /><DataRow label="ИИК" value={organization.iik} /></section>
      <section className="surface-panel"><div className="panel-heading"><div><h2>Первый руководитель</h2><p>Представитель организации</p></div></div><DataRow label="ФИО" value={organization.director_full_name} /><DataRow label="ИИН" value={organization.director_iin} /><DataRow label="Должность" value={organization.director_position} /><DataRow label="Email" value={organization.director_email} /><DataRow label="Телефон" value={organization.director_phone} /></section>
      <section className="surface-panel"><div className="panel-heading"><div><h2>Лицензии и разрешения</h2><p>Дополнительные сведения</p></div></div><p className="profile-text">{organization.licenses || "Не указаны"}</p></section>
    </div>}
  </>;
}
