import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from "@angular/core";
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from "@angular/forms";
import { Router, RouterLink } from "@angular/router";
import { AuthService } from "@core/auth/auth.service";
import { RegisterRequest } from "@core/models/auth.model";

@Component({
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule],
  templateUrl: "./register.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegisterComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly formBuilder = inject(FormBuilder);

  readonly form = this.formBuilder.nonNullable.group(
    {
      name: ["", [Validators.required, Validators.minLength(2)]],
      email: ["", [Validators.required, Validators.email]],
      password: ["", [Validators.required, Validators.minLength(8)]],
      confirmPassword: ["", Validators.required],
    },
    { validators: RegisterComponent.passwordsMatch },
  );
  readonly showPassword = signal(false);
  readonly showConfirmPassword = signal(false);
  readonly loading = signal(false);
  readonly submitted = signal(false);
  readonly error = signal("");

  static passwordsMatch(control: AbstractControl): ValidationErrors | null {
    const password = control.get("password")?.value;
    const confirmPassword = control.get("confirmPassword")?.value;

    return password && confirmPassword && password !== confirmPassword
      ? { passwordsMismatch: true }
      : null;
  }

  showError(field: "name" | "email" | "password" | "confirmPassword"): boolean {
    const control = this.form.controls[field];
    const mismatch =
      field === "confirmPassword" && this.form.hasError("passwordsMismatch");

    return (
      (control.invalid || mismatch) && (control.touched || this.submitted())
    );
  }

  register(): void {
    this.submitted.set(true);
    this.error.set("");
    this.form.markAllAsTouched();

    if (this.form.invalid) return;

    const { name, email, password } = this.form.getRawValue();
    const payload: RegisterRequest = {
      name: name.trim(),
      email: email.trim(),
      password,
    };

    this.loading.set(true);
    this.auth.register(payload).subscribe({
      next: () => this.router.navigateByUrl("/dashboard"),
      error: (error) => {
        this.loading.set(false);
        this.error.set(this.registerErrorMessage(error.status));
      },
    });
  }

  private registerErrorMessage(status: number): string {
    if (status === 409) return "Este e-mail já está cadastrado.";
    if (status === 400 || status === 422)
      return "Verifique os dados informados.";
    return "Não foi possível criar sua conta. Tente novamente.";
  }
}
