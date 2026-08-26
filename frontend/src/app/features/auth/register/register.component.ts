import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';

@Component({
  standalone: true,
  imports: [RouterLink, FormsModule],
  template: `<main class="auth-shell"><section class="auth-card"><p class="eyebrow">FIAP X</p><h1>Crie sua conta</h1><input [(ngModel)]="name" placeholder="Nome"><input [(ngModel)]="email" placeholder="E-mail" type="email"><input [(ngModel)]="password" placeholder="Senha" type="password"><button (click)="register()">Cadastrar</button>@if (error) {<p class="muted">{{error}}</p>}<a routerLink="/login">Já tenho uma conta</a></section></main>`
})
export class RegisterComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  name = ''; email = ''; password = ''; error = '';
  register(): void {
    this.auth.register(this.name, this.email, this.password).subscribe({ next: () => this.router.navigateByUrl('/dashboard'), error: () => this.error = 'Não foi possível criar a conta.' });
  }
}
