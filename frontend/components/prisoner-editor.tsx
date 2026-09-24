"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { mediaPath, Prisoner, Skill } from "@/lib/prisoners";

const textFields = [
  "full_name", "iin", "birth_date", "criminal_article", "sentence_term",
  "sentence_start", "sentence_end", "education", "qualification",
  "pre_prison_experience", "pre_prison_experience_years", "penitentiary_education",
  "health_status", "medical_restrictions", "current_employment",
  "total_work_experience_years", "disciplinary_restrictions", "safety_briefing_info",
  "work_capacity", "disability_status", "pension_status", "rating",
] as const;
type Field = typeof textFields[number];
type Values = Record<Field, string>;

function initialValues(prisoner?: Prisoner): Values {
  const defaults: Partial<Values> = {
    rating: "3", work_capacity: "UNKNOWN", disability_status: "NONE",
    pension_status: "NONE", pre_prison_experience_years: "0", total_work_experience_years: "0",
  };
  return Object.fromEntries(textFields.map((field) => [field, String(prisoner?.[field] ?? defaults[field] ?? "")])) as Values;
}

function FieldInput({ label, name, values, onChange, type = "text", required = false, multiline = false, hint }: {
  label: string; name: Field; values: Values; onChange: (name: Field, value: string) => void;
  type?: string; required?: boolean; multiline?: boolean; hint?: string;
}) {
  return <div className={`field ${multiline ? "full" : ""}`}>
    <label htmlFor={`prisoner-${name}`}>{label}{required ? " *" : ""}</label>
    {multiline
      ? <textarea id={`prisoner-${name}`} value={values[name]} onChange={(event) => onChange(name, event.target.value)} rows={3} />
      : <input id={`prisoner-${name}`} type={type} value={values[name]} onChange={(event) => onChange(name, event.target.value)} required={required} min={type === "number" ? (name === "rating" ? 1 : 0) : undefined} max={type === "number" ? (name === "rating" ? 5 : 100) : undefined} inputMode={name === "iin" ? "numeric" : undefined} maxLength={name === "iin" ? 12 : undefined} pattern={name === "iin" ? "[0-9]{12}" : undefined} />}
    {hint && <small>{hint}</small>}
  </div>;
}

export function PrisonerEditor({ prisoner }: { prisoner?: Prisoner }) {
  const router = useRouter();
  const [values, setValues] = useState<Values>(() => initialValues(prisoner));
  const [available, setAvailable] = useState(prisoner?.is_available ?? true);
  const [selectedSkills, setSelectedSkills] = useState<string[]>(() => prisoner?.skills.map((item) => item.id) ?? []);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [photo, setPhoto] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const preview = useMemo(() => photo ? URL.createObjectURL(photo) : (prisoner?.photo ? mediaPath(prisoner.photo) : ""), [photo, prisoner]);

  useEffect(() => {
    api<Skill[]>("/prisoners/skills/").then(setSkills).catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить навыки"));
  }, []);
  useEffect(() => () => { if (photo && preview) URL.revokeObjectURL(preview); }, [photo, preview]);

  function change(name: Field, value: string) {
    setValues((current) => ({ ...current, [name]: name === "iin" ? value.replace(/\D/g, "").slice(0, 12) : value }));
  }

  function selectPhoto(file: File | undefined) {
    setError("");
    if (!file) { setPhoto(null); return; }
    if (!["image/jpeg", "image/png"].includes(file.type) || file.size > 8 * 1024 * 1024) {
      setPhoto(null);
      setError("Загрузите фото JPEG или PNG размером не более 8 МБ");
      return;
    }
    setPhoto(file);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (values.sentence_start && values.sentence_end && values.sentence_end < values.sentence_start) {
      setError("Окончание срока не может быть раньше начала");
      return;
    }
    const body = new FormData();
    for (const field of textFields) body.append(field, values[field]);
    body.set("is_available", String(available));
    body.set("skill_ids", JSON.stringify(selectedSkills));
    if (photo) body.set("photo", photo);
    setSaving(true);
    try {
      const saved = await api<Prisoner>(prisoner ? `/prisoners/${prisoner.id}/` : "/prisoners/", {
        method: prisoner ? "PATCH" : "POST", body,
      });
      router.push(`/prisoners/${saved.id}`);
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось сохранить карточку");
    } finally {
      setSaving(false);
    }
  }

  return <>
    <Link className="back-link" href={prisoner ? `/prisoners/${prisoner.id}` : "/prisoners"}>← {prisoner ? "К личному делу" : "К реестру"}</Link>
    <div className="page-heading"><div><p className="page-kicker">Учёт осуждённых</p><h1>{prisoner ? "Редактирование карточки" : "Новая карточка"}</h1><p>Основные сведения, профессиональные навыки и эталонное фото для биометрии.</p></div></div>
    {error && <p className="error" role="alert">{error}</p>}
    <form className="prisoner-editor" onSubmit={submit}>
      <fieldset className="form-section"><legend>Основные данные</legend><div className="form-grid">
        <FieldInput label="ФИО" name="full_name" values={values} onChange={change} required />
        <FieldInput label="ИИН" name="iin" values={values} onChange={change} required hint="Ровно 12 цифр" />
        <FieldInput label="Дата рождения" name="birth_date" type="date" values={values} onChange={change} required />
        <FieldInput label="Рейтинг" name="rating" type="number" values={values} onChange={change} required />
        <FieldInput label="Статья УК РК" name="criminal_article" values={values} onChange={change} />
        <FieldInput label="Срок наказания" name="sentence_term" values={values} onChange={change} />
        <FieldInput label="Начало срока" name="sentence_start" type="date" values={values} onChange={change} />
        <FieldInput label="Окончание срока" name="sentence_end" type="date" values={values} onChange={change} />
        <div className="field"><label htmlFor="prisoner-work-capacity">Трудоспособность</label><select id="prisoner-work-capacity" value={values.work_capacity} onChange={(event) => change("work_capacity", event.target.value)}><option value="UNKNOWN">Не установлено</option><option value="CAPABLE">Трудоспособен</option><option value="UNABLE">Нетрудоспособен</option></select></div>
        <label className="prisoner-editor-check"><input type="checkbox" checked={available} onChange={(event) => setAvailable(event.target.checked)} /> Доступен для трудоустройства</label>
      </div></fieldset>

      <fieldset className="form-section"><legend>Фото</legend><div className="prisoner-editor-photo">
        <div className="case-photo">{preview ? <Image unoptimized src={preview} width={132} height={166} alt="Эталонное фото" /> : "Нет фото"}</div>
        <div className="field"><label htmlFor="prisoner-photo">{prisoner?.photo ? "Заменить фото" : "Загрузить фото"}</label><input id="prisoner-photo" type="file" accept="image/jpeg,image/png" onChange={(event) => selectPhoto(event.target.files?.[0])} /><small>JPEG или PNG, до 8 МБ. Для биометрического подписания требуется фото лица.</small></div>
      </div></fieldset>

      <fieldset className="form-section"><legend>Образование и трудовой опыт</legend><div className="form-grid">
        <FieldInput label="Образование" name="education" values={values} onChange={change} />
        <FieldInput label="Квалификация" name="qualification" values={values} onChange={change} />
        <FieldInput label="Стаж до заключения, лет" name="pre_prison_experience_years" type="number" values={values} onChange={change} required />
        <FieldInput label="Общий стаж, лет" name="total_work_experience_years" type="number" values={values} onChange={change} required />
        <FieldInput label="Опыт до заключения" name="pre_prison_experience" values={values} onChange={change} multiline />
        <FieldInput label="Образование в УИС" name="penitentiary_education" values={values} onChange={change} multiline />
        <div className="field full"><label>Навыки</label><div className="prisoner-editor-skills">{skills.map((skill) => <label key={skill.id}><input type="checkbox" checked={selectedSkills.includes(skill.id)} onChange={(event) => setSelectedSkills((current) => event.target.checked ? [...current, skill.id] : current.filter((id) => id !== skill.id))} />{skill.name_ru}</label>)}{skills.length === 0 && <small>Навыки не найдены</small>}</div></div>
        <FieldInput label="Текущая занятость" name="current_employment" values={values} onChange={change} />
      </div></fieldset>

      <fieldset className="form-section"><legend>Здоровье и ограничения</legend><div className="form-grid">
        <FieldInput label="Состояние здоровья" name="health_status" values={values} onChange={change} />
        <div className="field"><label htmlFor="prisoner-disability">Инвалидность</label><select id="prisoner-disability" value={values.disability_status} onChange={(event) => change("disability_status", event.target.value)}><option value="NONE">Нет</option><option value="GROUP_1">I группа</option><option value="GROUP_2">II группа</option><option value="GROUP_3">III группа</option></select></div>
        <div className="field"><label htmlFor="prisoner-pension">Пенсионный статус</label><select id="prisoner-pension" value={values.pension_status} onChange={(event) => change("pension_status", event.target.value)}><option value="NONE">Не является пенсионером</option><option value="AGE">По возрасту</option><option value="DISABILITY">По инвалидности</option><option value="OTHER">Иное основание</option></select></div>
        <FieldInput label="Медицинские ограничения" name="medical_restrictions" values={values} onChange={change} multiline />
        <FieldInput label="Дисциплинарные ограничения" name="disciplinary_restrictions" values={values} onChange={change} multiline />
        <FieldInput label="Инструктажи по ТБ" name="safety_briefing_info" values={values} onChange={change} multiline />
      </div></fieldset>
      <div className="prisoner-editor-actions"><Link className="md-button secondary" href={prisoner ? `/prisoners/${prisoner.id}` : "/prisoners"}>Отмена</Link><button className="md-button primary" type="submit" disabled={saving}>{saving ? "Сохранение…" : "Сохранить карточку"}</button></div>
    </form>
  </>;
}
