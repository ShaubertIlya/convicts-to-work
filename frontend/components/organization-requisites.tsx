import { OrganizationDetails } from "@/lib/dashboard";

function RequisiteRows({ organization }: { organization: OrganizationDetails }) {
  return <>
      <span>Наименование / БИН</span>
      <strong>{organization.name || "—"} · {organization.bin || "—"}</strong>
      <span>Вид деятельности</span>
      <strong>{organization.activity_type || "—"}</strong>
      <span>Штат</span>
      <strong>{organization.staff_count || "—"}</strong>
      <span>ОКЭД</span>
      <strong>{organization.oked.code} · {organization.oked.name_ru || "—"}</strong>
      <span>Банк / БИК</span>
      <strong>{organization.bank ? `${organization.bank.name_ru} · ${organization.bank.bik}` : "—"}</strong>
      <span>КБЕ / ИИК</span>
      <strong>{organization.kbe || "—"} · {organization.iik || "—"}</strong>
      <span>Адреса</span>
      <strong>{organization.legal_address || "—"} / {organization.actual_address || "—"}</strong>
      <span>Руководитель</span>
      <strong>{organization.director.full_name || "—"} · {organization.director.position || "—"}</strong>
      <span>Контакты руководителя</span>
      <strong>{organization.director.email || "—"} · {organization.director.phone || "—"}</strong>
      <span>Лицензии и разрешения</span>
      <strong>{organization.licenses || "Не указаны"}</strong>
  </>;
}

export function OrganizationRequisites({ organization, expanded = false }: { organization: OrganizationDetails; expanded?: boolean }) {
  if (expanded) return <div className="requisites-full"><RequisiteRows organization={organization} /></div>;
  return <details className="requisites">
    <summary>Реквизиты</summary>
    <div>
      <RequisiteRows organization={organization} />
    </div>
  </details>;
}
