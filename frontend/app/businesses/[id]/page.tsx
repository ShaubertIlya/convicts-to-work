"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/dashboard";
import { Organization } from "@/lib/organizations";

function DataRow({ label, value }: { label: string; value: string | number | null }) {
  return <div className="profile-row"><span>{label}</span><strong>{value || "—"}</strong></div>;
}

export default function BusinessDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Organization>(`/organizations/${id}/`).then(setOrganization)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Организация не найдена"));
  }, [id]);

  if (!organization) return <><Link className="back-link" href="/businesses">← К организациям МСБ</Link>{error ? <p className="error">{error}</p> : <div className="portal-loading inline"><span className="loader" />Загрузка организации…</div>}</>;

  return <>
    <Link className="back-link" href="/businesses">← К организациям МСБ</Link>
    <div className="page-heading"><div><p className="page-kicker">Карточка МСБ · зарегистрирована {formatDate(organization.created_at)}</p><h1>{organization.name}</h1><p>БИН {organization.bin} · пользователей {organization.users_count}</p></div></div>
    <section className="business-metrics"><article><small>Штат</small><strong>{organization.staff_count}</strong></article><article><small>Заявки</small><strong>{organization.applications_count}</strong></article><article><small>Договоры</small><strong>{organization.contracts_count}</strong></article></section>
    <div className="profile-grid">
      <section className="surface-panel"><div className="panel-heading"><div><h2>Юридическое лицо</h2><p>Регистрационные сведения</p></div></div><DataRow label="Наименование" value={organization.name} /><DataRow label="БИН" value={organization.bin} /><DataRow label="Деятельность" value={organization.activity_type} /><DataRow label="ОКЭД" value={`${organization.oked_code} · ${organization.oked_name_ru}`} /><DataRow label="Юридический адрес" value={organization.legal_address} /><DataRow label="Фактический адрес" value={organization.actual_address} /></section>
      <section className="surface-panel"><div className="panel-heading"><div><h2>Банковские реквизиты</h2><p>Актуальные данные организации</p></div></div><DataRow label="Банк" value={organization.bank_name} /><DataRow label="БИК" value={organization.bik} /><DataRow label="КБЕ" value={organization.kbe} /><DataRow label="ИИК" value={organization.iik} /></section>
      <section className="surface-panel"><div className="panel-heading"><div><h2>Первый руководитель</h2><p>Контактное лицо</p></div></div><DataRow label="ФИО" value={organization.director_full_name} /><DataRow label="ИИН" value={organization.director_iin} /><DataRow label="Должность" value={organization.director_position} /><DataRow label="Email" value={organization.director_email} /><DataRow label="Телефон" value={organization.director_phone} /></section>
      <section className="surface-panel"><div className="panel-heading"><div><h2>Лицензии и разрешения</h2><p>Дополнительные сведения</p></div></div><p className="profile-text">{organization.licenses || "Не указаны"}</p></section>
    </div>
  </>;
}
