import { HttpClient, HttpEvent } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { API_BASE_URL } from '../config/api.config';
import { mapVideoDto, Video, VideoResponseDto } from '../models/video.model';

export interface VideoCreateResponse { id: string; original_filename: string; status: string; progress: number; created_at: string; }
export interface VideoPageDto { items: VideoResponseDto[]; page: number; page_size: number; total: number; }

@Injectable({providedIn: 'root'})
export class VideoService {
  private readonly http = inject(HttpClient);
  list(): Observable<Video[]> { return this.http.get<VideoPageDto>(`${API_BASE_URL}/videos`).pipe(map((page) => page.items.map(mapVideoDto))); }
  upload(file: File): Observable<HttpEvent<VideoCreateResponse>> {
    const data = new FormData(); data.append('file', file); return this.http.post<VideoCreateResponse>(`${API_BASE_URL}/videos`, data, {observe: 'events', reportProgress: true});
  }
  get(id: string): Observable<Video> { return this.http.get<VideoResponseDto>(`${API_BASE_URL}/videos/${id}`).pipe(map(mapVideoDto)); }
  download(id: string): Observable<string> { return this.http.get<{url: string}>(`${API_BASE_URL}/videos/${id}/download`).pipe(map((result) => result.url)); }
}
