export function Pagination({ page, pageCount, onChange }: {
  page: number;
  pageCount: number;
  onChange: (page: number) => void;
}) {
  if (pageCount <= 1) return <div className="pagination"><span>Страница 1 из 1</span></div>;
  return <nav className="pagination" aria-label="Пагинация">
    <button type="button" disabled={page === 1} onClick={() => onChange(page - 1)}>←</button>
    {Array.from({ length: pageCount }, (_, index) => index + 1).map((item) => <button
      type="button"
      className={item === page ? "active" : ""}
      aria-current={item === page ? "page" : undefined}
      key={item}
      onClick={() => onChange(item)}
    >{item}</button>)}
    <button type="button" disabled={page === pageCount} onClick={() => onChange(page + 1)}>→</button>
  </nav>;
}
