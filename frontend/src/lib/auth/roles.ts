import type { RoleName } from "@/types/identity";

export const PORTAL_PATHS: Record<RoleName, string> = {
  student: "/student",
  teacher: "/teacher",
  admin: "/admin",
};

export const PORTAL_LABELS: Record<RoleName, string> = {
  student: "Student",
  teacher: "Teacher",
  admin: "Admin",
};

export const PORTAL_LOGIN_PATHS: Record<RoleName, string> = {
  student: "/login/student",
  teacher: "/login/teacher",
  admin: "/login/admin",
};

export function resolvePortalLoginPath(pathname?: string | null): string {
  if (!pathname) return "/login";
  if (pathname === "/admin" || pathname.startsWith("/admin/")) {
    return "/login/admin";
  }
  if (pathname === "/teacher" || pathname.startsWith("/teacher/")) {
    return "/login/teacher";
  }
  if (pathname === "/student" || pathname.startsWith("/student/")) {
    return "/login/student";
  }
  return "/login";
}

export function getPrimaryRole(roles: readonly RoleName[]): RoleName {
  if (roles.includes("admin")) return "admin";
  if (roles.includes("teacher")) return "teacher";
  return "student";
}

export function isAuthorizedForLoginPortal(
  roles: readonly RoleName[],
  portal: RoleName,
): boolean {
  if (portal === "admin") {
    return roles.includes("admin");
  }
  if (portal === "teacher") {
    return roles.includes("teacher");
  }
  // Student Login is strictly for Student accounts so Teachers/Admins are never silently treated as Students.
  return (
    roles.includes("student") &&
    !roles.includes("teacher") &&
    !roles.includes("admin")
  );
}

export function getPortalMismatchMessage(
  expectedPortal: RoleName,
  actualRoles: readonly RoleName[],
): string {
  const expectedLabel = PORTAL_LABELS[expectedPortal];
  if (expectedPortal === "student") {
    const primary = getPrimaryRole(actualRoles);
    const actualLabel = PORTAL_LABELS[primary];
    return `This account is registered with ${actualLabel} access, not Student-only portal login. Please sign in through the ${actualLabel} Login page.`;
  }
  return `This account does not have ${expectedLabel} access. Please use your authorized portal.`;
}

export function canAccessPortal(
  roles: readonly RoleName[],
  portal: RoleName,
): boolean {
  if (portal === "admin") {
    return roles.includes("admin");
  }
  if (portal === "teacher") {
    return roles.includes("teacher") || roles.includes("admin");
  }
  return roles.length > 0;
}

export function getAuthorizedPortals(roles: readonly RoleName[]): RoleName[] {
  const portals: RoleName[] = [];
  if (canAccessPortal(roles, "student")) portals.push("student");
  if (canAccessPortal(roles, "teacher")) portals.push("teacher");
  if (canAccessPortal(roles, "admin")) portals.push("admin");
  return portals;
}

export function resolveDefaultPortalPath(roles: readonly RoleName[]): string {
  if (roles.includes("admin")) {
    return "/admin";
  }
  if (roles.includes("teacher")) {
    return "/teacher";
  }
  return "/student";
}

export function sanitizeInternalPath(rawPath?: string | null): string | null {
  if (!rawPath) return null;
  const trimmed = rawPath.trim();
  if (!trimmed.startsWith("/") || trimmed.startsWith("//")) {
    return null;
  }
  if (trimmed.startsWith("/login") || trimmed.startsWith("/register")) {
    return null;
  }
  return trimmed;
}

export function resolvePostLoginRedirect(
  roles: readonly RoleName[],
  requestedNext?: string | null,
): string {
  const safeNext = sanitizeInternalPath(requestedNext);
  const defaultPath = resolveDefaultPortalPath(roles);
  if (!safeNext) {
    return defaultPath;
  }
  if (safeNext === "/admin" || safeNext.startsWith("/admin/")) {
    return canAccessPortal(roles, "admin") ? safeNext : defaultPath;
  }
  if (safeNext === "/teacher" || safeNext.startsWith("/teacher/")) {
    return canAccessPortal(roles, "teacher") ? safeNext : defaultPath;
  }
  if (
    safeNext === "/accept-teacher-invite" ||
    safeNext.startsWith("/accept-teacher-invite?")
  ) {
    return safeNext;
  }
  return safeNext;
}
