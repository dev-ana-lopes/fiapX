import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
} from "@angular/core";
import { RouterLink } from "@angular/router";
import { catchError, of } from "rxjs";
import { AuthService } from "../auth/auth.service";
import { NotificationBellComponent } from "../notifications/notification-bell.component";

@Component({
  selector: "app-page-header",
  standalone: true,
  imports: [RouterLink, NotificationBellComponent],
  templateUrl: "./page-header.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PageHeaderComponent {
  readonly eyebrow = input("");
  readonly title = input("");
  readonly subtitle = input("");
  readonly auth = inject(AuthService);
  readonly userInitials = computed(() => {
    const name = this.auth.currentUser()?.name?.trim();

    return name
      ? name
          .split(/\s+/)
          .slice(0, 2)
          .map((part) => part[0])
          .join("")
          .toUpperCase()
      : "US";
  });

  constructor() {
    this.auth
      .loadCurrentUser()
      .pipe(catchError(() => of(null)))
      .subscribe();
  }
}
