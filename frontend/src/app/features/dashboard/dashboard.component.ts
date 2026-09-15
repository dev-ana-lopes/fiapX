import { HttpEventType } from "@angular/common/http";
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  signal,
} from "@angular/core";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { ActivatedRoute, Router, RouterLink } from "@angular/router";
import {
  catchError,
  concatMap,
  filter,
  from,
  interval,
  map,
  of,
  Subscription,
  switchMap,
  toArray,
} from "rxjs";
import {
  ALLOWED_VIDEO_EXTENSIONS,
  FRONTEND_UPLOAD_STATE_DELAY_MS,
  MAX_UPLOAD_SIZE_BYTES,
  POLLING_INTERVAL_MS,
} from "@core/config/api.config";
import {
  BreadcrumbItem,
  BreadcrumbsComponent,
} from "@core/layout/breadcrumbs.component";
import { AppShellComponent } from "@core/layout/app-shell.component";
import { PageHeaderComponent } from "@core/layout/page-header.component";
import { Video, VideoStatus } from "@core/models/video.model";
import { VideoService } from "@core/services/video.service";
import { DownloadButtonComponent } from "@core/videos/download-button.component";

@Component({
  standalone: true,
  imports: [
    RouterLink,
    AppShellComponent,
    PageHeaderComponent,
    BreadcrumbsComponent,
    DownloadButtonComponent,
  ],
  templateUrl: "./dashboard.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardComponent {
  private readonly service = inject(VideoService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly thumbnailRequests = new Set<string>();
  private polling?: Subscription;

  readonly breadcrumbs: BreadcrumbItem[] = [{ label: "Início" }];
  readonly menuOpen = signal(false);
  readonly uploadOpen = signal(false);
  readonly selectedFiles = signal<File[]>([]);
  readonly dragOver = signal(false);
  readonly uploading = signal(false);
  readonly uploadError = signal("");
  readonly loading = signal(true);
  readonly error = signal("");
  readonly videos = signal<Video[]>([]);
  readonly thumbnailUrls = signal<Record<string, string>>({});
  readonly accept = ALLOWED_VIDEO_EXTENSIONS.map(
    (extension) => `.${extension}`,
  ).join(",");
  readonly completedPage = signal(1);
  readonly completedPageSize = 10;
  readonly activeVideos = computed(() =>
    this.videos().filter(
      (video) => video.status === "PROCESSING" || video.status === "QUEUED",
    ),
  );
  readonly queuedVideos = computed(() =>
    this.videos().filter(this.hasStatus("QUEUED")),
  );
  readonly processingVideos = computed(() =>
    this.videos().filter(this.hasStatus("PROCESSING")),
  );
  readonly completedVideos = computed(() =>
    this.videos().filter(this.hasStatus("COMPLETED")),
  );
  readonly completedTotalPages = computed(() =>
    Math.max(
      1,
      Math.ceil(this.completedVideos().length / this.completedPageSize),
    ),
  );
  readonly displayedCompletedVideos = computed(() => {
    const first = (this.completedPage() - 1) * this.completedPageSize;
    return this.completedVideos().slice(first, first + this.completedPageSize);
  });
  readonly failedVideos = computed(() =>
    this.videos().filter(this.hasStatus("FAILED")),
  );
  readonly totalVideos = computed(() => this.videos().length);

  constructor() {
    this.destroyRef.onDestroy(() =>
      Object.values(this.thumbnailUrls()).forEach((url) =>
        URL.revokeObjectURL(url),
      ),
    );
    this.startPolling();
    this.route.queryParamMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        if (params.get("upload") === "true") this.openUpload();
      });
  }

  goToCompletedPage(page: number): void {
    if (page >= 1 && page <= this.completedTotalPages())
      this.completedPage.set(page);
  }

  loadVideos(): void {
    this.loading.set(true);
    this.startPolling();
  }

  openUpload(): void {
    this.uploadError.set("");
    this.uploadOpen.set(true);
  }

  closeUpload(): void {
    if (this.uploading()) return;
    this.uploadOpen.set(false);
    this.selectedFiles.set([]);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { upload: null },
      queryParamsHandling: "merge",
    });
  }

  selectFile(event: Event): void {
    this.setFiles(Array.from((event.target as HTMLInputElement).files || []));
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(false);
    this.setFiles(Array.from(event.dataTransfer?.files || []));
  }

  isStepDone(video: Video, threshold: number): boolean {
    return video.status === "PROCESSING" && video.progress >= threshold;
  }

  upload(): void {
    const files = this.selectedFiles();
    if (!files.length) return;
    this.uploading.set(true);
    from(files)
      .pipe(
        concatMap((file) =>
          this.service.upload(file).pipe(
            filter((event) => event.type === HttpEventType.Response),
            map(() => true),
            catchError(() => of(false)),
          ),
        ),
        toArray(),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((results) => {
        this.uploading.set(false);
        const failed = results.filter((result) => !result).length;
        if (failed) {
          this.uploadError.set(`${failed} vídeo(s) não puderam ser enviados.`);
          this.loadVideos();
          return;
        }
        this.closeUpload();
        setTimeout(() => this.loadVideos(), FRONTEND_UPLOAD_STATE_DELAY_MS);
      });
  }

  private startPolling(): void {
    this.polling?.unsubscribe();
    this.polling = interval(POLLING_INTERVAL_MS)
      .pipe(
        switchMap(() => this.service.list().pipe(catchError(() => of(null)))),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((items) => this.handleVideoResponse(items));
    this.service
      .list()
      .pipe(
        catchError(() => of(null)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((items) => this.handleVideoResponse(items));
  }

  private handleVideoResponse(items: Video[] | null): void {
    this.loading.set(false);
    if (!items) {
      if (!this.videos().length)
        this.error.set("Não foi possível carregar seus vídeos.");
      return;
    }
    this.setVideos(items);
    this.loadThumbnails(items);
    this.error.set("");
    if (
      !items.some(
        (item) => item.status === "QUEUED" || item.status === "PROCESSING",
      )
    )
      this.polling?.unsubscribe();
  }

  private loadThumbnails(items: Video[]): void {
    for (const video of items.filter(this.hasStatus("COMPLETED"))) {
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

  private setVideos(items: Video[]): void {
    this.videos.set(items);
    if (this.completedPage() > this.completedTotalPages())
      this.completedPage.set(this.completedTotalPages());
  }

  private hasStatus(status: VideoStatus): (video: Video) => boolean {
    return (video) => video.status === status;
  }

  private setFiles(files: File[]): void {
    this.uploadError.set("");
    for (const file of files) {
      const extension = file.name.split(".").pop()?.toLowerCase();
      if (!extension || !ALLOWED_VIDEO_EXTENSIONS.includes(extension)) {
        this.uploadError.set(`Formato não suportado: ${file.name}`);
        return;
      }
      if (file.size > MAX_UPLOAD_SIZE_BYTES) {
        this.uploadError.set(`Arquivo acima de 500 MB: ${file.name}`);
        return;
      }
    }
    this.selectedFiles.set(files);
  }
}
