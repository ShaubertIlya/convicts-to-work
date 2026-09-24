"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useDashboardUser } from "@/components/dashboard-user";
import { Pagination } from "@/components/pagination";
import { api } from "@/lib/api";
import { formatDate, Page, roleNames, unwrap } from "@/lib/dashboard";
import { Organization, PlatformUser } from "@/lib/organizations";
import { REGISTRY_PAGE_SIZE } from "@/lib/registry";

const roles = ["BUSINESS_ADMIN", "ENBEK_ADMIN", "ENBEK_MANAGER", "ENBEK_EXECUTOR", "MEDIC", "PSYCHOLOGIST"];

export default function AdministrationPage() {
  const currentUser = useDashboardUser();
  const [users, setUsers] = useState<PlatformUser[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [editing, setEditing] = useState<PlatformUser | null>(null);
  const [count, setCount] = useState(0);
  const [query, setQuery] = useState("");
  const [role, setRole] = useState("");
  const [active, setActive] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(async () => {
    const params = new URLSearchParams({ page: String(page), page_size: String(REGISTRY_PAGE_SIZE), ordering: "full_name" });
    if (query.trim()) params.set("search", query.trim());
    if (role) params.set("role", role);
    if (active) params.set("is_active", active);
    try {
      const result = await api<Page<PlatformUser>>(`/auth/users/?${params}`);
      setUsers(result.results);
      setCount(result.count ?? result.results.length);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось загрузить пользователей");
    }
  }, [active, page, query, role]);

  useEffect(() => {
    if (currentUser.role !== "ENBEK_ADMIN") return;
    let cancelled = false;
    async function loadOrganizations() {
      const all: Organization[] = [];
      let page = 1;
      while (true) {
        const result = await api<Page<Organization>>(`/organizations/?ordering=name&page_size=50&page=${page}`);
        all.push(...unwrap(result));
        if (!result.next) break;
        page += 1;
      }
      if (!cancelled) setOrganizations(all);
    }
    void loadOrganizations().catch(() => undefined);
    return () => { cancelled = true; };
  }, [currentUser.role]);

  useEffect(() => {
    if (currentUser.role !== "ENBEK_ADMIN") return;
    const task = window.setTimeout(() => void load(), 250);
    return () => window.clearTimeout(task);
  }, [currentUser.role, load]);

  async function saveUser(event: FormEvent<HTMLFormElement>, user?: PlatformUser) {
    event.preventDefault();
    setError(""); setSuccess("");
    const form = event.currentTarget;
    const data = Object.fromEntries(new FormData(form));
    data.is_active = form.elements.namedItem("is_active") instanceof HTMLInputElement && (form.elements.namedItem("is_active") as HTMLInputElement).checked ? "true" : "false";
    if (!data.password) delete data.password;
    const payload = { ...data, is_active: data.is_active === "true" };
    try {
      await api(user ? `/auth/users/${user.id}/` : "/auth/users/", {
        method: user ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      });
      setEditing(null);
      if (!user) form.reset();
      setSuccess(user ? "Данные пользователя обновлены." : "Пользователь создан.");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось сохранить пользователя");
    }
  }

  async function toggleActive(user: PlatformUser) {
    setError(""); setSuccess("");
    try {
      await api(`/auth/users/${user.id}/`, { method: "PATCH", body: JSON.stringify({ is_active: !user.is_active }) });
      setSuccess(user.is_active ? "Учётная запись заблокирована." : "Учётная запись активирована.");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось изменить статус пользователя");
    }
  }

  if (currentUser.role !== "ENBEK_ADMIN") return <p className="error">Раздел доступен только администратору Еңбек.</p>;
  const pageCount = Math.max(1, Math.ceil(count / REGISTRY_PAGE_SIZE));

  return <>
    <div className="page-heading"><div><p className="page-kicker">Системное управление</p><h1>Администрирование</h1><p>Пользователи платформы, роли и доступ к системе.</p></div></div>
    {error && <p className="error" role="alert">{error}</p>}{success && <p className="success">{success}</p>}

    <details className="surface-panel create-panel">
      <summary><span><strong>Новый пользователь</strong><small>Создание учётной записи в выбранной организации</small></span><span className="md-button primary">+ Добавить</span></summary>
      <form className="compact-form" key={organizations.length} onSubmit={(event) => saveUser(event)}>
        <div className="field"><label htmlFor="new_full_name">ФИО</label><input id="new_full_name" name="full_name" minLength={2} maxLength={255} required /></div>
        <div className="field"><label htmlFor="new_email">Email</label><input id="new_email" name="email" type="email" required /></div>
        <div className="field"><label htmlFor="new_password">Временный пароль</label><input id="new_password" name="password" type="password" minLength={10} required /></div>
        <div className="field"><label htmlFor="new_organization">Организация</label><select id="new_organization" name="organization" defaultValue={currentUser.organization} required><option value="">Выберите</option>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.kind === "ENBEK" ? "Еңбек" : "МСБ"}</option>)}</select></div>
        <div className="field"><label htmlFor="new_role">Роль</label><select id="new_role" name="role" defaultValue="ENBEK_EXECUTOR">{roles.map((item) => <option key={item} value={item}>{roleNames[item]}</option>)}</select></div>
        <label className="check-field"><input name="is_active" type="checkbox" defaultChecked />Активная учётная запись</label>
        <div className="span-2 form-actions"><button className="md-button primary">Создать пользователя</button></div>
      </form>
    </details>

    {editing && <section className="surface-panel edit-user-panel"><div className="panel-heading"><div><h2>Редактирование пользователя</h2><p>{editing.organization_name}</p></div><button className="text-button" type="button" onClick={() => setEditing(null)}>Закрыть</button></div><form className="compact-form" key={editing.id} onSubmit={(event) => saveUser(event, editing)}>
      <div className="field"><label htmlFor="edit_user_full_name">ФИО</label><input id="edit_user_full_name" name="full_name" defaultValue={editing.full_name} minLength={2} maxLength={255} required /></div>
      <div className="field"><label htmlFor="edit_user_email">Email</label><input id="edit_user_email" name="email" type="email" defaultValue={editing.email} required /></div>
      <div className="field"><label htmlFor="edit_user_password">Новый пароль</label><input id="edit_user_password" name="password" type="password" minLength={10} placeholder="Оставьте пустым, чтобы не менять" /></div>
      <div className="field"><label htmlFor="edit_user_organization">Организация</label><select id="edit_user_organization" name="organization" defaultValue={editing.organization} required>{organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
      <div className="field"><label htmlFor="edit_user_role">Роль</label><select id="edit_user_role" name="role" defaultValue={editing.role}>{roles.map((item) => <option key={item} value={item}>{roleNames[item]}</option>)}</select></div>
      <label className="check-field"><input name="is_active" type="checkbox" defaultChecked={editing.is_active} />Активная учётная запись</label>
      <div className="span-2 form-actions"><button className="md-button primary">Сохранить изменения</button></div>
    </form></section>}

    <section className="surface-panel table-panel registry-panel">
      <div className="panel-heading"><div><h2>Пользователи платформы</h2><p>{count} учётных записей · по {REGISTRY_PAGE_SIZE} на странице</p></div></div>
      <div className="filter-bar"><label className="search-control"><span>⌕</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="ФИО, email, организация или БИН" /></label><select value={role} onChange={(event) => { setRole(event.target.value); setPage(1); }}><option value="">Все роли</option>{roles.map((item) => <option key={item} value={item}>{roleNames[item]}</option>)}</select><select value={active} onChange={(event) => { setActive(event.target.value); setPage(1); }}><option value="">Все статусы</option><option value="true">Активные</option><option value="false">Заблокированные</option></select><button className="text-button" type="button" onClick={() => { setQuery(""); setRole(""); setActive(""); setPage(1); }}>Сбросить</button></div>
      <div className="data-table-wrap registry-table"><table className="data-table"><thead><tr><th>Пользователь</th><th>Организация</th><th>Роль</th><th>Создан</th><th>Статус</th><th /></tr></thead><tbody>
        {users.map((user) => <tr key={user.id}><td><strong>{user.full_name}</strong><small>{user.email}</small></td><td><strong>{user.organization_name}</strong><small>{user.organization_kind === "ENBEK" ? "Организация Еңбек" : "МСБ"}</small></td><td>{roleNames[user.role] ?? user.role}</td><td>{formatDate(user.date_joined)}</td><td><span className={`status-chip ${user.is_active ? "status-active" : "status-withdrawn"}`}>{user.is_active ? "Активен" : "Заблокирован"}</span></td><td><div className="table-actions"><button className="text-button" type="button" onClick={() => setEditing(user)}>Редактировать</button><button className={`text-button ${user.is_active ? "danger-text" : ""}`} type="button" disabled={user.id === currentUser.id} onClick={() => toggleActive(user)}>{user.is_active ? "Заблокировать" : "Активировать"}</button></div></td></tr>)}
        {users.length === 0 && <tr><td colSpan={6} className="empty-state">Пользователи не найдены</td></tr>}
      </tbody></table></div>
      <Pagination page={page} pageCount={pageCount} onChange={setPage} />
    </section>
  </>;
}
