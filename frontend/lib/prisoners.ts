export type Skill = { id: string; name_ru: string; name_kk: string };

export type PrisonerHistory = {
  id: string;
  change_type: string;
  change_type_label: string;
  effective_date: string;
  previous_value: string;
  new_value: string;
  note: string;
};

export type Prisoner = {
  id: string;
  full_name: string;
  iin: string;
  birth_date: string;
  photo?: string;
  rating: number;
  is_available: boolean;
  work_capacity: "UNKNOWN" | "CAPABLE" | "UNABLE";
  work_capacity_label: string;
  criminal_article: string;
  sentence_term: string;
  sentence_start: string | null;
  sentence_end: string | null;
  education: string;
  qualification: string;
  pre_prison_experience: string;
  pre_prison_experience_years: number;
  penitentiary_education: string;
  health_status: string;
  disability_status: string;
  disability_status_label: string;
  medical_restrictions: string;
  current_employment: string;
  total_work_experience_years: number;
  pension_status: string;
  pension_status_label: string;
  disciplinary_restrictions: string;
  safety_briefing_info: string;
  skills: Skill[];
  has_active_contracts: boolean;
  change_history: PrisonerHistory[];
};

export const mediaPath = (value: string) => {
  try {
    const parsed = new URL(value);
    const path = `${parsed.pathname}${parsed.search}`;
    return parsed.hostname === "storage" ? `/storage${path}` : path;
  }
  catch { return value; }
};
