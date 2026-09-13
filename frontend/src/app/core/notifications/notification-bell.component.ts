import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from "@angular/core";
import { Router } from "@angular/router";
import { catchError, of } from "rxjs";
import { Notification } from "../models/notification.model";
import { notificationIconClass } from "../models/notification.utils";
import { NotificationService } from "../services/notification.service";

@Component({
  selector: "app-notification-bell",
  standalone: true,
  templateUrl: "./notification-bell.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotificationBellComponent {
  private readonly service = inject(NotificationService);
  private readonly router = inject(Router);
  readonly open = signal(false);
  readonly loading = signal(false);
  readonly error = signal("");
  readonly notifications = signal<Notification[]>([]);
  readonly unreadCount = signal(0);

  toggle(event: Event): void {
    event.stopPropagation();
    this.open.update((value) => !value);

    if (this.open()) this.load();
  }

  close(): void {
    this.open.set(false);
  }

  load(): void {
    this.loading.set(true);
    this.error.set("");
    this.service
      .list()
      .pipe(
        catchError(() => {
          this.error.set("Não foi possível carregar as notificações.");
          return of({ items: [] as Notification[], unreadCount: 0 });
        }),
      )
      .subscribe((page) => {
        this.notifications.set(page.items.slice(0, 8));
        this.unreadCount.set(page.unreadCount);
        this.loading.set(false);
      });
  }

  openVideos(item: Notification): void {
    const navigateToVideo = () => this.goToVideo(item.videoId);

    if (item.status === "PENDING") {
      this.service.markRead(item.id).subscribe({
        complete: navigateToVideo,
        error: navigateToVideo,
      });
      return;
    }

    navigateToVideo();
  }

  markAllRead(): void {
    this.service.markAllRead().subscribe({
      next: () => {
        const now = new Date().toISOString();
        this.notifications.update((items) =>
          items.map((item) => ({ ...item, status: "READ", readAt: now })),
        );
        this.unreadCount.set(0);
      },
    });
  }

  goToVideos(): void {
    this.close();
    this.router.navigateByUrl("/videos");
  }

  goToVideo(videoId: string): void {
    this.close();
    this.router.navigate(["/videos", videoId]);
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
