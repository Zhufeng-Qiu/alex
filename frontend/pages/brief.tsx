import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Head from "next/head";
import Layout from "../components/Layout";
import { API_URL } from "../lib/config";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

type Mode = "market_overview" | "user_focus";

interface BriefResponse {
  job_id?: string;
  message?: string;
  error?: string;
}

interface BriefJob {
  id: string;
  job_id?: string;
  created_at?: string;
  report_payload?: {
    content?: string;
    generated_at?: string;
    agent?: string;
    mode?: string;
  };
}

export default function Brief() {
  const { getToken } = useAuth();
  const [mode, setMode] = useState<Mode>("market_overview");
  const [interests, setInterests] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [brief, setBrief] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [briefHistory, setBriefHistory] = useState<BriefJob[]>([]);
  const [expandedBriefIds, setExpandedBriefIds] = useState<Set<string>>(new Set());

  const loadJobsAndHistory = async () => {
    try {
      const token = await getToken();
      if (!token) return;

      const response = await fetch(`${API_URL}/api/jobs`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) return;

      const data = await response.json();
      const jobs: BriefJob[] = Array.isArray(data?.jobs) ? data.jobs : [];
      if (jobs.length > 0) {
        // Save brief history for display (jobs where report_payload.agent === 'briefer')
        const briefs: BriefJob[] = jobs.filter((job) => {
          const payload = job.report_payload;
          return payload && payload.agent === "briefer" && typeof payload.content === "string";
        });
        setBriefHistory(briefs);

        // Assume the first job is the most recent; adjust if API shape differs.
        const latest = jobs[0];
        if (latest && typeof latest.id === "string") {
          setJobId(latest.id);
        } else if (latest && typeof latest.job_id === "string") {
          setJobId(latest.job_id);
        }
      }
    } catch {
      // Non-fatal: if we can't load a job, brief still works without persistence.
    }
  };

  useEffect(() => {
    void loadJobsAndHistory();
  }, [getToken]);

  const pollBriefJob = async (jobIdToPoll: string) => {
    // Poll the job status until the brief content is available, or time out after ~60s.
    const maxAttempts = 30;
    const delayMs = 2000;

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const token = await getToken();
        if (!token) return;

        const resp = await fetch(`${API_URL}/api/jobs/${jobIdToPoll}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (resp.ok) {
          const job: BriefJob = await resp.json();
          const payload = job.report_payload;
          if (payload && payload.agent === "briefer" && typeof payload.content === "string") {
            setBrief(payload.content);
            await loadJobsAndHistory();
            return;
          }
        }
      } catch {
        // Ignore transient errors and keep polling.
      }

      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }

    throw new Error("Brief is taking longer than expected. Please check brief history later.");
  };

  const generateBrief = async (selectedMode: Mode) => {
    try {
      setLoading(true);
      setError(null);
      setBrief(null);

      const token = await getToken();

      const body: Record<string, unknown> = {
        mode: selectedMode,
      };
      if (selectedMode === "user_focus" && interests.trim()) {
        body.interests = interests.trim();
      }
      if (jobId) {
        body.job_id = jobId;
      }

      const response = await fetch(`${API_URL}/api/brief`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to generate brief");
      }

      const data: BriefResponse = await response.json();
      if (typeof data.job_id === "string") {
        setJobId(data.job_id);
        await pollBriefJob(data.job_id);
        return;
      }

      throw new Error(data.error || "Failed to start brief job");
    } catch (e) {
      console.error(e);
      setError(e instanceof Error ? e.message : "Unexpected error generating brief");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <Head>
        <title>Brief Report | Alex AI Financial Advisor</title>
      </Head>
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Brief Report</h2>
            <p className="text-gray-600">
              Generate a concise, high-signal brief based on current market conditions or your own areas of interest.
              Earnings calls and stock price moves are prioritized.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Mode 1: Market overview */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col gap-4">
              <h3 className="text-lg font-semibold text-gray-900">Market Brief</h3>
              <p className="text-sm text-gray-600">
                Generate a brief report based on today&apos;s or this week&apos;s market context:
                earnings, guidance, and notable price moves.
              </p>
              <button
                onClick={() => {
                  setMode("market_overview");
                  generateBrief("market_overview");
                }}
                disabled={loading}
                className="mt-auto inline-flex items-center justify-center px-4 py-2 rounded-lg bg-primary text-white text-sm font-semibold hover:bg-blue-600 disabled:opacity-60"
              >
                {loading && mode === "market_overview" ? "Generating..." : "Generate Market Brief"}
              </button>
            </div>

            {/* Mode 2: User focus */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col gap-4 lg:col-span-2">
              <h3 className="text-lg font-semibold text-gray-900">Custom Brief (Your Focus)</h3>
              <p className="text-sm text-gray-600">
                Enter the companies, tickers, or themes you care about. The brief will focus on recent earnings and
                price action for those names.
              </p>
              <textarea
                value={interests}
                onChange={(e) => setInterests(e.target.value)}
                rows={4}
                className="mt-1 block w-full rounded-lg border-gray-300 shadow-sm focus:border-primary focus:ring-primary text-sm"
                placeholder="Example: AAPL, NVDA, cloud software, US banks"
              />
              <button
                onClick={() => {
                  setMode("user_focus");
                  generateBrief("user_focus");
                }}
                disabled={loading || !interests.trim()}
                className="inline-flex items-center justify-center px-4 py-2 rounded-lg bg-ai-accent text-white text-sm font-semibold hover:bg-purple-700 disabled:opacity-60"
              >
                {loading && mode === "user_focus" ? "Generating..." : "Generate Custom Brief"}
              </button>
              <p className="text-xs text-gray-500 mt-1">
                Input is validated server-side to guard against prompt injection and malicious content.
              </p>
            </div>
          </div>

          {/* Result */}
          <div className="space-y-6">
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Latest Brief</h3>
              {loading && !brief && (
                <p className="text-sm text-gray-500">Generating brief...</p>
              )}
              {error && (
                <div className="mb-4 rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-800">
                  {error}
                </div>
              )}
              {brief ? (
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>{brief}</ReactMarkdown>
                </div>
              ) : !loading && !error ? (
                <p className="text-sm text-gray-500">
                  No brief generated yet. Use one of the options above to create a new brief report.
                </p>
              ) : null}
            </div>

            {/* Brief history */}
            {briefHistory.length > 0 && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Previous Briefs</h3>
                <div className="space-y-4">
                  {briefHistory.map((job) => {
                    const isExpanded = expandedBriefIds.has(job.id);
                    const toggle = () => {
                      setExpandedBriefIds((prev) => {
                        const next = new Set(prev);
                        if (next.has(job.id)) next.delete(job.id);
                        else next.add(job.id);
                        return next;
                      });
                    };
                    return (
                      <div key={job.id} className="border border-gray-100 rounded-lg p-3">
                        <div className="flex items-center justify-between gap-2 flex-wrap">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium text-gray-900">
                              Mode: {job.report_payload?.mode || "unknown"}
                            </p>
                            <p className="text-xs text-gray-500">
                              {job.report_payload?.generated_at
                                ? new Date(job.report_payload.generated_at).toLocaleString()
                                : job.created_at
                                ? new Date(job.created_at).toLocaleString()
                                : ""}
                            </p>
                          </div>
                          {job.report_payload?.content && (
                            <button
                              type="button"
                              onClick={toggle}
                              className="text-sm font-medium text-primary hover:underline"
                            >
                              {isExpanded ? "Hide" : "Show"} content
                            </button>
                          )}
                        </div>
                        {job.report_payload?.content && isExpanded && (
                          <div className="prose prose-xs max-w-none mt-2">
                            <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                              {job.report_payload.content}
                            </ReactMarkdown>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}

