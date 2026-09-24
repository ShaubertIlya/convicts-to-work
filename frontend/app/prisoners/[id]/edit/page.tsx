"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { PrisonerEditor } from "@/components/prisoner-editor";
import { api } from "@/lib/api";
import { Prisoner } from "@/lib/prisoners";

export default function EditPrisonerPage() {
  const { id } = useParams<{ id: string }>();
  const [prisoner, setPrisoner] = useState<Prisoner | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Prisoner>(`/prisoners/${id}/`).then(setPrisoner)
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Личное дело не найдено"));
  }, [id]);

  if (error) return <><Link className="back-link" href="/prisoners">← К реестру</Link><p className="error" role="alert">{error}</p></>;
  if (!prisoner) return <div className="portal-loading inline"><span className="loader" />Загрузка личного дела…</div>;
  return <PrisonerEditor prisoner={prisoner} />;
}
