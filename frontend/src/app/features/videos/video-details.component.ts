import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from "@angular/core";
import { DatePipe } from "@angular/common";
import { ActivatedRoute, RouterLink } from "@angular/router";
import { catchError, of } from "rxjs";
import {
  BreadcrumbItem,
  BreadcrumbsComponent,
} from "@core/layout/breadcrumbs.component";
import { AppShellComponent } from "@core/layout/app-shell.component";
import { PageHeaderComponent } from "@core/layout/page-header.component";
import { Video, VideoStatus } from "@core/models/video.model";
import { VideoService } from "@core/services/video.service";
import { DownloadButtonComponent } from "@core/videos/download-button.component";
import { VideoPreviewCacheService } from "@core/videos/video-preview-cache.service";

interface TimelineStep {
  label: string;
  state: "active" | "completed" | "failed" | "pending";
}

@Component({
  standalone: true,
  imports: [
    DatePipe,
    RouterLink,
    AppShellComponent,
    PageHeaderComponent,
    BreadcrumbsComponent,
    DownloadButtonComponent,
  ],
  templateUrl: "./video-details.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VideoDetailsComponent {
  private readonly service = inject(VideoService);
  private readonly previewCache = inject(VideoPreviewCacheService);
  private readonly route = inject(ActivatedRoute);

  readonly video = signal<Video | null>(null);
  readonly previewUrl = signal("");
  readonly loading = signal(true);
  readonly error = signal("");
  readonly breadcrumbs: BreadcrumbItem[] = [
    { label: "Início", route: "/dashboard" },
    { label: "Meus vídeos", route: "/videos" },
    { label: "Detalhes do vídeo" },
  ];

  constructor() {
    this.route.paramMap.subscribe((params) => {
      const id = params.get("id");
      if (!id) {
        this.error.set("Vídeo não encontrado.");
        this.loading.set(false);
        return;
      }
      this.service
        .get(id)
        .pipe(
          catchError(() => {
            this.error.set("Não foi possível carregar este vídeo.");
            this.loading.set(false);
            return of(null);
          }),
        )
        .subscribe((video) => {
          if (video) {
            this.video.set(video);
            this.loadPreview(video.id);
          } else if (!this.error()) {
            this.error.set("Vídeo não encontrado.");
          }
          this.loading.set(false);
        });
    });
  }

  statusLabel(status: VideoStatus): string {
    return {
      UPLOADING: "Enviando",
      QUEUED: "Na fila",
      PROCESSING: "Processando",
      COMPLETED: "Concluído",
      FAILED: "Falhou",
    }[status];
  }

  timeline(status: VideoStatus): TimelineStep[] {
    const order: VideoStatus[] = [
      "UPLOADING",
      "QUEUED",
      "PROCESSING",
      "COMPLETED",
    ];
    const current = order.indexOf(status);

    return [
      { label: "Enviado", state: "completed" },
      {
        label: "Na fila",
        state:
          current >= 1
            ? "completed"
            : status === "FAILED"
              ? "failed"
              : "pending",
      },
      {
        label: "Processando",
        state:
          status === "FAILED"
            ? "failed"
            : current > 2
              ? "completed"
              : current === 2
                ? "active"
                : "pending",
      },
      {
        label: "Concluído",
        state: status === "COMPLETED" ? "completed" : "pending",
      },
    ];
  }

  private loadPreview(videoId: string): void {
    this.previewCache
      .get(videoId)
      .pipe(catchError(() => of("")))
      .subscribe((url) => this.previewUrl.set(url));
  }
}
