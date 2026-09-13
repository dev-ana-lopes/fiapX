export type VideoStatus = 'UPLOADING' | 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export interface Video {
  id: string;
  originalFilename: string;
  status: VideoStatus;
  progress: number;
  progressStage: string;
  frameCount?: number;
  resultSize?: string;
  duration?: string;
  resolution?: string;
  fps?: number;
  format?: string;
  errorMessage: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
  downloadAvailable: boolean;
  thumbnailUrl?: string;
}

export interface VideoResponseDto {
  id: string; original_filename: string; status: VideoStatus; progress: number; progress_stage: string;
  error_message: string | null; created_at: string; started_at: string | null;
  finished_at: string | null; download_available: boolean; frame_count?: number;
  result_size?: string; duration?: string; resolution?: string; fps?: number; format?: string;
}

export const mapVideoDto = (dto: VideoResponseDto): Video => ({
  id: dto.id, originalFilename: dto.original_filename, status: dto.status, progress: dto.progress, progressStage: dto.progress_stage,
  frameCount: dto.frame_count, resultSize: dto.result_size, duration: dto.duration,
  resolution: dto.resolution, fps: dto.fps, format: dto.format, errorMessage: dto.error_message,
  createdAt: dto.created_at, startedAt: dto.started_at, finishedAt: dto.finished_at,
  downloadAvailable: dto.download_available,
});
