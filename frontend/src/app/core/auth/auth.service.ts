import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { Observable, catchError, tap, throwError } from 'rxjs';
import { API_BASE_URL } from '../config/api.config';
import { AuthResponse, CurrentUser, RegisterRequest } from '../models/auth.model';

@Injectable({providedIn: 'root'})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly accessToken = signal<string | null>(localStorage.getItem('fiapx_access_token'));
  readonly currentUser = signal<CurrentUser | null>(this.readStoredUser());
  readonly isAuthenticated = computed(() => this.accessToken() !== null);

  getToken(): string | null { return this.accessToken(); }
  setToken(token: string): void { localStorage.setItem('fiapx_access_token', token); this.accessToken.set(token); }
  clear(): void { localStorage.removeItem('fiapx_access_token'); localStorage.removeItem('fiapx_current_user'); this.accessToken.set(null); this.currentUser.set(null); }
  loadCurrentUser(): Observable<CurrentUser> { return this.http.get<CurrentUser>(`${API_BASE_URL}/auth/me`).pipe(tap((user) => this.storeUser(user))); }
  refresh(): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${API_BASE_URL}/auth/refresh`, {}, {withCredentials: true}).pipe(tap((result) => this.setToken(result.access_token)));
  }
  login(email: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${API_BASE_URL}/auth/login`, {email, password}, {withCredentials: true}).pipe(tap((result) => this.setToken(result.access_token)));
  }
  register(payload: RegisterRequest): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${API_BASE_URL}/auth/register`, payload, {withCredentials: true}).pipe(tap((result) => this.setToken(result.access_token)));
  }
  logout(): Observable<void> {
    return this.http.post<void>(`${API_BASE_URL}/auth/logout`, {}, {withCredentials: true}).pipe(
      tap(() => this.clear()),
      catchError((error) => { this.clear(); return throwError(() => error); }),
    );
  }
  private storeUser(user: CurrentUser): void { localStorage.setItem('fiapx_current_user', JSON.stringify(user)); this.currentUser.set(user); }
  private readStoredUser(): CurrentUser | null { try { return JSON.parse(localStorage.getItem('fiapx_current_user') || 'null') as CurrentUser | null; } catch { localStorage.removeItem('fiapx_current_user'); return null; } }
}
