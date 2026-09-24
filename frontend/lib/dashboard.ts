export type User = {
  id: number;
  full_name: string;
  role: string;
  organization: string;
  organization_name: string;
};

export type Page<T> = {
  count?: number;
  next?: string | null;
  previous?: string | null;
  results: T[];
};

export type OrganizationDetails = {
  name: string;
  bin: string;
  activity_type: string;
  staff_count: number;
  legal_address: string;
  actual_address: string;
  oked: { code: string; name_ru: string; name_kk: string };
  bank: { name_ru: string; name_kk: string; bik: string; bank_code: string } | null;
  kbe: string;
  iik: string;
  licenses: string;
  director: {
    full_name: string;
    iin: string;
    position: string;
    email: string;
    phone: string;
  };
};

export const roleNames: Record<string, string> = {
  BUSINESS_ADMIN: "Администратор МСБ",
  ENBEK_ADMIN: "Администратор Еңбек",
  ENBEK_MANAGER: "Руководитель Еңбек",
  ENBEK_EXECUTOR: "Исполнитель Еңбек",
  MEDIC: "Медик",
  PSYCHOLOGIST: "Психолог",
};

export const statusNames: Record<string, string> = {
  DRAFT: "Черновик",
  SUBMITTED: "Подана",
  PROPOSED: "Кандидаты предложены",
  BUSINESS_RESPONDED: "Ответ МСБ получен",
  APPROVED: "Согласована",
  REJECTED_BUSINESS: "Отклонена МСБ",
  REJECTED_ENBEK: "Отклонена Еңбек",
  SCREENING: "Обследование",
  CONTRACTING: "Договоры",
  COMPLETED: "Завершена",
  WITHDRAWN: "Отозвана",
  AWAITING_PRISONER: "Ожидает осуждённого",
  PARTIALLY_SIGNED: "Подписан частично",
  ACTIVE: "Действующий",
  EXPIRED: "Истёк",
};

export const unwrap = <T,>(value: T[] | Page<T>) => Array.isArray(value) ? value : value.results;

export function formatDate(value: string) {
  return value ? new Intl.DateTimeFormat("ru-RU").format(new Date(value)) : "—";
}

export function formatMoney(value: string | number) {
  return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(Number(value));
}
