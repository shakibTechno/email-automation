import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export function formatDateTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function getInitials(firstName?: string, lastName?: string): string {
  const first = firstName?.charAt(0) || ''
  const last = lastName?.charAt(0) || ''
  return (first + last).toUpperCase() || '?'
}

export function downloadCSV(data: string, filename: string) {
  const blob = new Blob([data], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

export function getEngagementLevel(score: number): {
  label: string
  color: string
} {
  if (score >= 80) {
    return { label: 'High', color: 'text-success bg-success/[.10]' }
  } else if (score >= 50) {
    return { label: 'Medium', color: 'text-warning bg-warning/[.10]' }
  } else {
    return { label: 'Low', color: 'text-destructive bg-destructive/[.10]' }
  }
}

export function getSubscriptionStatusColor(status: string): string {
  const colors: Record<string, string> = {
    active: 'text-success bg-success/[.10] border-success/[.30]',
    unsubscribed: 'text-foreground bg-secondary/50 border-border',
    bounced: 'text-destructive bg-destructive/[.10] border-destructive/[.30]',
    complained: 'text-warning bg-warning/[.10] border-warning/[.30]',
  }
  return colors[status] || colors.active
}
