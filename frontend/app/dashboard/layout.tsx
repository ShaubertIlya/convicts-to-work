"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { DashboardUserProvider } from "@/components/dashboard-user";
import { api } from "@/lib/api";
import { roleNames, User } from "@/lib/dashboard";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api<User>("/auth/me/").then(setUser).catch(() => router.replace("/login"));
  }, [router]);

  const isClinicalRole = user?.role === "MEDIC" || user?.role === "PSYCHOLOGIST";
  const canViewReports = user?.role === "ENBEK_MANAGER" || user?.role === "ENBEK_ADMIN";
  const isClinicalPathAllowed = pathname === "/dashboard"
    || pathname === "/applications"
    || pathname.startsWith("/applications/screenings/");

  useEffect(() => {
    if (isClinicalRole && !isClinicalPathAllowed) router.replace("/applications");
  }, [isClinicalPathAllowed, isClinicalRole, router]);

  useEffect(() => {
    if (user && pathname === "/reports" && !canViewReports) router.replace("/dashboard");
  }, [canViewReports, pathname, router, user]);

  async function logout() {
    try {
      await api("/auth/logout/", { method: "POST", body: "{}" });
    } finally {
      router.replace("/");
      router.refresh();
    }
  }

  if (!user || (isClinicalRole && !isClinicalPathAllowed) || (pathname === "/reports" && !canViewReports)) {
    return <main className="portal-loading"><span className="loader" />Загрузка кабинета…</main>;
  }

  const menu = [
    { href: "/dashboard", label: "Обзор", icon: "⌂" },
    { href: "/applications", label: isClinicalRole ? "Заявки на обследование" : "Заявки", icon: "▤" },
    ...(!isClinicalRole ? [{ href: "/contracts", label: "Договоры", icon: "▥" }] : []),
    ...(canViewReports ? [{ href: "/reports", label: "Отчётность", icon: "▧" }] : []),
    ...(user.role !== "BUSINESS_ADMIN"
      && !isClinicalRole
      ? [
          { href: "/prisoners", label: "Осуждённые", icon: "◇" },
          { href: "/businesses", label: "Организации МСБ", icon: "▦" },
        ]
      : []),
    ...(user.role === "ENBEK_ADMIN"
      ? [{ href: "/administration", label: "Администрирование", icon: "⚙" }]
      : []),
    ...(!isClinicalRole ? [{ href: "/profile", label: "Профиль организации", icon: "○" }] : []),
  ];

  return <DashboardUserProvider user={user}>
    <div className="portal-shell">
      <aside className="portal-sidebar">
        <Link className="portal-brand" href="/"><span className="portal-mark">E</span><span>Еңбек<small>Трудовая платформа</small></span></Link>
        <nav className="portal-nav" aria-label="Разделы личного кабинета">
          {menu.map((item) => {
            const active = item.href === "/dashboard" ? pathname === item.href : pathname.startsWith(item.href);
            return <Link className={active ? "active" : ""} href={item.href} key={item.href}><span className="portal-nav-icon">{item.icon}</span>{item.label}</Link>;
          })}
        </nav>
        <div className="portal-account">
          <div className="avatar">{user.full_name.slice(0, 1).toUpperCase()}</div>
          <div><strong>{user.full_name}</strong><small>{roleNames[user.role] ?? user.role}</small></div>
          <button type="button" onClick={logout} aria-label="Выйти">↗</button>
        </div>
      </aside>
      <div className="portal-content">
        <header className="portal-topbar"><div><span>Организация</span><strong>{user.organization_name}</strong></div><div className="portal-topbar-actions"><Link className="icon-button" href="/" aria-label="На главную">⌂</Link><button className="icon-button mobile-logout" type="button" onClick={logout} aria-label="Выйти">↗</button></div></header>
        <main className="portal-main">{children}</main>
      </div>
    </div>
  </DashboardUserProvider>;
}
