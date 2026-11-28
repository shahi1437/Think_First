"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  Bell,
  CheckCheck,
  ClipboardCheck,
  GraduationCap,
  Megaphone,
  MessageSquare,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/lib/api-client";
import { formatUtcDateTime } from "@/lib/format-date";
import type { RoleName } from "@/types/identity";
import type {
  NotificationCategory,
  NotificationItemView,
} from "@/types/notifications";

interface NotificationCenterProps {
  accessToken?: string;
  activeRole: RoleName;
}

const CATEGORY_META: Record<
  NotificationCategory,
  { label: string; badgeClass: string; Icon: typeof Bell }
> = {
  assignment: {
    label: "Assignment",
    badgeClass: "bg-teal-50 text-teal-800 border-teal-200",
    Icon: ClipboardCheck,
  },
  submission_feedback: {
    label: "Feedback",
    badgeClass: "bg-amber-50 text-amber-800 border-amber-200",
    Icon: MessageSquare,
  },
  grading: {
    label: "Grade",
    badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-200",
    Icon: GraduationCap,
  },
  announcement: {
    label: "Announcement",
    badgeClass: "bg-sky-50 text-sky-800 border-sky-200",
    Icon: Megaphone,
  },
  classroom: {
    label: "Classroom",
    badgeClass: "bg-slate-100 text-slate-700 border-slate-200",
    Icon: Users,
  },
  ai_reminder: {
    label: "AI Reminder",
    badgeClass: "bg-teal-50 text-teal-900 border-teal-200",
    Icon: Sparkles,
  },
  system: {
    label: "System",
    badgeClass: "bg-slate-100 text-slate-700 border-slate-200",
    Icon: Bell,
  },
};

function formatNotificationTimestamp(iso: string): string {
  return formatUtcDateTime(iso);
}

export function NotificationCenter({
  accessToken,
  activeRole,
}: NotificationCenterProps) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItemView[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const [loading, setLoading] = useState(false);
  const [busyAll, setBusyAll] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const loadNotifications = useCallback(
    async (unreadOnly: boolean = false) => {
      if (!accessToken) return;
      setLoading(true);
      setError(null);
      try {
        const res = await fetchNotifications(accessToken, {
          role: activeRole,
          unread_only: unreadOnly,
          limit: 25,
        });
        setItems(res.items);
        setUnreadCount(res.unread_count);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Could not load notifications.",
        );
      } finally {
        setLoading(false);
      }
    },
    [accessToken, activeRole],
  );

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    void fetchNotifications(accessToken, {
      role: activeRole,
      unread_only: false,
      limit: 25,
    })
      .then((res) => {
        if (cancelled) return;
        setItems(res.items);
        setUnreadCount(res.unread_count);
      })
      .catch(() => {
        // Initial badge load fails silently; opening panel retries with error UI
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken, activeRole]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    function onPointerDown(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("mousedown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("mousedown", onPointerDown);
    };
  }, [open]);

  if (!accessToken) {
    return null;
  }

  async function handleToggle() {
    const next = !open;
    setOpen(next);
    if (next) {
      await loadNotifications(filter === "unread");
    }
  }

  async function handleFilterChange(nextFilter: "all" | "unread") {
    setFilter(nextFilter);
    await loadNotifications(nextFilter === "unread");
  }

  async function handleMarkRead(item: NotificationItemView) {
    if (!accessToken || item.is_read) return;
    try {
      const updated = await markNotificationRead(accessToken, item.id);
      setItems((prev) =>
        filter === "unread"
          ? prev.filter((n) => n.id !== item.id)
          : prev.map((n) => (n.id === item.id ? updated : n)),
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch {
      // Keep UI responsive; next open refreshes state
    }
  }

  async function handleMarkAllRead() {
    if (!accessToken || unreadCount === 0) return;
    setBusyAll(true);
    try {
      const res = await markAllNotificationsRead(accessToken, activeRole);
      setUnreadCount(res.unread_count);
      setItems((prev) =>
        filter === "unread"
          ? []
          : prev.map((n) => ({
              ...n,
              is_read: true,
              read_at: n.read_at ?? new Date().toISOString(),
            })),
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not mark all as read.",
      );
    } finally {
      setBusyAll(false);
    }
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => void handleToggle()}
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
        aria-expanded={open}
        aria-haspopup="dialog"
        data-testid="notification-bell-button"
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-600/30"
      >
        <Bell className="h-4 w-4" aria-hidden="true" />
        {unreadCount > 0 ? (
          <span
            data-testid="notification-unread-badge"
            className="absolute -right-1 -top-1 inline-flex min-w-[1.125rem] items-center justify-center rounded-full bg-teal-700 px-1 text-[10px] font-semibold leading-4 text-white tabular-nums"
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <section
          role="dialog"
          aria-label="Notification Center"
          data-testid="notification-center-panel"
          className="fixed inset-x-3 top-16 z-50 max-h-[80vh] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl sm:absolute sm:inset-x-auto sm:right-0 sm:top-11 sm:w-[24rem]"
        >
          <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold text-slate-950">
                Notifications
              </h2>
              <p className="text-xs text-slate-500 tabular-nums">
                {unreadCount === 0
                  ? "All caught up"
                  : `${unreadCount} unread update${unreadCount === 1 ? "" : "s"}`}
              </p>
            </div>
            <div className="flex items-center gap-1.5">
              {unreadCount > 0 ? (
                <button
                  type="button"
                  onClick={() => void handleMarkAllRead()}
                  disabled={busyAll}
                  data-testid="notification-mark-all-read"
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-700 transition-colors hover:bg-slate-50 hover:text-slate-950 disabled:opacity-50"
                >
                  <CheckCheck className="h-3.5 w-3.5" aria-hidden="true" />
                  Mark all read
                </button>
              ) : null}
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close notifications"
                className="inline-flex h-7 w-7 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-900"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>

          <div className="flex items-center gap-1.5 border-b border-slate-100 bg-slate-50/70 px-4 py-2">
            <button
              type="button"
              onClick={() => void handleFilterChange("all")}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                filter === "all"
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-200/70 hover:text-slate-900"
              }`}
            >
              All
            </button>
            <button
              type="button"
              onClick={() => void handleFilterChange("unread")}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                filter === "unread"
                  ? "bg-slate-900 text-white"
                  : "text-slate-600 hover:bg-slate-200/70 hover:text-slate-900"
              }`}
            >
              Unread
            </button>
          </div>

          <div className="max-h-[26rem] divide-y divide-slate-100 overflow-y-auto">
            {loading && items.length === 0 ? (
              <div className="px-4 py-8 text-center text-xs text-slate-500">
                Loading notifications…
              </div>
            ) : error ? (
              <div className="px-4 py-6 text-center text-xs text-rose-700">
                {error}
              </div>
            ) : items.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <p className="text-sm font-medium text-slate-800">
                  {filter === "unread"
                    ? "No unread notifications"
                    : "No notifications yet"}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Assignments, grades, class announcements, and retention
                  reminders will appear here.
                </p>
              </div>
            ) : (
              items.map((item) => {
                const meta = CATEGORY_META[item.category];
                const Icon = meta.Icon;
                return (
                  <div
                    key={item.id}
                    data-testid="notification-item"
                    className={`px-4 py-3 transition-colors ${
                      item.is_read ? "bg-white" : "bg-teal-50/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium ${meta.badgeClass}`}
                        >
                          <Icon className="h-3 w-3" aria-hidden="true" />
                          {meta.label}
                        </span>
                        {!item.is_read ? (
                          <span
                            className="h-1.5 w-1.5 rounded-full bg-teal-600"
                            aria-label="Unread"
                          />
                        ) : null}
                      </div>
                      <span className="shrink-0 text-[11px] text-slate-400 tabular-nums">
                        {formatNotificationTimestamp(item.created_at)}
                      </span>
                    </div>

                    <p className="mt-1.5 text-xs font-semibold text-slate-900">
                      {item.title}
                    </p>
                    <p className="mt-0.5 text-xs leading-relaxed text-slate-600">
                      {item.body}
                    </p>

                    <div className="mt-2 flex items-center justify-between gap-2">
                      {item.href ? (
                        <Link
                          href={item.href}
                          onClick={() => {
                            void handleMarkRead(item);
                            setOpen(false);
                          }}
                          className="text-xs font-medium text-teal-700 hover:text-teal-900 hover:underline"
                        >
                          Open →
                        </Link>
                      ) : (
                        <span />
                      )}
                      {!item.is_read ? (
                        <button
                          type="button"
                          onClick={() => void handleMarkRead(item)}
                          className="text-[11px] font-medium text-slate-500 hover:text-slate-900"
                        >
                          Mark read
                        </button>
                      ) : (
                        <span className="text-[11px] text-slate-400">Read</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>
      ) : null}
    </div>
  );
}
