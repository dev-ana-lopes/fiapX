import { DatePipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';
import { AppShellComponent } from '../../core/layout/app-shell.component';
import { PageHeaderComponent } from '../../core/layout/page-header.component';
import { BreadcrumbItem, BreadcrumbsComponent } from '../../core/layout/breadcrumbs.component';
import { Video, VideoStatus } from '../../core/models/video.model';
import { VideoService } from '../../core/services/video.service';
import { DownloadButtonComponent } from '../../core/videos/download-button.component';
import { VideoPreviewCacheService } from '../../core/videos/video-preview-cache.service';

@Component({
  standalone: true,
  imports: [DatePipe, RouterLink, AppShellComponent, PageHeaderComponent, BreadcrumbsComponent, DownloadButtonComponent],
  template: `
    <app-shell>
      <app-page-header eyebrow="MEUS VÍDEOS" title="Detalhes do vídeo" subtitle="Acompanhe o processamento e acesse as imagens geradas." />
      <app-breadcrumbs [items]="breadcrumbs" />
      @if (loading()) { <div class="detail-skeleton"></div> }
      @else if (error()) { <div class="state-message error-state">{{error()}} <a routerLink="/videos">Voltar para meus vídeos</a></div> }
      @else if (video(); as item) {
        <section class="video-detail-page">
          <header class="video-detail-heading">
            <div><h2>{{item.originalFilename}}</h2></div>
            <app-download-button [video]="item" (failed)="error.set('Não foi possível iniciar o download.')" />
          </header>
          <section class="video-detail-progress" aria-label="Status do processamento">
            <div class="progress-summary"><span>STATUS DO PROCESSAMENTO</span><strong>{{item.progress}}%</strong></div>
            <div class="progress-track"><span [style.width.%]="item.progress"></span></div>
            <div class="timeline"><div class="timeline-line"></div>
              @for (step of timeline(item.status); track step.label) {
                <div class="timeline-step" [class]="step.state"><span>{{step.state === 'failed' ? '×' : step.state === 'completed' ? '✓' : '•'}}</span><b>{{step.label}}</b></div>
              }
            </div>
          </section>
          <div class="video-detail-content">
            <div class="detail-preview thumb-default">
              @if (previewUrl()) { <video class="detail-video" [src]="previewUrl()" controls preload="metadata" (error)="previewUrl.set('')"></video> }
              @else { <span class="preview-unavailable">Prévia indisponível</span> }
            </div>
            <section class="video-detail-specs" aria-label="Informações do vídeo">
              <dl>
                <dt>Status</dt><dd><b class="status" [class.success]="item.status === 'COMPLETED'" [class.queued]="item.status === 'QUEUED'" [class.failed]="item.status === 'FAILED'">● {{statusLabel(item.status)}}</b></dd>
                <dt>Imagens geradas</dt><dd>{{item.frameCount ?? '—'}}</dd>
                <dt>Enviado em</dt><dd>{{item.createdAt | date:'dd/MM/yyyy'}}</dd>
                <dt>Resolução</dt><dd>{{item.resolution ?? '—'}}</dd>
                <dt>Formato</dt><dd>{{item.format ?? '—'}}</dd>
              </dl>
            </section>
          </div>
        </section>
      }
    </app-shell>
  `,
})
export class VideoDetailsComponent {
  private readonly service = inject(VideoService);
  private readonly previewCache = inject(VideoPreviewCacheService);
  private readonly route = inject(ActivatedRoute);
  readonly video = signal<Video | null>(null);
  readonly previewUrl = signal('');
  readonly loading = signal(true);
  readonly error = signal('');
  readonly breadcrumbs: BreadcrumbItem[] = [{label:'Início', route:'/dashboard'}, {label:'Meus vídeos', route:'/videos'}, {label:'Detalhes do vídeo'}];

  constructor() {
    this.route.paramMap.subscribe((params) => {
      const id = params.get('id');
      if (!id) { this.error.set('Vídeo não encontrado.'); this.loading.set(false); return; }
      this.service.get(id).pipe(catchError(() => { this.error.set('Não foi possível carregar este vídeo.'); this.loading.set(false); return of(null); })).subscribe((item) => {
        if (item) { this.video.set(item); this.loadPreview(item.id); }
        else if (!this.error()) this.error.set('Vídeo não encontrado.');
        this.loading.set(false);
      });
    });
  }

  private loadPreview(videoId: string): void { this.previewCache.get(videoId).pipe(catchError(() => of(''))).subscribe((url) => this.previewUrl.set(url)); }
  statusLabel(status: VideoStatus): string { return {UPLOADING: 'Enviando', QUEUED: 'Na fila', PROCESSING: 'Processando', COMPLETED: 'Concluído', FAILED: 'Falhou'}[status]; }
  timeline(status: VideoStatus) {
    const order: VideoStatus[] = ['UPLOADING', 'QUEUED', 'PROCESSING', 'COMPLETED'];
    const current = order.indexOf(status);
    return [{label: 'Enviado', state: 'completed'}, {label: 'Na fila', state: current >= 1 ? 'completed' : status === 'FAILED' ? 'failed' : 'pending'}, {label: 'Processando', state: status === 'FAILED' ? 'failed' : current > 2 ? 'completed' : current === 2 ? 'active' : 'pending'}, {label: 'Concluído', state: status === 'COMPLETED' ? 'completed' : 'pending'}];
  }
}
