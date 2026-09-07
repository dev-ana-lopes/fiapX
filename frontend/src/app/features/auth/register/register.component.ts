import { Component, inject, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';
import { RegisterRequest } from '../../../core/models/auth.model';

@Component({
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule],
  template: `<main class="login-shell"><div class="login-glow"></div><section class="login-card register-card" aria-labelledby="register-title"><a class="auth-brand" routerLink="/login" aria-label="FIAP X - voltar para login"><span>FIAP</span> X</a><h1 id="register-title">Crie sua conta</h1><p class="muted auth-intro">Preencha seus dados para começar</p><form [formGroup]="form" (ngSubmit)="register()" novalidate><label for="name">Nome<input id="name" formControlName="name" autocomplete="name" placeholder="Seu nome" [class.invalid]="showError('name')">@if(showError('name')){<small class="field-error">Informe seu nome.</small>}</label><label for="email">E-mail<input id="email" formControlName="email" autocomplete="email" type="email" placeholder="seu@email.com" [class.invalid]="showError('email')">@if(showError('email')){<small class="field-error">Informe um e-mail válido.</small>}</label><label for="password">Senha<div class="password-field"><input id="password" formControlName="password" autocomplete="new-password" [type]="showPassword() ? 'text' : 'password'" placeholder="••••••••" [class.invalid]="showError('password')"><button type="button" [attr.aria-label]="showPassword() ? 'Ocultar senha' : 'Mostrar senha'" (click)="showPassword.set(!showPassword())">{{showPassword() ? '◉' : '◌'}}</button></div>@if(showError('password')){<small class="field-error">A senha deve ter pelo menos 8 caracteres.</small>}</label><label for="confirmPassword">Confirmar senha<div class="password-field"><input id="confirmPassword" formControlName="confirmPassword" autocomplete="new-password" [type]="showConfirmPassword() ? 'text' : 'password'" placeholder="••••••••" [class.invalid]="showError('confirmPassword')"><button type="button" [attr.aria-label]="showConfirmPassword() ? 'Ocultar confirmação de senha' : 'Mostrar confirmação de senha'" (click)="showConfirmPassword.set(!showConfirmPassword())">{{showConfirmPassword() ? '◉' : '◌'}}</button></div>@if(showError('confirmPassword')){<small class="field-error">As senhas precisam ser iguais.</small>}</label>@if(error()){<p class="field-error form-error" role="alert">{{error()}}</p>}<button class="primary-button login-button" type="submit" [disabled]="loading()">@if(loading()){<span class="button-spinner" aria-hidden="true"></span>}{{loading() ? 'CRIANDO CONTA…' : 'CRIAR CONTA'}}</button></form><p class="login-footer">Já possui uma conta? <a routerLink="/login">Entrar</a></p></section></main>`
})
export class RegisterComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', Validators.required]
  }, { validators: RegisterComponent.passwordsMatch });
  readonly showPassword = signal(false);
  readonly showConfirmPassword = signal(false);
  readonly loading = signal(false);
  readonly submitted = signal(false);
  readonly error = signal('');

  static passwordsMatch(control: AbstractControl): ValidationErrors | null {
    const password = control.get('password')?.value;
    const confirmPassword = control.get('confirmPassword')?.value;
    return password && confirmPassword && password !== confirmPassword ? { passwordsMismatch: true } : null;
  }

  showError(field: 'name' | 'email' | 'password' | 'confirmPassword'): boolean {
    const control = this.form.controls[field];
    const mismatch = field === 'confirmPassword' && this.form.hasError('passwordsMismatch');
    return (control.invalid || mismatch) && (control.touched || this.submitted());
  }

  register(): void {
    this.submitted.set(true);
    this.error.set('');
    this.form.markAllAsTouched();
    if (this.form.invalid) return;
    const { name, email, password } = this.form.getRawValue();
    const payload: RegisterRequest = { name: name.trim(), email: email.trim(), password };
    this.loading.set(true);
    this.auth.register(payload).subscribe({
      next: () => this.router.navigateByUrl('/dashboard'),
      error: (err) => {
        this.loading.set(false);
        this.error.set(err.status === 409 ? 'Este e-mail já está cadastrado.' : err.status === 400 || err.status === 422 ? 'Verifique os dados informados.' : 'Não foi possível criar sua conta. Tente novamente.');
      }
    });
  }
}
