const API_URL = 'http://localhost:8000';

export type Vehicle = {
  id: number;
  user_id: number;
  make: string;
  model: string;
  year: number;
  mileage: number;
  vin: string | null;
  license_plate: string | null;
  created_at: string;
};

export type Maintenance = {
  id: number;
  vehicle_id: number;
  service_type: string;
  service_date: string;
  mileage: number;
  cost: string | number | null;
  notes: string | null;
  created_at: string;
};

export type Expense = {
  id: number;
  vehicle_id: number;
  amount: string | number;
  category: string;
  date: string;
  notes: string | null;
  created_at: string;
};

export type ReminderStatus = 'overdue' | 'approaching' | 'upcoming';

export type Schedule = {
  id: number;
  vehicle_id: number;
  service_type: string;
  interval_miles: number | null;
  interval_days: number | null;
  due_mileage: number | null;
  due_date: string | null;
  notes: string | null;
  created_at: string;
  status: ReminderStatus;
  miles_remaining: number | null;
  days_remaining: number | null;
};

export type User = {
  id: number;
  name: string;
  email: string;
};

export async function apiRequest<T = unknown>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers }
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const detail = data?.detail;
    throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((e: { msg?: string }) => e.msg).join(', ') : `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  return text ? JSON.parse(text) as T : undefined as T;
}

export const todayIso = () => {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};
export const fmtMileage = (value: number) => `${value.toLocaleString()} mi`;
export const fmtDate = (value: string) => new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });

export const reminderStatusLabel = (status: ReminderStatus): string => {
  if (status === 'overdue') return 'Overdue';
  if (status === 'approaching') return 'Due soon';
  return 'Upcoming';
};

export const intervalLabel = (schedule: Pick<Schedule, 'interval_miles' | 'interval_days'>): string => {
  if (schedule.interval_miles != null) return `Every ${fmtMileage(schedule.interval_miles)}`;
  if (schedule.interval_days != null) {
    const days = schedule.interval_days;
    return `Every ${days} ${days === 1 ? 'day' : 'days'}`;
  }
  return '';
};

export const dueLabel = (schedule: Pick<Schedule, 'due_mileage' | 'due_date'>): string => {
  if (schedule.due_mileage != null) return `Due at ${fmtMileage(schedule.due_mileage)}`;
  if (schedule.due_date) return `Due ${fmtDate(schedule.due_date)}`;
  return '';
};

export const reminderTiming = (schedule: Pick<Schedule, 'miles_remaining' | 'days_remaining'>): string => {
  if (schedule.miles_remaining != null) {
    if (schedule.miles_remaining < 0) return `${fmtMileage(Math.abs(schedule.miles_remaining))} overdue`;
    if (schedule.miles_remaining === 0) return 'Due now';
    return `${fmtMileage(schedule.miles_remaining)} left`;
  }
  if (schedule.days_remaining != null) {
    const days = schedule.days_remaining;
    if (days < 0) {
      const count = Math.abs(days);
      return `${count} ${count === 1 ? 'day' : 'days'} overdue`;
    }
    if (days === 0) return 'Due today';
    return `${days} ${days === 1 ? 'day' : 'days'} left`;
  }
  return '';
};
