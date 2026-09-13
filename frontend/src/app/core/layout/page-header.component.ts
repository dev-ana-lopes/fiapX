import { Component, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';
import { AuthService } from '../auth/auth.service';
import { NotificationBellComponent } from '../notifications/notification-bell.component';

@Component({
  selector: 'app-page-header',
  standalone: true,
  imports: [RouterLink, NotificationBellComponent],
  template: `<header class="topbar page-header"><div class="page-header-copy"><p class="page-kicker">{{eyebrow()}}</p><h1>{{title()}}</h1><p class="muted">{{subtitle()}}</p></div><div class="top-actions page-header-actions"><a class="primary-button new-video-button" routerLink="/dashboard" [queryParams]="{upload: 'true'}">＋ &nbsp;NOVO VÍDEO</a><app-notification-bell /><span class="avatar" aria-hidden="true">{{userInitials()}}</span><span class="user-name">{{auth.currentUser()?.name || 'Usuário'}}</span></div></header>`,
})
export class PageHeaderComponent {
  readonly eyebrow = input('');
  readonly title = input('');
  readonly subtitle = input('');
  readonly auth = inject(AuthService);

  constructor() { this.auth.loadCurrentUser().pipe(catchError(() => of(null))).subscribe(); }

  userInitials(): string {
    const name = this.auth.currentUser()?.name?.trim();
    return name ? name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() : 'US';
  }
}
