import { z } from "zod";
import { roleNameSchema } from "@/types/identity";

export const notificationCategorySchema = z.enum([
  "assignment",
  "submission_feedback",
  "grading",
  "announcement",
  "classroom",
  "ai_reminder",
  "system",
]);
export type NotificationCategory = z.infer<typeof notificationCategorySchema>;

export const notificationItemSchema = z.object({
  id: z.string(),
  recipient_role: roleNameSchema,
  category: notificationCategorySchema,
  title: z.string(),
  body: z.string(),
  href: z.string().nullable(),
  is_read: z.boolean(),
  read_at: z.string().nullable(),
  metadata: z.record(z.string(), z.unknown()),
  created_at: z.string(),
});
export type NotificationItemView = z.infer<typeof notificationItemSchema>;

export const notificationListResponseSchema = z.object({
  items: z.array(notificationItemSchema),
  total: z.number(),
  unread_count: z.number(),
  limit: z.number(),
  offset: z.number(),
});
export type NotificationListResponse = z.infer<
  typeof notificationListResponseSchema
>;

export const markAllReadResponseSchema = z.object({
  marked_count: z.number(),
  unread_count: z.number(),
});
export type MarkAllReadResponse = z.infer<typeof markAllReadResponseSchema>;

export const teacherAnnouncementResponseSchema = z.object({
  course_id: z.string(),
  course_code: z.string().optional(),
  title: z.string(),
  recipients_notified: z.number(),
  created_at: z.string(),
});
export type TeacherAnnouncementResponse = z.infer<
  typeof teacherAnnouncementResponseSchema
>;
