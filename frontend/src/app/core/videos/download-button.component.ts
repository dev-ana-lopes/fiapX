import { Component, inject, input, output } from '@angular/core';
import { Video } from '../models/video.model';
import { VideoService } from '../services/video.service';

@Component({
  selector: 'app-download-button',
  standalone: true,
  template: `<button class="download-action" [disabled]="!video().downloadAvailable" (click)="download($event)">⇩&nbsp; BAIXAR ZIP</button>`,
})
export class DownloadButtonComponent {
  readonly video = input.required<Video>();
  readonly failed = output<void>();
  private readonly service = inject(VideoService);

  download(event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    if (!this.video().downloadAvailable) return;
    this.service.download(this.video().id).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'frames.zip';
        link.click();
        URL.revokeObjectURL(url);
      },
      error: () => this.failed.emit(),
    });
  }
}
