/**
 * Zero-dependency deterministic line-by-line code diff (LCS algorithm)
 * used by Code Attempt Comparison (Phase 4) and Debugging Journey Replay (Phase 5).
 */

export interface DiffLine {
  kind: "unchanged" | "added" | "removed";
  oldLineNumber: number | null;
  newLineNumber: number | null;
  text: string;
}

export interface CodeDiffSummary {
  lines: DiffLine[];
  addedCount: number;
  removedCount: number;
  unchangedCount: number;
}

export function computeLineDiff(
  beforeCode: string,
  afterCode: string,
): CodeDiffSummary {
  const oldLines = beforeCode.replace(/\r\n/g, "\n").split("\n");
  const newLines = afterCode.replace(/\r\n/g, "\n").split("\n");

  const m = oldLines.length;
  const n = newLines.length;

  // Guard against extremely large inputs to keep UI instant
  if (m * n > 250_000) {
    const fallback: DiffLine[] = [
      ...oldLines.map((text, idx) => ({
        kind: "removed" as const,
        oldLineNumber: idx + 1,
        newLineNumber: null,
        text,
      })),
      ...newLines.map((text, idx) => ({
        kind: "added" as const,
        oldLineNumber: null,
        newLineNumber: idx + 1,
        text,
      })),
    ];
    return {
      lines: fallback,
      addedCount: n,
      removedCount: m,
      unchangedCount: 0,
    };
  }

  const dp: number[][] = Array.from({ length: m + 1 }, () =>
    new Array<number>(n + 1).fill(0),
  );

  for (let i = m - 1; i >= 0; i -= 1) {
    for (let j = n - 1; j >= 0; j -= 1) {
      if (oldLines[i] === newLines[j]) {
        dp[i][j] = dp[i + 1][j + 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
  }

  const result: DiffLine[] = [];
  let i = 0;
  let j = 0;
  let addedCount = 0;
  let removedCount = 0;
  let unchangedCount = 0;

  while (i < m && j < n) {
    if (oldLines[i] === newLines[j]) {
      result.push({
        kind: "unchanged",
        oldLineNumber: i + 1,
        newLineNumber: j + 1,
        text: oldLines[i],
      });
      unchangedCount += 1;
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      result.push({
        kind: "removed",
        oldLineNumber: i + 1,
        newLineNumber: null,
        text: oldLines[i],
      });
      removedCount += 1;
      i += 1;
    } else {
      result.push({
        kind: "added",
        oldLineNumber: null,
        newLineNumber: j + 1,
        text: newLines[j],
      });
      addedCount += 1;
      j += 1;
    }
  }

  while (i < m) {
    result.push({
      kind: "removed",
      oldLineNumber: i + 1,
      newLineNumber: null,
      text: oldLines[i],
    });
    removedCount += 1;
    i += 1;
  }

  while (j < n) {
    result.push({
      kind: "added",
      oldLineNumber: null,
      newLineNumber: j + 1,
      text: newLines[j],
    });
    addedCount += 1;
    j += 1;
  }

  return { lines: result, addedCount, removedCount, unchangedCount };
}
