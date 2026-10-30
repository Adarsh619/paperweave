export default function WakingBanner() {
  return (
    <div role="status" className="rounded-lg border border-border bg-accent-soft px-4 py-3 text-sm">
      <span className="font-medium">Waking up the server…</span>{" "}
      <span className="text-muted">
        The free-tier backend sleeps when idle and takes up to a minute to start. Your question will run as soon as
        it&apos;s up. Example questions are always instant.
      </span>
    </div>
  );
}
