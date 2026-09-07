import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { API_BASE_URL } from '../config/api.config';
import { mapNotificationDto, Notification, NotificationPageDto } from '../models/notification.model';

@Injectable({providedIn: 'root'})
export class NotificationService {
  private readonly http = inject(HttpClient);

  list(): Observable<{items: Notification[]; unreadCount: number}> {
    return this.http.get<NotificationPageDto>(`${API_BASE_URL}/notifications`).pipe(
      map((page) => ({items: page.items.map(mapNotificationDto), unreadCount: page.unread_count})),
    );
  }

  markRead(id: string): Observable<void> {
    return this.http.patch<void>(`${API_BASE_URL}/notifications/${id}/read`, {});
  }

  markAllRead(): Observable<void> {
    return this.http.post<void>(`${API_BASE_URL}/notifications/read-all`, {});
  }
}
