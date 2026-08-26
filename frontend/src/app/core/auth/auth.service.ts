import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { API_BASE_URL } from '../config/api.config';

@Injectable({providedIn: 'root'})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly accessToken = signal<string | null>(localStorage.getItem('fiapx_access_token'));
  readonly isAuthenticated = computed(() => this.accessToken() !== null);

  getToken(): string | null { return this.accessToken(); }
  setToken(token: string): void { localStorage.setItem('fiapx_access_token', token); this.accessToken.set(token); }
  clear(): void { localStorage.removeItem('fiapx_access_token'); localStorage.removeItem('fiapx_refresh_token'); this.accessToken.set(null); }
  refresh(): Observable<{access_token: string; refresh_token: string}> {
    return this.http.post<{access_token: string; refresh_token: string}>(`${API_BASE_URL}/auth/refresh`, {refresh_token: localStorage.getItem('fiapx_refresh_token')}).pipe(tap((result) => { this.setToken(result.access_token); localStorage.setItem('fiapx_refresh_token', result.refresh_token); }));
  }
  login(email: string, password: string): Observable<{access_token: string; refresh_token: string}> {
    return this.http.post<{access_token: string; refresh_token: string}>(`${API_BASE_URL}/auth/login`, {email, password}).pipe(tap((result) => { this.setToken(result.access_token); localStorage.setItem('fiapx_refresh_token', result.refresh_token); }));
  }
  register(name: string, email: string, password: string): Observable<{access_token: string; refresh_token: string}> {
    return this.http.post<{access_token: string; refresh_token: string}>(`${API_BASE_URL}/auth/register`, {name, email, password}).pipe(tap((result) => { this.setToken(result.access_token); localStorage.setItem('fiapx_refresh_token', result.refresh_token); }));
  }
}
