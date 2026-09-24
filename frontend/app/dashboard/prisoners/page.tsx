"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Pagination } from "@/components/pagination";
import { api } from "@/lib/api";
import { Page, unwrap } from "@/lib/dashboard";
import { mediaPath, Prisoner, Skill } from "@/lib/prisoners";
import { REGISTRY_PAGE_SIZE } from "@/lib/registry";


export default function PrisonersPage() {
  const [prisoners, setPrisoners] = useState<Prisoner[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [query, setQuery] = useState("");
  const [skill, setSkill] = useState("");
  const [education, setEducation] = useState("");
  const [qualification, setQualification] = useState("");
  const [rating, setRating] = useState("");
  const [experience, setExperience] = useState("");
  const [health, setHealth] = useState("");
  const [disability, setDisability] = useState("");
  const [availability, setAvailability] = useState("");
  const [medicalOnly, setMedicalOnly] = useState(false);
  const [disciplineOnly, setDisciplineOnly] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    const task = window.setTimeout(() => {
      api<Skill[]>("/prisoners/skills/")
        .then(setSkills)
        .catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить карточки"));
    }, 0);
    return () => window.clearTimeout(task);
  }, []);

  useEffect(() => {
    const task = window.setTimeout(() => {
      const params = new URLSearchParams({ page: String(page), page_size: String(REGISTRY_PAGE_SIZE) });
      for (const [key, value] of Object.entries({
        search: query.trim(), skill, education: education.trim(),
        qualification: qualification.trim(), rating_min: rating,
        experience_min: experience, health: health.trim(), disability,
      })) if (value) params.set(key, value);
      if (availability) params.set("available", availability === "available" ? "true" : "false");
      if (medicalOnly) params.set("has_medical_restrictions", "true");
      if (disciplineOnly) params.set("has_disciplinary_restrictions", "true");
      api<Page<Prisoner>>(`/prisoners/?${params}`)
        .then((result) => { setPrisoners(unwrap(result)); setTotal(result.count ?? unwrap(result).length); setError(""); })
        .catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить карточки"));
    }, 200);
    return () => window.clearTimeout(task);
  }, [availability, disciplineOnly, disability, education, experience, health, medicalOnly, page, qualification, query, rating, skill]);

  const pageCount = Math.max(1, Math.ceil(total / REGISTRY_PAGE_SIZE));
  const currentPage = Math.min(page, pageCount);
  const rows = prisoners;
  function reset() {
    setQuery(""); setSkill(""); setEducation(""); setQualification(""); setRating("");
    setExperience(""); setHealth(""); setDisability(""); setAvailability("");
    setMedicalOnly(false); setDisciplineOnly(false); setPage(1);
  }

  return <>
    <div className="page-heading"><div><p className="page-kicker">Учёт и подбор</p><h1>Осуждённые</h1><p>Карточки, профессиональные сведения, ограничения и текущая занятость.</p></div></div>
    {error && <p className="error" role="alert">{error}</p>}
    <section className="surface-panel prisoner-registry">
      <div className="panel-heading"><div><h2>Реестр личных дел</h2><p>{total} карточек · по {REGISTRY_PAGE_SIZE} на странице</p></div></div>
      <div className="prisoner-filters">
        <label className="search-control span-2"><span>⌕</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="ФИО, ИИН, навык или опыт" /></label>
        <select value={skill} onChange={(event) => { setSkill(event.target.value); setPage(1); }}><option value="">Все навыки</option>{skills.map((item) => <option key={item.id} value={item.id}>{item.name_ru}</option>)}</select>
        <select value={rating} onChange={(event) => { setRating(event.target.value); setPage(1); }}><option value="">Любой рейтинг</option><option value="5">5 звёзд</option><option value="4">От 4 звёзд</option><option value="3">От 3 звёзд</option></select>
        <input value={education} onChange={(event) => { setEducation(event.target.value); setPage(1); }} placeholder="Образование" />
        <input value={qualification} onChange={(event) => { setQualification(event.target.value); setPage(1); }} placeholder="Квалификация" />
        <select value={experience} onChange={(event) => { setExperience(event.target.value); setPage(1); }}><option value="">Любой стаж</option><option value="3">От 3 лет</option><option value="5">От 5 лет</option><option value="10">От 10 лет</option></select>
        <input value={health} onChange={(event) => { setHealth(event.target.value); setPage(1); }} placeholder="Состояние здоровья" />
        <select value={disability} onChange={(event) => { setDisability(event.target.value); setPage(1); }}><option value="">Любая инвалидность</option><option value="NONE">Нет</option><option value="GROUP_1">I группа</option><option value="GROUP_2">II группа</option><option value="GROUP_3">III группа</option></select>
        <select value={availability} onChange={(event) => { setAvailability(event.target.value); setPage(1); }}><option value="">Любая занятость</option><option value="available">Доступен для трудоустройства</option><option value="busy">Сейчас недоступен</option></select>
        <label className="filter-check"><input type="checkbox" checked={medicalOnly} onChange={(event) => { setMedicalOnly(event.target.checked); setPage(1); }} /> Есть мед. ограничения</label>
        <label className="filter-check"><input type="checkbox" checked={disciplineOnly} onChange={(event) => { setDisciplineOnly(event.target.checked); setPage(1); }} /> Есть дисциплинарные ограничения</label>
        <button className="text-button" type="button" onClick={reset}>Сбросить фильтры</button>
      </div>
      <div className="prisoner-list">
        {rows.map((item) => <Link className="prisoner-card" href={`/prisoners/${item.id}`} key={item.id}>
          <div className="prisoner-photo">{item.photo ? <Image unoptimized width={84} height={104} src={mediaPath(item.photo)} alt={`Фото: ${item.full_name}`} /> : <span>Фото</span>}</div>
          <div className="prisoner-card-main"><div className="prisoner-card-title"><div><strong>{item.full_name}</strong><small>ИИН {item.iin} · ★ {item.rating}</small></div><span className={`status-chip ${item.is_available ? "status-active" : "status-draft"}`}>{item.is_available ? "Доступен" : "Занят"}</span></div>
            <div className="skill-chips">{item.skills.map((row) => <span key={row.id}>{row.name_ru}</span>)}</div>
            <div className="prisoner-summary"><span><small>Образование</small><strong>{item.education || "—"}</strong></span><span><small>Квалификация</small><strong>{item.qualification || "—"}</strong></span><span><small>Опыт / стаж</small><strong>{item.pre_prison_experience || "—"} · {item.total_work_experience_years} лет</strong></span><span><small>Здоровье</small><strong>{item.health_status || "—"}</strong></span><span><small>Текущая занятость</small><strong>{item.current_employment || "—"}</strong></span><span><small>Ограничения</small><strong>{item.medical_restrictions || item.disciplinary_restrictions || "Нет"}</strong></span></div>
          </div><span className="card-arrow">→</span>
        </Link>)}
        {rows.length === 0 && <p className="empty-state">По заданным параметрам карточек нет</p>}
      </div>
      <Pagination page={currentPage} pageCount={pageCount} onChange={setPage} />
    </section>
  </>;
}
