import { HttpClient, HttpEvent } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { EMPTY, Observable, expand, map, reduce } from 'rxjs';
import { API_BASE_URL } from '../config/api.config';
import { mapVideoDto, Video, VideoResponseDto } from '../models/video.model';

export interface VideoCreateResponse { id: string; original_filename: string; status: string; progress: number; created_at: string; }
export interface VideoPageDto { items: VideoResponseDto[]; page: number; page_size: number; total: number; }

@Injectable({providedIn: 'root'})
export class VideoService {
  private readonly http = inject(HttpClient);
  list(): Observable<Video[]> {
    const pageSize = 100;
    return this.listPage(1, pageSize).pipe(
      expand((page) => page.page * page.page_size < page.total ? this.listPage(page.page + 1, pageSize) : EMPTY),
      reduce((videos, page) => [...videos, ...page.items.map(mapVideoDto)], [] as Video[]),
      map((videos) => videos.sort((first, second) => new Date(second.createdAt).getTime() - new Date(first.createdAt).getTime())),
    );
  }
  upload(file: File): Observable<HttpEvent<VideoCreateResponse>> {
    const data = new FormData(); data.append('file', file); return this.http.post<VideoCreateResponse>(`${API_BASE_URL}/videos`, data, {observe: 'events', reportProgress: true});
  }
  get(id: string): Observable<Video> { return this.http.get<VideoResponseDto>(`${API_BASE_URL}/videos/${id}`).pipe(map(mapVideoDto)); }
  download(id: string): Observable<Blob> { return this.http.get(`${API_BASE_URL}/videos/${id}/download/file`, {responseType: 'blob'}); }
  preview(id: string): Observable<Blob> { return this.http.get(`${API_BASE_URL}/videos/${id}/preview`, {responseType: 'blob'}); }
  thumbnail(id: string): Observable<Blob> { return this.http.get(`${API_BASE_URL}/videos/${id}/thumbnail`, {responseType: 'blob'}); }
  private listPage(page: number, pageSize: number): Observable<VideoPageDto> { return this.http.get<VideoPageDto>(`${API_BASE_URL}/videos`, {params: {page, page_size: pageSize}}); }
}
