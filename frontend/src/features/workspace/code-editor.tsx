"use client";

import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[320px] items-center justify-center bg-[#1e1e1e] text-sm text-slate-300">
      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
      <span>Loading Monaco code editor...</span>
    </div>
  ),
});

interface CodeEditorProps {
  language: string;
  value: string;
  onChange: (nextValue: string) => void;
  usePlainTextarea?: boolean;
}

export function CodeEditor({
  language,
  value,
  onChange,
  usePlainTextarea = false,
}: CodeEditorProps) {
  if (usePlainTextarea) {
    return (
      <textarea
        aria-label="Code editor"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        spellCheck={false}
        className="h-full min-h-[340px] w-full resize-none bg-[#0f172a] p-4 font-mono text-sm leading-relaxed text-slate-100 focus:outline-none"
      />
    );
  }

  return (
    <div className="h-[380px] w-full overflow-hidden bg-[#1e1e1e] lg:h-[420px]">
      <MonacoEditor
        height="100%"
        language={language}
        theme="vs-dark"
        value={value}
        onChange={(next) => onChange(next ?? "")}
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          tabSize: 4,
          automaticLayout: true,
          scrollBeyondLastLine: false,
          wordWrap: "on",
          padding: { top: 12, bottom: 12 },
          accessibilitySupport: "on",
        }}
      />
    </div>
  );
}
