export const SUPPORTED_LANGUAGE_SLUGS = [
  "python",
  "javascript",
  "c",
  "cpp",
  "java",
] as const;

export type SupportedLanguageSlug = (typeof SUPPORTED_LANGUAGE_SLUGS)[number];

export interface LanguageDisplayMeta {
  slug: SupportedLanguageSlug;
  label: string;
  shortLabel: string;
  monacoLanguage: string;
  runtimeLabel: string;
  badgeColor: string;
}

export const LANGUAGE_META: Record<SupportedLanguageSlug, LanguageDisplayMeta> = {
  python: {
    slug: "python",
    label: "Python 3",
    shortLabel: "Python",
    monacoLanguage: "python",
    runtimeLabel: "Python 3",
    badgeColor: "bg-indigo-100 text-indigo-800 border-indigo-200",
  },
  javascript: {
    slug: "javascript",
    label: "JavaScript",
    shortLabel: "JS",
    monacoLanguage: "javascript",
    runtimeLabel: "Node.js",
    badgeColor: "bg-amber-100 text-amber-900 border-amber-200",
  },
  c: {
    slug: "c",
    label: "C",
    shortLabel: "C",
    monacoLanguage: "c",
    runtimeLabel: "GCC C",
    badgeColor: "bg-sky-100 text-sky-900 border-sky-200",
  },
  cpp: {
    slug: "cpp",
    label: "C++",
    shortLabel: "C++",
    monacoLanguage: "cpp",
    runtimeLabel: "GCC C++",
    badgeColor: "bg-violet-100 text-violet-900 border-violet-200",
  },
  java: {
    slug: "java",
    label: "Java",
    shortLabel: "Java",
    monacoLanguage: "java",
    runtimeLabel: "OpenJDK",
    badgeColor: "bg-rose-100 text-rose-900 border-rose-200",
  },
};

export function getLanguageDisplayName(slug: string | null | undefined): string {
  if (!slug) return "Python 3";
  const key = slug.toLowerCase() as SupportedLanguageSlug;
  return LANGUAGE_META[key]?.label ?? slug.toUpperCase();
}

export function getLanguageShortLabel(slug: string | null | undefined): string {
  if (!slug) return "Python";
  const key = slug.toLowerCase() as SupportedLanguageSlug;
  return LANGUAGE_META[key]?.shortLabel ?? slug.toUpperCase();
}

export function getMonacoLanguageForSlug(slug: string | null | undefined): string {
  if (!slug) return "python";
  const key = slug.toLowerCase() as SupportedLanguageSlug;
  return LANGUAGE_META[key]?.monacoLanguage ?? "python";
}
