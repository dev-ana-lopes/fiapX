import { DatePipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';
import { AppShellComponent } from '../../core/layout/app-shell.component';
import { PageHeaderComponent } from '../../core/layout/page-header.component';
import { BreadcrumbItem, BreadcrumbsComponent } from '../../core/layout/breadcrumbs.component';
import { Video } from '../../core/models/video.model';
import { VideoService } from '../../core/services/video.service';
import { DownloadButtonComponent } from '../../core/videos/download-button.component';

@Component({
  standalone: true,
  imports: [DatePipe, RouterLink, AppShellComponent, PageHeaderComponent, BreadcrumbsComponent, DownloadButtonComponent],
  template: `
    <app-shell>
      <app-page-header eyebrow="BIBLIOTECA" title="Meus vídeos" subtitle="Consulte seus vídeos processados e baixe as imagens geradas." />
      <app-breadcrumbs [items]="breadcrumbs" />
      @if (loading()) { <div class="video-list-skeleton">@for (item of [1, 2, 3]; track item) { <div class="video-list-row skeleton-row"><span></span><span></span><span></span></div> }</div> }
      @if (!loading() && error()) { <div class="state-message error-state" role="alert">{{error()}} <button class="text-button" (click)="load()">TENTAR NOVAMENTE</button></div> }
      @if (!loading() && !error() && !videos().length) { <div class="empty-state"><h2>Nenhum vídeo processado ainda.</h2><p class="muted">Os vídeos concluídos aparecerão aqui.</p></div> }
      @if (!loading() && videos().length) {
        <section class="video-list" aria-label="Vídeos processados">
          <div class="video-list-header"><span>ID</span><span>VÍDEO</span><span>DATA DE IMPORTAÇÃO</span><span>STATUS</span><span>AÇÕES</span></div>
          @for (video of videos(); track video.id) {
            <div class="video-list-row">
              <span class="video-list-id" [title]="video.id">{{video.id}}</span>
              <a class="video-list-main" [routerLink]="['/videos', video.id]">
                <div class="list-thumb thumb-default">@if (thumbnailUrls()[video.id]) { <img class="thumb-image" [src]="thumbnailUrls()[video.id]" alt="Prévia do vídeo"> }</div>
                <strong class="truncate">{{video.originalFilename}}</strong>
              </a>
              <time [attr.datetime]="video.createdAt">{{video.createdAt | date:'dd/MM/yyyy HH:mm'}}</time>
              <b class="status success">● Concluído</b>
              <app-download-button [video]="video" (failed)="error.set('Não foi possível iniciar o download.')" />
            </div>
          }
        </section>
        @if (totalPages() > 1) {
          <nav class="video-pagination" aria-label="Paginação de vídeos">
            <button class="pagination-button" [disabled]="page() === 1" (click)="goToPage(page() - 1)">‹ ANTERIOR</button>
            <span>Página <strong>{{page()}}</strong> de <strong>{{totalPages()}}</strong></span>
            <button class="pagination-button" [disabled]="page() === totalPages()" (click)="goToPage(page() + 1)">PRÓXIMA ›</button>
          </nav>
        }
      }
    </app-shell>
  `,
})
export class MyVideosComponent {
  private readonly service = inject(VideoService);
  private readonly destroyRef = inject(DestroyRef);
  readonly allVideos = signal<Video[]>([]);
  readonly page = signal(1);
  readonly pageSize = 10;
  readonly completedVideos = computed(() => this.allVideos().filter((item) => item.status === 'COMPLETED'));
  readonly totalPages = computed(() => Math.max(1, Math.ceil(this.completedVideos().length / this.pageSize)));
  readonly videos = computed(() => {
    const first = (this.page() - 1) * this.pageSize;
    return this.completedVideos().slice(first, first + this.pageSize);
  });
  readonly thumbnailUrls = signal<Record<string, string>>({});
  readonly loading = signal(true);
  readonly error = signal('');
  readonly breadcrumbs: BreadcrumbItem[] = [{label:'Início', route:'/dashboard'}, {label:'Meus vídeos'}];
  private readonly thumbnailRequests = new Set<string>();

  constructor() {
    this.destroyRef.onDestroy(() => Object.values(this.thumbnailUrls()).forEach((url) => URL.revokeObjectURL(url)));
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set('');
    this.service.list().pipe(catchError(() => { this.error.set('Não foi possível carregar seus vídeos.'); return of([] as Video[]); }), takeUntilDestroyed(this.destroyRef)).subscribe((items) => {
      this.allVideos.set(items);
      if (this.page() > this.totalPages()) this.page.set(this.totalPages());
      this.loading.set(false);
      this.loadThumbnails(this.videos());
    });
  }

  private loadThumbnails(items: Video[]): void {
    for (const video of items) {
      if (this.thumbnailUrls()[video.id] || this.thumbnailRequests.has(video.id)) continue;
      this.thumbnailRequests.add(video.id);
      this.service.thumbnail(video.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (blob) => this.thumbnailUrls.update((urls) => ({...urls, [video.id]: URL.createObjectURL(blob)})),
        complete: () => this.thumbnailRequests.delete(video.id),
        error: () => this.thumbnailRequests.delete(video.id),
      });
    }
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages()) return;
    this.page.set(page);
    this.loadThumbnails(this.videos());
  }
}
