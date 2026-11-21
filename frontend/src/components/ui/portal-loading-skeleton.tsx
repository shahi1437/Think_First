export function PortalLoadingSkeleton() {
  return (
    <div
      aria-busy="true"
      aria-label="Loading page content"
      className="space-y-6 animate-pulse"
    >
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="h-4 w-36 rounded bg-slate-200" />
        <div className="mt-3 h-8 w-80 max-w-full rounded bg-slate-200" />
        <div className="mt-3 h-4 w-2/3 rounded bg-slate-100" />
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-24 rounded-2xl border border-slate-100 bg-slate-50"
            />
          ))}
        </div>
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="h-44 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
          >
            <div className="h-4 w-28 rounded bg-slate-200" />
            <div className="mt-3 h-6 w-3/4 rounded bg-slate-200" />
            <div className="mt-3 h-4 w-full rounded bg-slate-100" />
          </div>
        ))}
      </div>
    </div>
  );
}
