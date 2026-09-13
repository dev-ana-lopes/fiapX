import { Notification } from "./notification.model";

export interface NotificationGroup {
  label: string;
  items: Notification[];
}

export function notificationIconClass(type: string): string {
  return type === "VIDEO_FAILED"
    ? "error"
    : type === "VIDEO_COMPLETED"
      ? "success"
      : "info";
}

export function groupNotifications(
  notifications: Notification[],
  now = new Date(),
): NotificationGroup[] {
  const grouped = new Map<string, Notification[]>();
  for (const item of notifications) {
    const date = new Date(item.createdAt);
    const label =
      date.toDateString() === now.toDateString() ? "Hoje" : "Anteriores";
    grouped.set(label, [...(grouped.get(label) || []), item]);
  }
  return [...grouped.entries()].map(([label, items]) => ({ label, items }));
}
