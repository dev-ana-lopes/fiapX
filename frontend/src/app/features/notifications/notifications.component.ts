import { Component, inject, signal } from '@angular/core';
import { AppShellComponent } from '../../core/layout/app-shell.component';
import { Notification } from '../../core/models/notification.model';
import { groupNotifications, notificationIconClass } from '../../core/models/notification.utils';
import { NotificationService } from '../../core/services/notification.service';

@Component({
  standalone: true,
  imports: [AppShellComponent],
  template: `
    <app-shell>
      <header class="notifications-header">
        <div><p class="page-kicker">CENTRAL DE ATIVIDADES</p><h1>Notificações</h1></div>
        <button class="text-button" [disabled]="unreadCount() === 0 || loading()" (click)="markAllRead()">
          MARCAR TODAS COMO LIDAS
        </button>
      </header>

      @if (loading()) {
        <div class="state-message">Carregando notificações…</div>
      } @else if (error()) {
        <div class="state-message error-state">{{error()}} <button class="text-button" (click)="load()">Tentar novamente</button></div>
      } @else if (notifications().length === 0) {
        <div class="empty-state"><h2>Nenhuma notificação</h2><p class="muted">Você será avisado quando houver novidades sobre seus vídeos.</p></div>
      } @else {
        @for (group of groups(); track group.label) {
          <section class="notification-group"><h3>{{group.label}}</h3>
            @for (item of group.items; track item.id) {
              <article class="notification-item" [class.notification-unread]="item.status === 'PENDING'" (click)="markRead(item)">
                <span class="notification-icon" [class]="iconClass(item)">{{icon(item)}}</span>
                <div><strong>{{item.title || 'Atualização do processamento'}}</strong><p>{{item.message || 'Há uma atualização sobre seu vídeo.'}}</p></div>
                <time>{{formatTime(item.createdAt)}}</time>
                @if (item.status === 'PENDING') { <i class="unread" aria-label="Não lida"></i> }
              </article>
            }
          </section>
        }
      }
    </app-shell>
  `,
})
export class NotificationsComponent {
  private readonly service = inject(NotificationService);
  readonly notifications = signal<Notification[]>([]);
  readonly unreadCount = signal(0);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);

  constructor() { this.load(); }

  groups(): Array<{label: string; items: Notification[]}> {
    return groupNotifications(this.notifications());
  }

  load(): void {
    this.loading.set(true); this.error.set(null);
    this.service.list().subscribe({
      next: (page) => { this.notifications.set(page.items); this.unreadCount.set(page.unreadCount); this.loading.set(false); },
      error: () => { this.error.set('Não foi possível carregar as notificações.'); this.loading.set(false); },
    });
  }

  markRead(item: Notification): void {
    if (item.status !== 'PENDING') return;
    this.service.markRead(item.id).subscribe({
      next: () => {
        item.status = 'READ'; item.readAt = new Date().toISOString();
        this.notifications.update((items) => [...items]);
        this.unreadCount.update((count) => Math.max(0, count - 1));
      },
    });
  }

  markAllRead(): void {
    this.service.markAllRead().subscribe({
      next: () => {
        const now = new Date().toISOString();
        this.notifications.update((items) => items.map((item) => ({...item, status: 'READ', readAt: now})));
        this.unreadCount.set(0);
      },
    });
  }

  iconClass(item: Notification): string { return notificationIconClass(item.type); }
  icon(item: Notification): string { return item.type === 'VIDEO_FAILED' ? '×' : item.type === 'VIDEO_COMPLETED' ? '✓' : 'i'; }
  formatTime(value: string): string { return new Intl.DateTimeFormat('pt-BR', {hour: '2-digit', minute: '2-digit'}).format(new Date(value)); }
}
