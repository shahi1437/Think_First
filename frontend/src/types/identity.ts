import { z } from "zod";

export const roleNameSchema = z.enum(["student", "teacher", "admin"]);
export const programmingExperienceSchema = z.enum([
  "none",
  "beginner",
  "basic",
  "intermediate",
  "advanced",
]);
export const preferredLanguageSchema = z.enum([
  "python",
  "javascript",
  "c",
  "cpp",
  "java",
]);
export const learningGoalSchema = z.enum([
  "school_fundamentals",
  "university_coursework",
  "debugging_mastery",
  "interview_prep",
  "competitive_programming",
]);
export const explanationLanguageSchema = z.enum(["en", "bn"]);
export const startingPreferenceSchema = z.enum([
  "guided_beginner",
  "diagnostic_assessment",
]);
export const recommendedEntryTrackSchema = z.enum([
  "foundation_lessons",
  "diagnostic_assessment",
]);

export const userPreferencesResponseSchema = z.object({
  programming_experience: programmingExperienceSchema,
  preferred_language: preferredLanguageSchema,
  active_language_slug: preferredLanguageSchema.optional(),
  learning_goal: learningGoalSchema,
  daily_practice_minutes: z.number().int().min(10).max(240),
  preferred_explanation_language: explanationLanguageSchema,
  starting_preference: startingPreferenceSchema,
  recommended_entry_track: recommendedEntryTrackSchema,
  recommendation_rationale: z.string(),
});

export const userMeResponseSchema = z.object({
  id: z.string(),
  email: z.string(),
  full_name: z.string(),
  avatar_url: z.string().nullable().optional(),
  roles: z.array(roleNameSchema),
  onboarding_completed: z.boolean(),
  onboarding_completed_at: z.string().nullable().optional(),
  preferences: userPreferencesResponseSchema.nullable().optional(),
});

export const onboardingFormSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(2, "Please enter your full name (at least 2 characters).")
    .max(120, "Name must be 120 characters or fewer."),
  programming_experience: programmingExperienceSchema,
  preferred_language: preferredLanguageSchema,
  learning_goal: learningGoalSchema,
  daily_practice_minutes: z
    .number()
    .int("Practice time must be a whole number of minutes.")
    .min(10, "Choose at least 10 minutes per day.")
    .max(240, "Maximum daily target is 240 minutes."),
  preferred_explanation_language: explanationLanguageSchema,
  starting_preference: startingPreferenceSchema,
});

export type RoleName = z.infer<typeof roleNameSchema>;
export type UserPreferencesResponse = z.infer<
  typeof userPreferencesResponseSchema
>;
export type UserMeResponse = z.infer<typeof userMeResponseSchema>;
export type OnboardingFormValues = z.infer<typeof onboardingFormSchema>;
