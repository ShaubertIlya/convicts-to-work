"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSubmitting(true);
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      await api("/auth/login/", { method: "POST", body: JSON.stringify(data) });
      router.replace("/dashboard");
      router.refresh();
    }
    catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ошибка входа");
      setSubmitting(false);
    }
  }
  return <main className="auth-shell"><section className="auth-card narrow"><Link className="brand" href="/"><span className="mark">E</span> Еңбек</Link><h2>Вход в систему</h2><p className="muted">Используйте учётную запись вашей организации.</p>{error && <p className="error" role="alert">{error}</p>}<form className="form-grid" onSubmit={submit}><div className="field full"><label htmlFor="login-email">Email</label><input id="login-email" name="email" type="email" maxLength={254} autoComplete="email" required /></div><div className="field full"><label htmlFor="login-password">Пароль</label><input id="login-password" name="password" type="password" maxLength={128} autoComplete="current-password" required /></div><button className="button field full" disabled={submitting}>{submitting ? "Входим…" : "Войти"}</button></form><p className="muted">Нет профиля компании? <Link href="/register">Зарегистрироваться</Link></p></section></main>;
}
