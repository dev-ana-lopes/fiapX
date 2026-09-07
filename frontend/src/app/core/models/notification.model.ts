export type NotificationStatus = 'PENDING' | 'READ';

export interface Notification {
  id: string;
  videoId: string;
  type: 'VIDEO_COMPLETED' | 'VIDEO_FAILED' | string;
  status: NotificationStatus | string;
  title: string | null;
  message: string | null;
  createdAt: string;
  readAt: string | null;
}

export interface NotificationResponseDto {
  id: string;
  video_id: string;
  type: string;
  status: string;
  title: string | null;
  message: string | null;
  created_at: string;
  read_at: string | null;
}

export interface NotificationPageDto {
  items: NotificationResponseDto[];
  unread_count: number;
}

export const mapNotificationDto = (dto: NotificationResponseDto): Notification => ({
  id: dto.id,
  videoId: dto.video_id,
  type: dto.type,
  status: dto.status,
  title: dto.title,
  message: dto.message,
  createdAt: dto.created_at,
  readAt: dto.read_at,
});
