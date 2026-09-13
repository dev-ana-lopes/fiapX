import { Injectable, inject } from "@angular/core";
import { Observable, map, shareReplay } from "rxjs";
import { VideoService } from "../services/video.service";

@Injectable({ providedIn: "root" })
export class VideoPreviewCacheService {
  private readonly service = inject(VideoService);
  private readonly previews = new Map<string, Observable<string>>();

  get(videoId: string): Observable<string> {
    const cached = this.previews.get(videoId);
    if (cached) return cached;
    const preview = this.service.preview(videoId).pipe(
      map((blob) => URL.createObjectURL(blob)),
      shareReplay({ bufferSize: 1, refCount: false }),
    );
    this.previews.set(videoId, preview);
    return preview;
  }
}
