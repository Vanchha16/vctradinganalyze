/**
 * Native Intl-based formatters - no date/number formatting dependency
 * added for this (docs/54 §4): Intl.DateTimeFormat/NumberFormat/
 * RelativeTimeFormat are sufficient for every page in this phase.
 */

const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "Asia/Bangkok",
});

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  dateStyle: "medium",
  timeZone: "Asia/Bangkok",
});

const relativeFormatter = new Intl.RelativeTimeFormat("en-US", {
  numeric: "auto",
});

const RELATIVE_UNITS: { unit: Intl.RelativeTimeFormatUnit; seconds: number }[] =
  [
    { unit: "year", seconds: 31536000 },
    { unit: "month", seconds: 2592000 },
    { unit: "week", seconds: 604800 },
    { unit: "day", seconds: 86400 },
    { unit: "hour", seconds: 3600 },
    { unit: "minute", seconds: 60 },
  ];

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return dateTimeFormatter.format(date);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return dateFormatter.format(date);
}

export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  const diffSeconds = (date.getTime() - Date.now()) / 1000;
  const absSeconds = Math.abs(diffSeconds);

  for (const { unit, seconds } of RELATIVE_UNITS) {
    if (absSeconds >= seconds) {
      return relativeFormatter.format(Math.round(diffSeconds / seconds), unit);
    }
  }
  return relativeFormatter.format(Math.round(diffSeconds / 60), "minute");
}

export function formatPrice(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const numeric = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(numeric)) return "—";
  return numeric.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 5,
  });
}

export function formatPercent(
  value: number | null | undefined,
  fractionDigits = 1,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toFixed(fractionDigits)}%`;
}

/** USD currency amounts (calculator tools) - distinct from `formatPrice`,
 * which is for asset quote prices, not dollar amounts. */
export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * Economic calendar figures (forecast / previous / actual).
 *
 * The backend stores these as `Numeric(20, 8)`, so the raw JSON is
 * unreadable: "0.8%" arrives as "0.80000000", and Python renders a zero
 * as "0E-8", which reached the UI verbatim. Trailing zeros are dropped
 * and the provider's unit ("%", "K", "B") is appended, so the table
 * shows the figure the way the release prints it.
 */
export function formatEconomicValue(
  value: string | number | null | undefined,
  unit?: string | null,
): string {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(numeric)) return "—";
  const formatted = numeric.toLocaleString("en-US", {
    maximumFractionDigits: 4,
  });
  return unit ? `${formatted}${unit}` : formatted;
}

export function formatEnumLabel(value: string | null | undefined): string {
  if (!value) return "—";
  return value.replace(/_/g, " ");
}
