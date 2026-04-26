import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDateTime(value?: string | null) {
  if (!value) {
    return "--";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

export function formatMetric(value?: number | null, digits = 2) {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return "--";
  }

  return value.toFixed(digits);
}

export function summarizeMetadata(metadata: Record<string, unknown>) {
  return Object.entries(metadata)
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${String(value)}`);
}
