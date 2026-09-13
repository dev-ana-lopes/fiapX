import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, of } from 'rxjs';
import { Notification } from '../models/notification.model';
import { notificationIconClass } from '../models/notification.utils';
import { NotificationService } from '../services/notification.service';

@Component({
  selector: 'app-notification-bell',
  standalone: true,
  template: `
    <button class="icon-button" aria-label="Notificações" [attr.aria-expanded]="open()" (click)="toggle($event)">
      🔔 @if(unreadCount()){<i>{{unreadCount()}}</i>}
    </button>
    @if(open()) {
      <div class="notification-backdrop" (click)="close()">
        <section class="notification-popover" role="dialog" aria-modal="true" aria-labelledby="notification-title" (click)="$event.stopPropagation()">
          <header class="notification-popover-header"><div><p class="page-kicker">CENTRAL DE ATIVIDADES</p><h2 id="notification-title">Notificações</h2></div><button class="close-button" aria-label="Fechar notificações" (click)="close()">×</button></header>
          @if(loading()){<p class="muted notification-loading">Carregando notificações…</p>}
          @else if(error()){<p class="field-error">{{error()}}</p>}
          @else if(!notifications().length){<p class="muted notification-empty">Nenhuma notificação nova.</p>}
          @else {<div class="notification-popover-list">@for(item of notifications();track item.id){<button class="notification-popover-item" [class.notification-unread]="item.status==='PENDING'" (click)="openVideos(item)"><span class="notification-icon" [class]="iconClass(item)">{{icon(item)}}</span><span class="notification-copy"><strong>{{item.title || 'Atualização do processamento'}}</strong><small>{{item.message || 'Há uma atualização sobre seu vídeo.'}}</small><time>{{formatTime(item.createdAt)}}</time></span></button>}</div>}
          <footer class="notification-popover-footer"><button class="text-button" [disabled]="!unreadCount() || loading()" (click)="markAllRead()">MARCAR TODAS COMO LIDAS</button><button class="text-button" (click)="goToVideos()">VER MEUS VÍDEOS</button></footer>
        </section>
      </div>
    }
  `,
})
export class NotificationBellComponent {
  private readonly service = inject(NotificationService);
  private readonly router = inject(Router);
  readonly open = signal(false);
  readonly loading = signal(false);
  readonly error = signal('');
  readonly notifications = signal<Notification[]>([]);
  readonly unreadCount = signal(0);

  toggle(event: Event): void { event.stopPropagation(); this.open.update((value) => !value); if (this.open()) this.load(); }
  close(): void { this.open.set(false); }
  load(): void { this.loading.set(true); this.error.set(''); this.service.list().pipe(catchError(() => { this.error.set('Não foi possível carregar as notificações.'); return of({items: [] as Notification[], unreadCount: 0}); })).subscribe((page) => { this.notifications.set(page.items.slice(0, 8)); this.unreadCount.set(page.unreadCount); this.loading.set(false); }); }
  openVideos(item: Notification): void { const navigateToVideo = () => this.goToVideo(item.videoId); if (item.status === 'PENDING') { this.service.markRead(item.id).subscribe({complete: navigateToVideo, error: navigateToVideo}); } else navigateToVideo(); }
  markAllRead(): void { this.service.markAllRead().subscribe({next: () => { const now = new Date().toISOString(); this.notifications.update((items) => items.map((item) => ({...item, status: 'READ', readAt: now}))); this.unreadCount.set(0); }}); }
  goToVideos(): void { this.close(); this.router.navigateByUrl('/videos'); }
  goToVideo(videoId: string): void { this.close(); this.router.navigate(['/videos', videoId]); }
  iconClass(item: Notification): string { return notificationIconClass(item.type); }
  icon(item: Notification): string { return item.type === 'VIDEO_FAILED' ? '×' : item.type === 'VIDEO_COMPLETED' ? '✓' : 'i'; }
  formatTime(value: string): string { return new Intl.DateTimeFormat('pt-BR', {hour: '2-digit', minute: '2-digit'}).format(new Date(value)); }
}
