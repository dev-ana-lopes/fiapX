import { HttpErrorResponse, HttpInterceptorFn } from "@angular/common/http";
import { inject } from "@angular/core";
import { catchError, finalize, shareReplay, switchMap, throwError } from "rxjs";
import { AuthService } from "../auth/auth.service";

let refreshInFlight: ReturnType<AuthService["refresh"]> | null = null;

export const authInterceptor: HttpInterceptorFn = (request, next) => {
  const auth = inject(AuthService);
  const token = auth.getToken();
  const authenticatedRequest = request.clone({
    withCredentials: true,
    ...(token ? { setHeaders: { Authorization: `Bearer ${token}` } } : {}),
  });
  return next(authenticatedRequest).pipe(
    catchError((error: HttpErrorResponse) => {
      if (
        error.status !== 401 ||
        request.url.includes("/auth/refresh") ||
        !token
      )
        return throwError(() => error);
      if (!refreshInFlight) {
        refreshInFlight = auth.refresh().pipe(
          shareReplay({ bufferSize: 1, refCount: true }),
          finalize(() => {
            refreshInFlight = null;
          }),
        );
      }
      return refreshInFlight.pipe(
        switchMap(() => {
          const refreshed = auth.getToken();
          return next(
            refreshed
              ? request.clone({
                  withCredentials: true,
                  setHeaders: { Authorization: `Bearer ${refreshed}` },
                })
              : request,
          );
        }),
        catchError((refreshError) => {
          auth.clear();
          return throwError(() => refreshError);
        }),
      );
    }),
  );
};
