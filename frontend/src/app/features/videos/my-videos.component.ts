import { DatePipe } from "@angular/common";
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  signal,
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { catchError, of } from "rxjs";
import { RouterLink } from "@angular/router";
import {
  BreadcrumbItem,
  BreadcrumbsComponent,
} from "@core/layout/breadcrumbs.component";
import { AppShellComponent } from "@core/layout/app-shell.component";
import { PageHeaderComponent } from "@core/layout/page-header.component";
import { Video } from "@core/models/video.model";
import { VideoService } from "@core/services/video.service";
import { DownloadButtonComponent } from "@core/videos/download-button.component";

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
  templateUrl: "./my-videos.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MyVideosComponent {
  private readonly service = inject(VideoService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly thumbnailRequests = new Set<string>();

  readonly allVideos = signal<Video[]>([]);
  readonly page = signal(1);
  readonly pageSize = 10;
  readonly completedVideos = computed(() =>
    this.allVideos().filter((item) => item.status === "COMPLETED"),
  );
  readonly totalPages = computed(() =>
    Math.max(1, Math.ceil(this.completedVideos().length / this.pageSize)),
  );
  readonly videos = computed(() => {
    const first = (this.page() - 1) * this.pageSize;
    return this.completedVideos().slice(first, first + this.pageSize);
  });
  readonly thumbnailUrls = signal<Record<string, string>>({});
  readonly loading = signal(true);
  readonly error = signal("");
  readonly breadcrumbs: BreadcrumbItem[] = [
    { label: "Início", route: "/dashboard" },
    { label: "Meus vídeos" },
  ];

  constructor() {
    this.destroyRef.onDestroy(() =>
      Object.values(this.thumbnailUrls()).forEach((url) =>
        URL.revokeObjectURL(url),
      ),
    );
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set("");
    this.service
      .list()
      .pipe(
        catchError(() => {
          this.error.set("Não foi possível carregar seus vídeos.");
          return of([] as Video[]);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((items) => {
        this.allVideos.set(items);
        if (this.page() > this.totalPages()) this.page.set(this.totalPages());
        this.loading.set(false);
        this.loadThumbnails(this.videos());
      });
  }

  goToPage(page: number): void {
    if (page < 1 || page > this.totalPages()) return;
    this.page.set(page);
    this.loadThumbnails(this.videos());
  }

  private loadThumbnails(items: Video[]): void {
    for (const video of items) {
      if (
        this.thumbnailUrls()[video.id] ||
        this.thumbnailRequests.has(video.id)
      )
        continue;
      this.thumbnailRequests.add(video.id);
      this.service
        .thumbnail(video.id)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (blob) =>
            this.thumbnailUrls.update((urls) => ({
              ...urls,
              [video.id]: URL.createObjectURL(blob),
            })),
          complete: () => this.thumbnailRequests.delete(video.id),
          error: () => this.thumbnailRequests.delete(video.id),
        });
    }
  }
}
