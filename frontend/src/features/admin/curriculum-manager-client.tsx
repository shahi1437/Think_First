"use client";

import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  FlaskConical,
  Loader2,
  Plus,
} from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  updateAdminLessonStatus,
  updateAdminTrack,
  upsertAdminLesson,
  validateAdminLessonExercise,
} from "@/lib/api-client";
import type { AdminLessonDetailView } from "@/types/admin";
import type { LearningTrackView, TrackSlug } from "@/types/learning";

interface CurriculumManagerClientProps {
  accessToken: string;
  initialTracks: LearningTrackView[];
  initialLessons: AdminLessonDetailView[];
}

const ALL_TRACKS: TrackSlug[] = [
  "absolute_beginner",
  "basic_university",
  "intermediate",
  "advanced",
];

export function CurriculumManagerClient({
  accessToken,
  initialTracks,
  initialLessons,
}: CurriculumManagerClientProps) {
  const [tracks, setTracks] = useState<LearningTrackView[]>(initialTracks);
  const [lessons, setLessons] =
    useState<AdminLessonDetailView[]>(initialLessons);
  const [trackFilter, setTrackFilter] = useState<string>("all");

  // Track editor state
  const [editingTrackSlug, setEditingTrackSlug] = useState<string | null>(null);
  const [trackTitleEn, setTrackTitleEn] = useState("");
  const [trackTitleBn, setTrackTitleBn] = useState("");
  const [trackSummaryEn, setTrackSummaryEn] = useState("");
  const [trackSummaryBn, setTrackSummaryBn] = useState("");
  const [trackSkillsCsv, setTrackSkillsCsv] = useState("");

  // Lesson authoring state
  const [slug, setSlug] = useState("");
  const [skillSlug, setSkillSlug] = useState("nested_control_flow");
  const [displayOrder, setDisplayOrder] = useState("25");
  const [titleEn, setTitleEn] = useState("");
  const [titleBn, setTitleBn] = useState("");
  const [summaryEn, setSummaryEn] = useState("");
  const [summaryBn, setSummaryBn] = useState("");
  const [contentEn, setContentEn] = useState("");
  const [contentBn, setContentBn] = useState("");
  const [selectedTracks, setSelectedTracks] = useState<TrackSlug[]>([
    "intermediate",
  ]);
  const [starterCode, setStarterCode] = useState(
    "n = int(input())\nprint(n * n)\n",
  );
  const [testInput, setTestInput] = useState("4");
  const [testOutput, setTestOutput] = useState("16");
  const [refSolutionInput, setRefSolutionInput] = useState(
    "n = int(input())\nprint(n * n)\n",
  );

  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const visibleLessons =
    trackFilter === "all"
      ? lessons
      : lessons.filter((l) => l.track_slugs.includes(trackFilter));

  function openTrackEditor(t: LearningTrackView) {
    setEditingTrackSlug(t.slug);
    setTrackTitleEn(t.title_en);
    setTrackTitleBn(t.title_bn);
    setTrackSummaryEn(t.summary_en);
    setTrackSummaryBn(t.summary_bn);
    setTrackSkillsCsv(t.recommended_focus_skills.join(", "));
  }

  async function handleSaveTrack() {
    if (!editingTrackSlug) return;
    setBusyKey(`track-${editingTrackSlug}`);
    setErrorMsg(null);
    setFeedback(null);
    try {
      const updated = await updateAdminTrack(accessToken, editingTrackSlug, {
        title_en: trackTitleEn,
        title_bn: trackTitleBn,
        summary_en: trackSummaryEn,
        summary_bn: trackSummaryBn,
        recommended_focus_skills: trackSkillsCsv
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      });
      setTracks((prev) =>
        prev.map((t) => (t.slug === updated.slug ? updated : t)),
      );
      setEditingTrackSlug(null);
      setFeedback(`Updated learning track '${updated.title_en}'.`);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to update track.");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleCreateLesson(publish: boolean) {
    setBusyKey("create-lesson");
    setErrorMsg(null);
    setFeedback(null);
    try {
      await upsertAdminLesson(accessToken, {
        slug: slug.trim().toLowerCase(),
        skill_slug: skillSlug.trim(),
        display_order: Math.max(1, Number(displayOrder) || 25),
        title_en: titleEn.trim(),
        title_bn: titleBn.trim() || titleEn.trim(),
        summary_en: summaryEn.trim(),
        summary_bn: summaryBn.trim() || summaryEn.trim(),
        content_en_md: contentEn.trim(),
        content_bn_md: contentBn.trim() || contentEn.trim(),
        learning_objectives: ["Apply concept on real Judge0 practice"],
        prerequisite_lesson_slugs: [],
        track_slugs: selectedTracks,
        interactive_examples: [],
        guided_exercise: {
          prompt_en: summaryEn.trim(),
          prompt_bn: summaryBn.trim() || summaryEn.trim(),
          language_slug: "python",
          starter_code: starterCode,
          test_cases: [
            {
              name: "Primary guided check",
              input_data: testInput,
              expected_output: testOutput,
            },
          ],
        },
        estimated_minutes: 20,
        publish,
      });
      setFeedback(
        `Saved lesson '${slug.trim()}' (${publish ? "published" : "draft"}).`,
      );
      setSlug("");
      setTitleEn("");
      setTitleBn("");
      setSummaryEn("");
      setSummaryBn("");
      setContentEn("");
      setContentBn("");
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to save lesson.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  async function handleLessonStatus(
    lessonId: string,
    status: "published" | "archived" | "draft",
  ) {
    setBusyKey(`lesson-status-${lessonId}`);
    setErrorMsg(null);
    setFeedback(null);
    try {
      const updated = await updateAdminLessonStatus(
        accessToken,
        lessonId,
        status,
      );
      setLessons((prev) =>
        prev.map((l) => (l.lesson_id === lessonId ? updated : l)),
      );
      setFeedback(`Lesson '${updated.slug}' updated to ${updated.status}.`);
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to update lesson status.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  async function handleValidateLessonExercise(lessonId: string) {
    setBusyKey(`lesson-val-${lessonId}`);
    setErrorMsg(null);
    setFeedback(null);
    try {
      const res = await validateAdminLessonExercise(
        accessToken,
        lessonId,
        refSolutionInput,
      );
      setFeedback(
        res.passed
          ? `Judge0 guided exercise validation PASSED (${res.passed_tests}/${res.total_tests}).`
          : `Judge0 guided exercise validation FAILED: ${res.errors.join("; ")}`,
      );
    } catch (err) {
      setErrorMsg(
        err instanceof Error ? err.message : "Exercise validation failed.",
      );
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wider text-indigo-700">
          Curriculum &amp; Track Governance
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">
          Learning Tracks &amp; Bilingual Lesson Catalog
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Manage all 4 learner tracks, inspect Intermediate &amp; Advanced
          curriculum ({lessons.length} lessons total), and validate guided Judge0
          exercises.
        </p>
      </section>

      {errorMsg ? (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-900"
        >
          <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
          <span>{errorMsg}</span>
        </div>
      ) : null}

      {feedback ? (
        <div
          role="status"
          className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-950"
        >
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-700" />
          <span>{feedback}</span>
        </div>
      ) : null}

      {/* Learning Tracks Editor */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-base font-bold text-slate-900">
          Learner Tracks ({tracks.length})
        </h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {tracks.map((track) => (
            <div
              key={track.slug}
              className="rounded-xl border border-slate-200 bg-slate-50 p-4"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-bold text-slate-900">
                    {track.title_en} ({track.title_bn})
                  </p>
                  <p className="mt-1 text-xs text-slate-600">
                    {track.summary_en}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => openTrackEditor(track)}
                  className="shrink-0 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                >
                  Edit
                </button>
              </div>
              <p className="mt-2 font-mono text-[11px] text-indigo-700">
                Focus skills: {track.recommended_focus_skills.join(", ")}
              </p>
            </div>
          ))}
        </div>

        {editingTrackSlug ? (
          <div className="mt-4 space-y-3 rounded-xl border border-indigo-200 bg-indigo-50/40 p-4 text-xs">
            <p className="font-bold text-indigo-950">
              Editing Track: {editingTrackSlug}
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                type="text"
                value={trackTitleEn}
                onChange={(e) => setTrackTitleEn(e.target.value)}
                placeholder="Title (EN)"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2"
              />
              <input
                type="text"
                value={trackTitleBn}
                onChange={(e) => setTrackTitleBn(e.target.value)}
                placeholder="Title (BN)"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2"
              />
              <textarea
                rows={2}
                value={trackSummaryEn}
                onChange={(e) => setTrackSummaryEn(e.target.value)}
                placeholder="Summary (EN)"
                className="rounded-lg border border-slate-300 bg-white p-2"
              />
              <textarea
                rows={2}
                value={trackSummaryBn}
                onChange={(e) => setTrackSummaryBn(e.target.value)}
                placeholder="Summary (BN)"
                className="rounded-lg border border-slate-300 bg-white p-2"
              />
              <input
                type="text"
                value={trackSkillsCsv}
                onChange={(e) => setTrackSkillsCsv(e.target.value)}
                placeholder="Focus skill slugs CSV"
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 sm:col-span-2"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditingTrackSlug(null)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-semibold"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busyKey !== null}
                onClick={() => void handleSaveTrack()}
                className="rounded-lg bg-indigo-600 px-3 py-1.5 font-semibold text-white"
              >
                Save Track
              </button>
            </div>
          </div>
        ) : null}
      </section>

      {/* Author / Version a Bilingual Lesson */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="flex items-center gap-2 text-base font-bold text-slate-900">
          <Plus className="h-4 w-4 text-indigo-600" />
          <span>Author / Update Bilingual Lesson</span>
        </h2>
        <div className="mt-4 grid gap-3 text-xs sm:grid-cols-3">
          <input
            type="text"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder="lesson-slug-kebab"
            className="rounded-lg border border-slate-300 px-3 py-2"
          />
          <input
            type="text"
            value={skillSlug}
            onChange={(e) => setSkillSlug(e.target.value)}
            placeholder="skill_slug (e.g. recursion_fundamentals)"
            className="rounded-lg border border-slate-300 px-3 py-2"
          />
          <input
            type="number"
            value={displayOrder}
            onChange={(e) => setDisplayOrder(e.target.value)}
            placeholder="Display order"
            className="rounded-lg border border-slate-300 px-3 py-2"
          />
          <input
            type="text"
            value={titleEn}
            onChange={(e) => setTitleEn(e.target.value)}
            placeholder="Lesson Title (English)"
            className="rounded-lg border border-slate-300 px-3 py-2 sm:col-span-2"
          />
          <input
            type="text"
            value={titleBn}
            onChange={(e) => setTitleBn(e.target.value)}
            placeholder="Lesson Title (বাংলা)"
            className="rounded-lg border border-slate-300 px-3 py-2"
          />
          <input
            type="text"
            value={summaryEn}
            onChange={(e) => setSummaryEn(e.target.value)}
            placeholder="Summary (English)"
            className="rounded-lg border border-slate-300 px-3 py-2 sm:col-span-2"
          />
          <input
            type="text"
            value={summaryBn}
            onChange={(e) => setSummaryBn(e.target.value)}
            placeholder="Summary (বাংলা)"
            className="rounded-lg border border-slate-300 px-3 py-2"
          />
          <textarea
            rows={3}
            value={contentEn}
            onChange={(e) => setContentEn(e.target.value)}
            placeholder="Markdown Content (English)"
            className="rounded-lg border border-slate-300 p-2 sm:col-span-2"
          />
          <textarea
            rows={3}
            value={contentBn}
            onChange={(e) => setContentBn(e.target.value)}
            placeholder="Markdown Content (বাংলা)"
            className="rounded-lg border border-slate-300 p-2"
          />
          <div className="flex flex-wrap items-center gap-3 sm:col-span-3">
            <span className="font-semibold text-slate-700">Tracks:</span>
            {ALL_TRACKS.map((trk) => {
              const active = selectedTracks.includes(trk);
              return (
                <label key={trk} className="inline-flex items-center gap-1.5">
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={() =>
                      setSelectedTracks((prev) =>
                        prev.includes(trk)
                          ? prev.filter((item) => item !== trk)
                          : [...prev, trk],
                      )
                    }
                  />
                  <span>{trk}</span>
                </label>
              );
            })}
          </div>
          <textarea
            rows={2}
            value={starterCode}
            onChange={(e) => setStarterCode(e.target.value)}
            placeholder="Guided exercise starter code"
            className="rounded-lg border border-slate-300 bg-slate-50 p-2 font-mono"
          />
          <input
            type="text"
            value={testInput}
            onChange={(e) => setTestInput(e.target.value)}
            placeholder="Guided check stdin"
            className="rounded-lg border border-slate-300 p-2 font-mono"
          />
          <input
            type="text"
            value={testOutput}
            onChange={(e) => setTestOutput(e.target.value)}
            placeholder="Expected stdout"
            className="rounded-lg border border-slate-300 p-2 font-mono"
          />
        </div>
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            disabled={busyKey !== null || !slug.trim() || !titleEn.trim()}
            onClick={() => void handleCreateLesson(false)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-50"
          >
            Save Draft
          </button>
          <button
            type="button"
            disabled={busyKey !== null || !slug.trim() || !titleEn.trim()}
            onClick={() => void handleCreateLesson(true)}
            className="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            Publish Lesson
          </button>
        </div>
      </section>

      {/* Lessons Catalog + Guided Exercise Judge0 Validator */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-teal-600" />
            <h2 className="text-base font-bold text-slate-900">
              Curriculum Lessons ({visibleLessons.length})
            </h2>
          </div>
          <select
            aria-label="Filter lessons by track"
            value={trackFilter}
            onChange={(e) => setTrackFilter(e.target.value)}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs"
          >
            <option value="all">All Tracks ({lessons.length})</option>
            {ALL_TRACKS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">
          <label className="block font-semibold text-slate-700">
            Reference Solution for On-Demand Lesson Exercise Validation
          </label>
          <textarea
            rows={2}
            value={refSolutionInput}
            onChange={(e) => setRefSolutionInput(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2 font-mono text-xs"
          />
        </div>

        <div className="mt-4 space-y-2">
          {visibleLessons.map((lesson) => (
            <div
              key={lesson.lesson_id}
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-4 text-xs"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-slate-500">
                    #{lesson.display_order}
                  </span>
                  <Badge
                    variant={
                      lesson.status === "published" ? "emerald" : "neutral"
                    }
                  >
                    {lesson.status} (v{lesson.version_number})
                  </Badge>
                  <Badge variant="indigo">{lesson.skill_slug}</Badge>
                  {lesson.track_slugs.map((trk) => (
                    <Badge key={trk} variant="teal">
                      {trk}
                    </Badge>
                  ))}
                </div>
                <p className="mt-1.5 text-sm font-bold text-slate-900">
                  {lesson.title_en} ·{" "}
                  <span className="font-normal text-slate-600">
                    {lesson.title_bn}
                  </span>
                </p>
                <p className="mt-0.5 text-slate-600">{lesson.summary_en}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  disabled={busyKey !== null}
                  onClick={() =>
                    void handleValidateLessonExercise(lesson.lesson_id)
                  }
                  className="inline-flex items-center gap-1 rounded-lg border border-teal-300 bg-teal-50 px-2.5 py-1.5 font-semibold text-teal-800 hover:bg-teal-100"
                >
                  {busyKey === `lesson-val-${lesson.lesson_id}` ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <FlaskConical className="h-3 w-3" />
                  )}
                  <span>Validate Exercise</span>
                </button>
                {lesson.status !== "published" ? (
                  <button
                    type="button"
                    disabled={busyKey !== null}
                    onClick={() =>
                      void handleLessonStatus(lesson.lesson_id, "published")
                    }
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 font-semibold text-white hover:bg-emerald-700"
                  >
                    Publish
                  </button>
                ) : (
                  <button
                    type="button"
                    disabled={busyKey !== null}
                    onClick={() =>
                      void handleLessonStatus(lesson.lesson_id, "archived")
                    }
                    className="rounded-lg border border-slate-300 px-3 py-1.5 font-semibold text-slate-700 hover:bg-slate-100"
                  >
                    Archive
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
