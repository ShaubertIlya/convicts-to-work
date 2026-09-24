import { OrganizationDetails } from "@/lib/dashboard";
import { Prisoner, Skill } from "@/lib/prisoners";

export type CandidatePrisoner = Partial<Prisoner> & {
  id: string;
  rating: number;
  skills: Skill[];
  photo?: string;
};

export type Candidate = {
  id: string;
  status: string;
  prisoner: CandidatePrisoner;
  screenings: Screening[];
};

export type Application = {
  id: string;
  status: string;
  quantity: number;
  skill: string;
  skill_name_ru: string;
  skill_name_kk: string;
  skill_requirement: string;
  organization_name: string;
  organization_details: OrganizationDetails;
  workplace_address: string;
  salary: string;
  schedule: string;
  employment_type: string;
  activity_description: string;
  duration_months: number;
  candidates: Candidate[];
  business_comment: string;
  enbek_comment: string;
  created_at: string;
  updated_at: string;
};

export type Screening = {
  id: string;
  application_id: string;
  prisoner_name: string;
  organization_name: string;
  skill_name_ru: string;
  workplace_address: string;
  schedule: string;
  kind: string;
  result: string;
  comment: string;
  conclusion_document: string | null;
  conclusion_file_name: string;
  reviewer_name?: string;
  reviewed_at: string | null;
  created_at: string;
};

export const applicationStatuses = [
  "DRAFT", "SUBMITTED", "PROPOSED", "BUSINESS_RESPONDED", "APPROVED", "SCREENING",
  "CONTRACTING", "COMPLETED", "REJECTED_BUSINESS", "REJECTED_ENBEK", "WITHDRAWN",
];
