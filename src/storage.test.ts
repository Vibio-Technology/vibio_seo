import { afterEach, describe, expect, it, vi } from "vitest";

import { saveRun } from "./storage";
import type { RunRecord } from "./types";

function run(id: string): RunRecord {
  return {
    id,
    mode: "audit",
    projectName: "Vibio",
    siteUrl: "https://example.com",
    market: "DE",
    language: "de-DE",
    objective: "Audit",
    provider: "deepseek",
    model: "deepseek-chat",
    report: `# ${id}`,
    evidence: [],
    createdAt: "2026-07-13T08:00:00Z",
  };
}

function storage(initialRuns: RunRecord[], write: (value: string) => void): Storage {
  let value = JSON.stringify(initialRuns);
  return {
    get length() { return value ? 1 : 0; },
    clear() { value = ""; },
    getItem(key) { return key === "vibio:runs" ? value : null; },
    key(index) { return index === 0 && value ? "vibio:runs" : null; },
    removeItem(key) { if (key === "vibio:runs") value = ""; },
    setItem(key, next) {
      if (key !== "vibio:runs") return;
      write(next);
      value = next;
    },
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("saveRun", () => {
  it("evicts the oldest history entries until the browser accepts the write", () => {
    const local = storage([run("old-1"), run("old-2"), run("old-3")], (value) => {
      if ((JSON.parse(value) as unknown[]).length > 2) throw new DOMException("quota");
    });
    vi.stubGlobal("localStorage", local);

    const result = saveRun(run("new"));

    expect(result.persisted).toBe(true);
    expect(result.runs.map((item) => item.id)).toEqual(["new", "old-1"]);
  });

  it("reports when even the current record cannot be persisted", () => {
    vi.stubGlobal("localStorage", storage([], () => { throw new DOMException("quota"); }));

    const result = saveRun(run("new"));

    expect(result.persisted).toBe(false);
    expect(result.runs.map((item) => item.id)).toEqual(["new"]);
  });
});
