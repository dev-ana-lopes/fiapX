import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from "@angular/core";
import { AppShellComponent } from "@core/layout/app-shell.component";
import { Notification } from "@core/models/notification.model";
import {
  groupNotifications,
  notificationIconClass,
} from "@core/models/notification.utils";
import { NotificationService } from "@core/services/notification.service";

@Component({
  standalone: true,
  imports: [AppShellComponent],
  templateUrl: "./notifications.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotificationsComponent {
  private readonly service = inject(NotificationService);

  readonly notifications = signal<Notification[]>([]);
  readonly unreadCount = signal(0);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly groups = computed(() => groupNotifications(this.notifications()));

  constructor() {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.service.list().subscribe({
      next: (page) => {
        this.notifications.set(page.items);
        this.unreadCount.set(page.unreadCount);
        this.loading.set(false);
      },
      error: () => {
        this.error.set("Não foi possível carregar as notificações.");
        this.loading.set(false);
      },
    });
  }

  markRead(item: Notification): void {
    if (item.status !== "PENDING") return;

    this.service.markRead(item.id).subscribe({
      next: () => {
        const readAt = new Date().toISOString();
        this.notifications.update((items) =>
          items.map((notification) =>
            notification.id === item.id
              ? { ...notification, status: "READ", readAt }
              : notification,
          ),
        );
        this.unreadCount.update((count) => Math.max(0, count - 1));
      },
    });
  }

  markAllRead(): void {
    this.service.markAllRead().subscribe({
      next: () => {
        const readAt = new Date().toISOString();
        this.notifications.update((items) =>
          items.map((item) => ({ ...item, status: "READ", readAt })),
        );
        this.unreadCount.set(0);
      },
    });
  }

  iconClass(item: Notification): string {
    return notificationIconClass(item.type);
  }

  icon(item: Notification): string {
    if (item.type === "VIDEO_FAILED") return "×";
    return item.type === "VIDEO_COMPLETED" ? "✓" : "i";
  }

  formatTime(value: string): string {
    return new Intl.DateTimeFormat("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  }
}
