import { describe, expect, it } from "vitest";
import { mapNotificationDto } from "./notification.model";
import {
  groupNotifications,
  notificationIconClass,
} from "./notification.utils";

const today = "2026-09-07T12:00:00.000Z";

describe("notification presentation helpers", () => {
  it("maps the API snake_case contract to the UI model", () => {
    expect(
      mapNotificationDto({
        id: "notification-1",
        video_id: "video-1",
        type: "VIDEO_FAILED",
        status: "PENDING",
        title: "Falha",
        message: "Erro",
        created_at: today,
        read_at: null,
      }),
    ).toEqual({
      id: "notification-1",
      videoId: "video-1",
      type: "VIDEO_FAILED",
      status: "PENDING",
      title: "Falha",
      message: "Erro",
      createdAt: today,
      readAt: null,
    });
  });

  it("groups notifications into today and older items", () => {
    const groups = groupNotifications(
      [
        {
          id: "today",
          videoId: "v1",
          type: "VIDEO_COMPLETED",
          status: "READ",
          title: null,
          message: null,
          createdAt: today,
          readAt: today,
        },
        {
          id: "old",
          videoId: "v2",
          type: "VIDEO_FAILED",
          status: "PENDING",
          title: null,
          message: null,
          createdAt: "2026-09-06T12:00:00.000Z",
          readAt: null,
        },
      ],
      new Date(today),
    );

    expect(
      groups.map((group) => [group.label, group.items.map((item) => item.id)]),
    ).toEqual([
      ["Hoje", ["today"]],
      ["Anteriores", ["old"]],
    ]);
  });

  it("selects a semantic icon style for processing outcomes", () => {
    expect(notificationIconClass("VIDEO_COMPLETED")).toBe("success");
    expect(notificationIconClass("VIDEO_FAILED")).toBe("error");
    expect(notificationIconClass("OTHER")).toBe("info");
  });
});
