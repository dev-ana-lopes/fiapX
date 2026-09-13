import {
  ChangeDetectionStrategy,
  Component,
  inject,
  input,
  output,
} from "@angular/core";
import { Router, RouterLink, RouterLinkActive } from "@angular/router";
import { AuthService } from "../auth/auth.service";

@Component({
  selector: "app-shell",
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  templateUrl: "./app-shell.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppShellComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  readonly menuOpen = input(false);
  readonly toggleMenu = output<void>();
  readonly closeMenu = output<void>();

  logout(): void {
    this.auth.logout().subscribe({
      next: () => this.router.navigateByUrl("/login"),
      error: () => this.router.navigateByUrl("/login"),
    });
  }
}
