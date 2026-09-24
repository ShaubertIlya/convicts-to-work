"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

type Oked = { id: string; code: string; name_ru: string; name_kk: string };
type Bank = { id: string; bic: string; bank_code: string; name_ru: string; name_kk: string };

const digits = (value: string, limit: number) => value.replace(/\D/g, "").slice(0, limit);
const normalizeIik = (value: string) => value.replace(/\s/g, "").toUpperCase();
const formatIik = (value: string) =>
  normalizeIik(value).replace(/[^A-Z0-9]/g, "").slice(0, 20).replace(/(.{4})/g, "$1 ").trim();

function formatPhone(value: string) {
  const source = digits(value, 11);
  if (!source) return "";
  const local = (source.startsWith("7") || source.startsWith("8") ? source.slice(1) : source).slice(0, 10);
  let result = "+7";
  if (local.length) result += ` (${local.slice(0, 3)}`;
  if (local.length >= 3) result += ")";
  if (local.length > 3) result += ` ${local.slice(3, 6)}`;
  if (local.length > 6) result += `-${local.slice(6, 8)}`;
  if (local.length > 8) result += `-${local.slice(8, 10)}`;
  return result;
}

function normalizePhone(value: string) {
  const local = digits(value, 11);
  if (local.length === 11 && (local.startsWith("7") || local.startsWith("8"))) return `+7${local.slice(1)}`;
  return local.length === 10 ? `+7${local}` : "";
}

function isValidIik(value: string) {
  const normalized = normalizeIik(value);
  if (!/^KZ\d{2}[A-HJ-NP-Z0-9]{16}$/.test(normalized)) return false;
  const rearranged = normalized.slice(4) + normalized.slice(0, 4);
  const numeric = [...rearranged].map((char) => (/[A-Z]/.test(char) ? char.charCodeAt(0) - 55 : char)).join("");
  let remainder = 0;
  for (const char of numeric) remainder = (remainder * 10 + Number(char)) % 97;
  return remainder === 1;
}

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [same, setSame] = useState(false);
  const [legalAddress, setLegalAddress] = useState("");
  const [actualAddress, setActualAddress] = useState("");
  const [okedRows, setOkedRows] = useState<Oked[]>([]);
  const [okedQuery, setOkedQuery] = useState("");
  const [selectedOked, setSelectedOked] = useState<Oked | null>(null);
  const [banks, setBanks] = useState<Bank[]>([]);
  const [bankId, setBankId] = useState("");
  const [phone, setPhone] = useState("");
  const [iik, setIik] = useState("");
  const selectedBank = useMemo(() => banks.find((bank) => bank.id === bankId), [bankId, banks]);
  const filteredOked = useMemo(() => {
    const query = okedQuery.trim().toLocaleLowerCase("ru");
    if (query.length < 2 || selectedOked) return [];
    return okedRows.filter((item) =>
      item.name_ru.toLocaleLowerCase("ru").includes(query)
      || item.name_kk.toLocaleLowerCase("kk").includes(query)
    ).slice(0, 8);
  }, [okedQuery, okedRows, selectedOked]);

  useEffect(() => {
    Promise.all([api<Oked[]>("/organizations/oked/"), api<Bank[]>("/organizations/banks/")])
      .then(([oked, bankRows]) => { setOkedRows(oked); setBanks(bankRows); })
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Не удалось загрузить справочники."))
      .finally(() => setLoading(false));
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const phoneValue = normalizePhone(phone);
    const iikValue = normalizeIik(iik);
    if (!selectedOked) { setError("Найдите ОКЭД по названию и выберите вариант из справочника."); return; }
    if (!phoneValue) { setError("Укажите полный номер телефона руководителя."); return; }
    if (!isValidIik(iikValue)) { setError("Проверьте ИИК: нужен действительный казахстанский IBAN из 20 символов."); return; }
    if (selectedBank && iikValue.slice(4, 7) !== selectedBank.bank_code) { setError("Код банка в ИИК не соответствует выбранному банку."); return; }

    const values = Object.fromEntries(new FormData(event.currentTarget));
    const payload = {
      ...values,
      staff_count: Number(values.staff_count),
      oked_code: selectedOked.code,
      actual_address: same ? legalAddress : actualAddress,
      actual_address_same: same,
      bank: bankId,
      director_phone: phoneValue,
      iik: iikValue,
    };
    setSubmitting(true);
    try {
      await api("/auth/register/", { method: "POST", body: JSON.stringify(payload) });
      router.push("/login");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Ошибка регистрации");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-shell registration-shell">
      <section className="auth-card registration-card">
        <Link className="brand" href="/"><span className="mark">E</span> Еңбек</Link>
        <h2>Регистрация компании</h2>
        <p className="muted">Заполните сведения о компании. Профиль станет доступен сразу после регистрации.</p>
        {error && <p className="error" role="alert">{error}</p>}

        <form className="registration-form" onSubmit={submit}>
          <fieldset className="form-section">
            <legend>Информация о юридическом лице</legend>
            <p className="section-hint">Регистрационные данные и основной вид деятельности</p>
            <div className="form-grid">
              <div className="field full"><label htmlFor="name">Название юридического лица</label><input id="name" name="name" minLength={2} maxLength={255} required /></div>
              <div className="field"><label htmlFor="bin">БИН</label><input id="bin" name="bin" inputMode="numeric" pattern="[0-9]{12}" minLength={12} maxLength={12} placeholder="12 цифр" title="Введите ровно 12 цифр" onInput={(event) => { event.currentTarget.value = digits(event.currentTarget.value, 12); }} required /><small>Ровно 12 цифр</small></div>
              <div className="field"><label htmlFor="staff_count">Численность штата</label><input id="staff_count" name="staff_count" type="number" min="1" max="1000000" step="1" required /></div>
              <div className="field full oked-picker">
                <label htmlFor="oked_search">ОКЭД — поиск по названию</label>
                <input id="oked_search" type="search" minLength={2} maxLength={255} value={okedQuery} placeholder={loading ? "Загрузка справочника…" : "Например, строительство жилых зданий"} onChange={(event) => { setOkedQuery(event.target.value); setSelectedOked(null); }} disabled={loading} autoComplete="off" required />
                {filteredOked.length > 0 && <div className="oked-results" role="listbox" aria-label="Результаты поиска ОКЭД">{filteredOked.map((item) => <button type="button" role="option" aria-selected={false} key={item.id} onClick={() => { setSelectedOked(item); setOkedQuery(item.name_ru); }}><span>{item.name_ru}</span><strong>{item.code}</strong></button>)}</div>}
                {okedQuery.trim().length >= 2 && !selectedOked && filteredOked.length === 0 && <small>По вашему запросу ничего не найдено</small>}
                {selectedOked ? <small className="selected-reference">Выбрано: {selectedOked.code} — {selectedOked.name_ru}</small> : <small>Введите не менее двух букв и выберите название из справочника</small>}
              </div>
              <div className="field full"><label htmlFor="activity_type">Вид деятельности</label><input id="activity_type" name="activity_type" minLength={2} maxLength={255} required /></div>
              <div className="field full"><label htmlFor="licenses">Лицензии и разрешения</label><textarea id="licenses" name="licenses" maxLength={2000} rows={3} placeholder="Если применимо" /></div>
              <div className="address-fields full">
                <div className="field"><label htmlFor="legal_address">Юридический адрес</label><textarea id="legal_address" name="legal_address" minLength={5} maxLength={500} rows={3} value={legalAddress} onChange={(event) => setLegalAddress(event.target.value)} required /></div>
                <div className="field"><label htmlFor="actual_address">Фактический адрес</label><textarea id="actual_address" name="actual_address" minLength={5} maxLength={500} rows={3} value={same ? legalAddress : actualAddress} onChange={(event) => setActualAddress(event.target.value)} readOnly={same} required /></div>
                <label className="address-match"><input type="checkbox" checked={same} onChange={(event) => setSame(event.target.checked)} /> Юридический адрес совпадает с фактическим</label>
              </div>
            </div>
          </fieldset>

          <fieldset className="form-section">
            <legend>Банковские реквизиты</legend>
            <p className="section-hint">БИК подставляется автоматически из справочника Национального Банка</p>
            <div className="form-grid">
              <div className="field full"><label htmlFor="bank">Наименование банка</label><select id="bank" name="bank" value={bankId} onChange={(event) => setBankId(event.target.value)} disabled={loading} required><option value="">Выберите банк</option>{banks.map((bank) => <option value={bank.id} key={bank.id}>{bank.name_ru}</option>)}</select></div>
              <div className="field"><label htmlFor="bik">БИК</label><input id="bik" value={selectedBank?.bic ?? ""} placeholder="Заполнится автоматически" readOnly /></div>
              <div className="field"><label htmlFor="kbe">КБЕ</label><input id="kbe" name="kbe" inputMode="numeric" pattern="[12][0-9]" minLength={2} maxLength={2} placeholder="Например, 17" title="Две цифры; первая — 1 или 2" onInput={(event) => { event.currentTarget.value = digits(event.currentTarget.value, 2); }} required /><small>2 цифры; первая — 1 или 2</small></div>
              <div className="field full"><label htmlFor="iik">ИИК (IBAN)</label><input id="iik" name="iik" autoCapitalize="characters" autoComplete="off" minLength={20} maxLength={24} placeholder="KZ00 0000 0000 0000 0000" value={iik} onChange={(event) => setIik(formatIik(event.target.value))} required /><small>20 символов, начинается с KZ</small></div>
            </div>
          </fieldset>

          <fieldset className="form-section">
            <legend>Первый руководитель</legend>
            <div className="form-grid">
              <div className="field full"><label htmlFor="director_full_name">ФИО руководителя</label><input id="director_full_name" name="director_full_name" minLength={2} maxLength={255} autoComplete="name" required /></div>
              <div className="field"><label htmlFor="director_iin">ИИН руководителя</label><input id="director_iin" name="director_iin" inputMode="numeric" pattern="[0-9]{12}" minLength={12} maxLength={12} placeholder="12 цифр" title="Введите ровно 12 цифр" onInput={(event) => { event.currentTarget.value = digits(event.currentTarget.value, 12); }} required /></div>
              <div className="field"><label htmlFor="director_position">Должность</label><input id="director_position" name="director_position" minLength={2} maxLength={255} required /></div>
              <div className="field"><label htmlFor="director_email">Email руководителя</label><input id="director_email" name="director_email" type="email" maxLength={254} autoComplete="email" required /></div>
              <div className="field"><label htmlFor="director_phone">Телефон руководителя</label><input id="director_phone" name="director_phone_display" type="tel" inputMode="tel" maxLength={18} placeholder="+7 (___) ___-__-__" value={phone} onChange={(event) => setPhone(formatPhone(event.target.value))} autoComplete="tel" required /></div>
            </div>
          </fieldset>

          <fieldset className="form-section">
            <legend>Учётная запись администратора</legend>
            <div className="form-grid">
              <div className="field full"><label htmlFor="full_name">ФИО администратора</label><input id="full_name" name="full_name" minLength={2} maxLength={255} autoComplete="name" required /></div>
              <div className="field"><label htmlFor="email">Email для входа</label><input id="email" name="email" type="email" maxLength={254} autoComplete="email" required /></div>
              <div className="field"><label htmlFor="password">Пароль</label><input id="password" name="password" type="password" minLength={10} maxLength={128} autoComplete="new-password" required /><small>Не менее 10 символов</small></div>
            </div>
          </fieldset>

          <button className="button submit-registration" disabled={loading || submitting}>{submitting ? "Создаём профиль…" : "Создать профиль"}</button>
        </form>
      </section>
    </main>
  );
}
