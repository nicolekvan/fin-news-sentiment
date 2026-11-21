import Link from "next/link";

export default function NotFound() {
  return (
    <div className="py-24 text-center">
      <h1 className="text-lg font-semibold">Page not found</h1>
      <p className="mt-1 text-xs text-muted">This company or page isn&apos;t in the snapshot.</p>
      <Link href="/" className="mt-3 inline-block text-xs text-accent hover:underline">
        Back to the overview
      </Link>
    </div>
  );
}
