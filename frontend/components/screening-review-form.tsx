"use client";

import { FormEvent, useState } from "react";
import { api } from "@/lib/api";
import { Screening } from "@/lib/applications";

export function ScreeningReviewForm({
  screening,
  onReviewed,
}: {
  screening: Screening;
  onReviewed: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    if (!submitter?.value) return;
    const form = event.currentTarget;
    const values = new FormData(form);
    values.set("result", submitter.value);
    setBusy(true);
    setError("");
    try {
      await api(`/applications/screenings/${screening.id}/review/`, {
        method: "POST",
        body: values,
      });
      form.reset();
      await onReviewed();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось сохранить заключение");
    } finally {
      setBusy(false);
    }
  }

  return <form className="screening-review-form" onSubmit={submit}>
    <div className="screening-fields">
      <div className="field">
        <label htmlFor={`comment-${screening.id}`}>Комментарий к заключению</label>
        <textarea id={`comment-${screening.id}`} name="comment" rows={3} minLength={3} maxLength={2000} required placeholder="Укажите обоснование решения" />
        <small>Комментарий обязателен для любого решения</small>
      </div>
      <div className="field">
        <label htmlFor={`document-${screening.id}`}>Заключение, PDF</label>
        <input id={`document-${screening.id}`} name="document" type="file" accept="application/pdf,.pdf" required />
        <small>Один PDF-файл размером до 10 МБ</small>
      </div>
    </div>
    {error && <p className="error" role="alert">{error}</p>}
    <div className="screening-actions">
      <button className="md-button secondary" type="submit" name="result" value="APPROVED" disabled={busy}>{busy ? "Сохраняем…" : "Согласовать"}</button>
      <button className="md-button danger" type="submit" name="result" value="REJECTED" disabled={busy}>{busy ? "Сохраняем…" : "Отклонить"}</button>
    </div>
  </form>;
}
