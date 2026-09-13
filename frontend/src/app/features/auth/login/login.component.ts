import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from "@angular/core";
import { FormsModule } from "@angular/forms";
import { Router, RouterLink } from "@angular/router";
import { AuthService } from "@core/auth/auth.service";

@Component({
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: "./login.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  email = "";
  password = "";
  readonly showPassword = signal(false);
  readonly loading = signal(false);
  readonly error = signal("");

  login(): void {
    this.loading.set(true);
    this.error.set("");
    this.auth.login(this.email, this.password).subscribe({
      next: () => this.router.navigateByUrl("/dashboard"),
      error: (error) => {
        this.loading.set(false);
        this.error.set(
          error.status === 401
            ? "E-mail ou senha inválidos."
            : "Não foi possível entrar agora.",
        );
      },
    });
  }
}
