import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../auth/auth.service';

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthService);
  const token = auth.getToken();
  const authenticatedRequest = request.clone({
    withCredentials: true,
    ...(token ? {setHeaders: {Authorization: `Bearer ${token}`}} : {}),
  });
  return next(authenticatedRequest).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status !== 401 || request.url.includes('/auth/refresh') || !token) return throwError(() => error);
      return auth.refresh().pipe(switchMap(() => {
        const refreshed = auth.getToken();
        return next(refreshed ? request.clone({withCredentials: true, setHeaders: {Authorization: `Bearer ${refreshed}`}}) : request);
      }), catchError((refreshError) => { auth.clear(); return throwError(() => refreshError); }));
    })
  );
};
