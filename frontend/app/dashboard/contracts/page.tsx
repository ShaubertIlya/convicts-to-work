"use client";

import { useCallback, useEffect, useState } from "react";
import { useDashboardUser } from "@/components/dashboard-user";
import { Modal } from "@/components/modal";
import { Pagination } from "@/components/pagination";
import { api } from "@/lib/api";
import { formatDate, OrganizationDetails, Page, statusNames, unwrap } from "@/lib/dashboard";
import { mediaPath } from "@/lib/prisoners";
import { REGISTRY_PAGE_SIZE } from "@/lib/registry";

type Signature = { party: string; signed_at: string; signed_by_name: string };
type Contract = {
  id: string; number: string; application: string; prisoner_name: string;
  organization_name: string; organization_details: OrganizationDetails; status: string;
  starts_on: string; ends_on: string; signatures: Signature[]; created_at: string;
  document: string;
};

const contractStatuses = ["AWAITING_PRISONER", "PARTIALLY_SIGNED", "ACTIVE", "EXPIRED"];
const signatureNames: Record<string, string> = {
  PRISONER: "Осуждённый", ENBEK_MANAGER: "Руководитель Еңбек", BUSINESS_ADMIN: "МСБ",
};

function formatSignedAt(value: string) {
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

export default function ContractsPage() {
  const user = useDashboardUser();
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [applicationId, setApplicationId] = useState("");
  const [acknowledgedIds, setAcknowledgedIds] = useState<string[]>([]);
  const [selectedContractId, setSelectedContractId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [biometryResult, setBiometryResult] = useState<"success" | "error" | null>(null);

  const load = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), page_size: String(REGISTRY_PAGE_SIZE) });
      if (query.trim()) params.set("search", query.trim());
      if (status) params.set("status", status);
      if (applicationId) params.set("application_id", applicationId);
      const rows = await api<Page<Contract>>(`/contracts/?${params}`);
      setContracts(unwrap(rows));
      setTotal(rows.count ?? unwrap(rows).length);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось загрузить договоры"); }
  }, [applicationId, page, query, status]);
  useEffect(() => {
    const task = window.setTimeout(() => {
      const params = new URLSearchParams(window.location.search);
      const requestedNumber = params.get("number");
      if (requestedNumber) setQuery(requestedNumber);
      const requestedApplication = params.get("application_id");
      if (requestedApplication) setApplicationId(requestedApplication);
      const biometry = params.get("biometry");
      if (biometry === "success" || biometry === "error") {
        setBiometryResult(biometry);
        params.delete("biometry");
        const remaining = params.toString();
        window.history.replaceState(window.history.state, "", `${window.location.pathname}${remaining ? `?${remaining}` : ""}`);
      }
    }, 0);
    return () => window.clearTimeout(task);
  }, []);

  useEffect(() => {
    const task = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(task);
  }, [load]);

  const pageCount = Math.max(1, Math.ceil(total / REGISTRY_PAGE_SIZE));
  const selectedContract = contracts.find((item) => item.id === selectedContractId);

  async function action(path: string) {
    setError("");
    try { await api(path, { method: "POST", body: "{}" }); await load(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Ошибка операции"); }
  }

  async function startBiometry(contract: Contract) {
    setError("");
    try {
      const result = await api<{ redirect_url: string }>(`/contracts/${contract.id}/start-prisoner-signature/`, { method: "POST", body: JSON.stringify({ acknowledged: acknowledgedIds.includes(contract.id) }) });
      window.location.assign(result.redirect_url);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Ошибка биометрии"); }
  }

  async function uploadDocument(contract: Contract, document?: File) {
    if (!document) return;
    setError("");
    try {
      const body = new FormData();
      body.set("document", document);
      await api(`/contracts/${contract.id}/upload-document/`, { method: "POST", body });
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Не удалось загрузить PDF договора"); }
  }

  return <>
    <div className="page-heading"><div><p className="page-kicker">Документы</p><h1>Трудовые договоры</h1><p>Реестр договоров и статусы подписания.</p></div></div>
    {error && <p className="error" role="alert">{error}</p>}
    {biometryResult && <Modal className="result-dialog" role="alertdialog" labelledBy="biometry-result-title" describedBy="biometry-result-description" onClose={() => setBiometryResult(null)}>
      <h2 id="biometry-result-title">{biometryResult === "success" ? "Подпись подтверждена" : "Подписание не завершено"}</h2>
      <p id="biometry-result-description">{biometryResult === "success" ? "Биометрия пройдена, подпись осуждённого зафиксирована. Для завершения договора нужны подписи МСБ и руководителя Еңбек." : "Биометрическая проверка не завершилась успешно. Подпись осуждённого не зафиксирована; при необходимости запустите проверку повторно."}</p>
      <button className="md-button primary" type="button" autoFocus onClick={() => setBiometryResult(null)}>Понятно</button>
    </Modal>}
    {selectedContract && <Modal className="contract-dialog" labelledBy="contract-dialog-title" onClose={() => setSelectedContractId(null)}>
        <div className="contract-dialog-heading"><div><p className="page-kicker">Трудовой договор</p><h2 id="contract-dialog-title">{selectedContract.number}</h2></div><button className="text-button" type="button" autoFocus onClick={() => setSelectedContractId(null)} aria-label="Закрыть сведения о договоре">Закрыть</button></div>
        <div className="contract-dialog-facts"><div><small>Компания</small><strong>{selectedContract.organization_name}</strong></div><div><small>Работник</small><strong>{selectedContract.prisoner_name}</strong></div><div><small>Срок действия</small><strong>{formatDate(selectedContract.starts_on)} — {formatDate(selectedContract.ends_on)}</strong></div><div><small>Статус</small><span className={`status-chip status-${selectedContract.status.toLowerCase()}`}>{statusNames[selectedContract.status] ?? selectedContract.status}</span></div></div>
        <div className="contract-dialog-section"><h3>Подписи сторон</h3><div className="contract-signature-list">
          {Object.entries(signatureNames).map(([party, name]) => {
            const signature = selectedContract.signatures.find((item) => item.party === party);
            return <div key={party}><strong>{name}</strong><span>{signature ? `${formatSignedAt(signature.signed_at)}${signature.signed_by_name ? ` · ${signature.signed_by_name}` : ""}` : "Не подписан"}</span></div>;
          })}
        </div></div>
        <div className="contract-dialog-section"><h3>Документ и действия</h3>
          {error && <p className="error" role="alert">{error}</p>}
          <div className="contract-dialog-actions">
            {["ENBEK_EXECUTOR", "ENBEK_MANAGER"].includes(user.role) && selectedContract.signatures.length === 0 && <label className="contract-upload">Загрузить PDF договора<input type="file" accept="application/pdf,.pdf" onChange={(event) => void uploadDocument(selectedContract, event.target.files?.[0])} /></label>}
            {selectedContract.document && <a className="md-button secondary" href={mediaPath(selectedContract.document)} target="_blank" rel="noreferrer">Открыть PDF договора</a>}
            {["ENBEK_EXECUTOR", "ENBEK_MANAGER"].includes(user.role) && selectedContract.status === "AWAITING_PRISONER" && selectedContract.document && <><label className="contract-consent"><input type="checkbox" checked={acknowledgedIds.includes(selectedContract.id)} onChange={(event) => setAcknowledgedIds((current) => event.target.checked ? [...current, selectedContract.id] : current.filter((id) => id !== selectedContract.id))} />Осуждённый ознакомился с PDF</label><button className="md-button primary" type="button" disabled={!acknowledgedIds.includes(selectedContract.id)} onClick={() => startBiometry(selectedContract)}>Подпись осуждённого</button></>}
            {["BUSINESS_ADMIN", "ENBEK_MANAGER"].includes(user.role) && selectedContract.document && selectedContract.signatures.some((item) => item.party === "PRISONER") && !selectedContract.signatures.some((item) => item.party === user.role) && <button className="md-button primary" type="button" onClick={() => action(`/contracts/${selectedContract.id}/sign/`)}>Подписать договор</button>}
            {!selectedContract.document && <span className="contract-awaiting-document">Ожидается PDF договора</span>}
          </div>
        </div>
    </Modal>}
    <section className="surface-panel table-panel registry-panel contracts-registry">
      <div className="panel-heading"><div><h2>Реестр договоров</h2><p>{total} договоров · по {REGISTRY_PAGE_SIZE} на странице</p></div></div>
      <div className="filter-bar"><label className="search-control"><span>⌕</span><input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="Номер, компания или сотрудник" /></label><select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">Все статусы</option>{contractStatuses.map((item) => <option value={item} key={item}>{statusNames[item]}</option>)}</select><button className="text-button" type="button" onClick={() => { setQuery(""); setStatus(""); setApplicationId(""); setPage(1); }}>Сбросить</button></div>
      <div className="data-table-wrap registry-table"><table className="data-table"><thead><tr><th>Договор</th><th>Компания</th><th>Работник</th><th>Срок действия</th><th>Подписи</th><th>Статус</th><th /></tr></thead><tbody>
        {contracts.map((contract) => <tr key={contract.id}>
          <td><strong>{contract.number}</strong><small>{formatDate(contract.created_at)}</small></td>
          <td><strong>{contract.organization_name}</strong><small>БИН {contract.organization_details.bin}</small></td>
          <td>{contract.prisoner_name}</td>
          <td><strong>{formatDate(contract.starts_on)}</strong><small>до {formatDate(contract.ends_on)}</small></td>
          <td><div className="signature-dots" aria-label={`${contract.signatures.length} из 3 подписей`}><span className={contract.signatures.some((item) => item.party === "PRISONER") ? "done" : ""}>О</span><span className={contract.signatures.some((item) => item.party === "ENBEK_MANAGER") ? "done" : ""}>Е</span><span className={contract.signatures.some((item) => item.party === "BUSINESS_ADMIN") ? "done" : ""}>М</span></div></td>
          <td><span className={`status-chip status-${contract.status.toLowerCase()}`}>{statusNames[contract.status] ?? contract.status}</span></td>
          <td><button className="text-button" type="button" onClick={() => { setError(""); setSelectedContractId(contract.id); }}>Открыть</button></td>
        </tr>)}
        {contracts.length === 0 && <tr><td colSpan={7} className="empty-state">По заданным фильтрам договоров нет</td></tr>}
      </tbody></table></div>
      <Pagination page={Math.min(page, pageCount)} pageCount={pageCount} onChange={setPage} />
    </section>
  </>;
}
