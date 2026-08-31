"use client";

type Option<T extends string> = { id: T; label: string };

export function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
}: {
  value: T;
  options: Option<T>[];
  onChange: (id: T) => void;
  ariaLabel: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className="inline-flex rounded-[9px] bg-black/[0.06] p-[2px]"
    >
      {options.map((option) => {
        const selected = option.id === value;
        return (
          <button
            key={option.id}
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(option.id)}
            className={`min-w-[72px] rounded-[7px] px-3 py-[5px] text-[12px] font-medium tracking-[-0.01em] transition-all duration-200 ${
              selected
                ? "bg-white text-apple-ink shadow-[0_1px_2px_rgba(0,0,0,0.12)]"
                : "bg-transparent text-apple-muted hover:text-apple-ink"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
