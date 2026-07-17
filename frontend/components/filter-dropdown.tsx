"use client";

import { useRouter } from "next/navigation";

export type FilterDropdownOption = {
  value: string;
  label: string;
  href: string;
};

export default function FilterDropdown({
  label,
  value,
  options,
  className = "",
}: {
  label: string;
  value: string;
  options: FilterDropdownOption[];
  className?: string;
}) {
  const router = useRouter();

  return (
    <label className={`inline-flex items-center gap-2 text-sm text-on-surface-variant ${className}`}>
      <span className="font-medium">{label}</span>
      <span className="relative inline-flex">
        <select
          aria-label={label}
          className="appearance-none rounded-full border border-outline-variant bg-surface px-4 py-2 pr-9 text-sm font-medium text-on-surface focus:outline-none focus:ring-2 focus:ring-primary/40"
          onChange={(e) => {
            const next = options.find((opt) => opt.value === e.target.value);
            if (next) router.push(next.href);
          }}
          value={value}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <span
          aria-hidden
          className="pointer-events-none material-symbols-outlined absolute right-2 top-1/2 -translate-y-1/2 text-on-surface-variant"
          style={{ fontSize: "18px" }}
        >
          expand_more
        </span>
      </span>
    </label>
  );
}
