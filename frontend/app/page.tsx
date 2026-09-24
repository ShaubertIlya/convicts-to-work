"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Stats = { total_available: number; by_skill: { id: string; name_ru: string; name_kk: string; count: number }[] };

const copy = {
  ru: {
    about: "О платформе", benefits: "Преимущества", how: "Как это работает", login: "Войти", cabinet: "Личный кабинет",
    start: "Подать заявку", eyebrow: "Цифровая платформа трудовых отношений",
    title: "Работа, которая создаёт новые возможности",
    lead: "Единый прозрачный процесс для бизнеса и РГП «Еңбек»: от заявки на работников до подписанного трудового договора.",
    available: "доступных кандидатов", skills: "По специальностям", why: "Почему это удобно",
    cards: [
      ["Прозрачный процесс", "Статус заявки и каждого кандидата виден на всех этапах."],
      ["Проверенные кандидаты", "Медицинское и психологическое заключения проходят в системе."],
      ["Один цифровой маршрут", "Заявка, подбор, согласование и договор связаны между собой."],
    ],
    steps: "Четыре шага до договора",
    flow: ["Компания регистрируется и подаёт заявку", "Еңбек подбирает кандидатов", "Кандидаты проходят два обследования", "Стороны подписывают договор"],
  },
  kk: {
    about: "Платформа туралы", benefits: "Артықшылықтар", how: "Бұл қалай жұмыс істейді", login: "Кіру", cabinet: "Жеке кабинет",
    start: "Өтінім беру", eyebrow: "Цифрлық еңбек қатынастары платформасы",
    title: "Жаңа мүмкіндіктер ашатын жұмыс",
    lead: "Бизнес пен «Еңбек» РМК үшін бірыңғай ашық үдеріс: жұмысшыларға өтінімнен еңбек шартына дейін.",
    available: "қолжетімді үміткер", skills: "Мамандықтар бойынша", why: "Неліктен ыңғайлы",
    cards: [
      ["Ашық үдеріс", "Өтінім мен әр үміткердің мәртебесі барлық кезеңде көрінеді."],
      ["Тексерілген үміткерлер", "Медициналық және психологиялық қорытынды жүйеде өтеді."],
      ["Бірыңғай цифрлық бағыт", "Өтінім, іріктеу, келісу және шарт өзара байланысқан."],
    ],
    steps: "Шартқа дейінгі төрт қадам",
    flow: ["Компания тіркеліп, өтінім береді", "Еңбек үміткерлерді іріктейді", "Үміткерлер екі тексеруден өтеді", "Тараптар шартқа қол қояды"],
  },
};

export default function Home() {
  const [lang, setLang] = useState<"ru" | "kk">("ru");
  const [stats, setStats] = useState<Stats>({ total_available: 0, by_skill: [] });
  const [authenticated, setAuthenticated] = useState(false);
  const t = copy[lang];
  const applicationHref = authenticated ? "/dashboard#new-application" : "/login";
  useEffect(() => {
    api<Stats>("/public/stats/").then(setStats).catch(() => undefined);
    api("/auth/me/").then(() => setAuthenticated(true)).catch(() => setAuthenticated(false));
  }, []);
  return <>
    <header className="topbar"><div className="container nav">
      <Link className="brand" href="/"><span className="mark">E</span> Еңбек</Link>
      <nav className="links"><a href="#about">{t.about}</a><a href="#benefits">{t.benefits}</a><a href="#how">{t.how}</a></nav>
      <div className="actions"><button className="button ghost small" onClick={() => setLang(lang === "ru" ? "kk" : "ru")}>{lang === "ru" ? "ҚАЗ" : "РУС"}</button><Link className="button ghost small" href={authenticated ? "/dashboard" : "/login"}>{authenticated ? t.cabinet : t.login}</Link><Link className="button small" href={applicationHref}>{t.start}</Link></div>
    </div></header>
    <main>
      <section className="hero" id="about"><div className="container hero-grid">
        <div><div className="eyebrow">{t.eyebrow}</div><h1>{t.title}</h1><p className="lead">{t.lead}</p><div className="actions"><Link className="button" href={applicationHref}>{t.start}</Link><a className="button secondary" href="#how">{t.how}</a></div></div>
        <div className="hero-card"><div className="eyebrow">{t.skills}</div><div className="metric">{stats.total_available}</div><p>{t.available}</p>{stats.by_skill.slice(0, 5).map((item) => <div className="skill-row" key={item.id}><span>{lang === "ru" ? item.name_ru : item.name_kk}</span><strong>{item.count}</strong></div>)}</div>
      </div></section>
      <section className="section white" id="benefits"><div className="container"><div className="eyebrow">Еңбек</div><h2>{t.why}</h2><div className="grid-3">{t.cards.map(([title, body], index) => <article className="card" key={title}><div className="step">0{index + 1}</div><h3>{title}</h3><p className="muted">{body}</p></article>)}</div></div></section>
      <section className="section" id="how"><div className="container"><h2>{t.steps}</h2><div className="grid-3">{t.flow.map((step, index) => <article className="card" key={step}><div className="step">{index + 1}</div><h3>{step}</h3></article>)}</div></div></section>
    </main>
    <footer className="footer"><div className="container">© 2026 Еңбек · Цифровая платформа трудовых отношений</div></footer>
  </>;
}
