import React from "react";

type RootState = {
  description?: string;
  chart_image?: string | null;
  chart_options?: any;
};

export function ChartRenderer({ state }: { state: RootState }) {
  const title = state?.description ?? "Chart";

  // ✅ if server returned an image (base64 / url)
  if (state?.chart_image) {
    return (
      <div className="p-4 rounded-xl bg-zinc-900 border border-zinc-800">
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <img
          src={state.chart_image}
          alt={title}
          className="rounded-lg border border-zinc-800 max-w-full"
        />
      </div>
    );
  }

  // ✅ fallback: show options as JSON (useful for debugging)
  return (
    <div className="p-4 rounded-xl bg-zinc-900 border border-zinc-800">
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <div className="text-sm text-zinc-400 mb-3">
        No chart image provided — showing chart options instead:
      </div>
      <pre className="text-xs overflow-auto whitespace-pre-wrap">
        {JSON.stringify(state?.chart_options, null, 2)}
      </pre>
    </div>
  );
}
