import React, { useMemo } from "react";

type RootState = {
  render_type?: string;
  description?: string;
  table_markdown?: string;
  executor_state?: {
    db_result?: Record<string, any>[];
  };
};

function extractColumns(rows: Record<string, any>[]) {
  if (!rows?.length) return [];
  return Object.keys(rows[0]);
}

/**
 * Parse GitHub-style markdown table into rows/columns
 */
function parseMarkdownTable(md: string) {
  const lines = md
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  // find the first line that looks like a markdown table header
  const headerIndex = lines.findIndex((l) => l.startsWith("|") && l.endsWith("|"));
  if (headerIndex === -1) return { columns: [], rows: [] };

  // header row
  const headerLine = lines[headerIndex];
  const dividerLine = lines[headerIndex + 1];
  if (!dividerLine || !dividerLine.includes("---")) return { columns: [], rows: [] };

  const columns = headerLine
    .slice(1, -1)
    .split("|")
    .map((c) => c.trim());

  const dataLines = lines.slice(headerIndex + 2).filter((l) => l.startsWith("|") && l.endsWith("|"));

  const rows = dataLines.map((line) => {
    const cells = line
      .slice(1, -1)
      .split("|")
      .map((c) => c.trim());

    const row: Record<string, any> = {};
    columns.forEach((col, i) => {
      row[col] = cells[i] ?? "";
    });
    return row;
  });

  return { columns, rows };
}

export function TableRenderer({ state }: { state: RootState }) {
  const title = state?.description ?? "Results";

  // ✅ first priority: db_result
  const dbRows = state?.executor_state?.db_result ?? [];

  // ✅ fallback: parse markdown
  const mdParsed = useMemo(() => {
    if (!dbRows.length && state?.table_markdown) {
      return parseMarkdownTable(state.table_markdown);
    }
    return { columns: [], rows: [] };
  }, [dbRows.length, state?.table_markdown]);

  const rows = dbRows.length ? dbRows : mdParsed.rows;
  const columns = useMemo(() => extractColumns(rows), [rows]);

  const hasRows = rows.length > 0;

  if (!hasRows) {
    return (
      <div className="p-4 rounded-xl bg-zinc-900 border border-zinc-800">
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <div className="text-sm text-zinc-400">No data to display.</div>

        {state?.table_markdown && (
          <pre className="mt-4 text-xs overflow-auto whitespace-pre-wrap text-zinc-500">
            {state.table_markdown}
          </pre>
        )}
      </div>
    );
  }

  return (
    <div className="p-4 rounded-xl bg-zinc-900 border border-zinc-800">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-lg font-semibold">{title}</h3>
          <p className="text-xs text-zinc-400">{rows.length} rows</p>
        </div>

        <button
          className="px-3 py-1.5 text-sm rounded-lg bg-zinc-800 hover:bg-zinc-700"
          onClick={() => {
            const csv = [
              columns.join(","),
              ...rows.map((r) => columns.map((c) => JSON.stringify(r[c] ?? "")).join(",")),
            ].join("\n");

            navigator.clipboard.writeText(csv);
          }}
        >
          Copy CSV
        </button>
      </div>

      <div className="overflow-auto max-h-[420px] rounded-lg border border-zinc-800">
        <table className="min-w-full text-sm text-left">
          <thead className="sticky top-0 bg-zinc-950 z-10">
            <tr>
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-3 py-2 border-b border-zinc-800 font-medium text-zinc-200 whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.map((row, idx) => (
              <tr
                key={idx}
                className={`border-b border-zinc-800 ${
                  idx % 2 === 0 ? "bg-zinc-900" : "bg-zinc-950"
                } hover:bg-zinc-800 transition`}
              >
                {columns.map((col) => (
                  <td key={col} className="px-3 py-2 text-zinc-200 whitespace-nowrap">
                    {String(row[col] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
