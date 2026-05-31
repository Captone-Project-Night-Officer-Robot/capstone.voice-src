export default function Panel({ title, right, className = "", bodyRef, children }) {
  return (
    <section
      className={`flex flex-col rounded-xl border border-white/5 bg-panel/80 ${className}`}
    >
      {title && (
        <header className="flex items-center justify-between px-4 py-2.5 border-b border-white/5">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
            {title}
          </h2>
          {right}
        </header>
      )}
      <div ref={bodyRef} className="min-h-0 flex-1 overflow-auto p-3">
        {children}
      </div>
    </section>
  );
}
