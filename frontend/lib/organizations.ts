export type Organization = {
  id: string;
  name: string;
  kind: "BUSINESS" | "ENBEK";
  bin: string;
  activity_type: string;
  staff_count: number;
  legal_address: string;
  actual_address: string;
  oked_code: string;
  oked_name_ru: string;
  bank_name: string | null;
  bik: string | null;
  kbe: string;
  iik: string;
  licenses: string;
  director_full_name: string;
  director_iin: string;
  director_position: string;
  director_email: string;
  director_phone: string;
  users_count: number;
  applications_count: number;
  contracts_count: number;
  created_at: string;
};

export type PlatformUser = {
  id: number;
  email: string;
  full_name: string;
  role: string;
  organization: string;
  organization_name: string;
  organization_kind: "BUSINESS" | "ENBEK";
  is_active: boolean;
  date_joined: string;
};
