import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../auth/auth.service';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthService);
  const token = auth.getToken();
  return next(token ? request.clone({setHeaders: {Authorization: `Bearer ${token}`}}) : request).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status !== 401 || request.url.includes('/auth/refresh') || !localStorage.getItem('fiapx_refresh_token')) return throwError(() => error);
      return auth.refresh().pipe(switchMap(() => next(request)), catchError((refreshError) => { auth.clear(); return throwError(() => refreshError); }));
    })
  );
};
