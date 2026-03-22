import { Clock, Film, Tv, Users } from "lucide-react";

const CHART_BARS = [
  35, 52, 45, 68, 42, 72, 58, 40, 65, 48, 55, 70, 38, 62, 50,
  75, 44, 60, 46, 55, 68, 42, 58, 72, 48, 64, 52, 45, 70, 56,
];

const STAT_CARDS = [
  { icon: Film, label: "Total Movies" },
  { icon: Tv, label: "Total Series" },
  { icon: Users, label: "Active Users" },
  { icon: Clock, label: "Hours Watched" },
];

const TOP_WATCHED_WIDTHS = [85, 68, 52, 35];

export function DashboardPage() {
  return (
    <div className="p-4 md:p-8">
      <div className="mb-8">
        <h1 className="text-[#2a2520] text-2xl font-semibold mb-1">Welcome back</h1>
        <p className="text-[#2a2520]/60 text-sm">
          Your media statistics will appear here once data is synced
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {STAT_CARDS.map(({ icon: Icon, label }) => (
          <div
            key={label}
            className="bg-white/40 border border-[#c9b89a]/30 rounded-xl p-5 flex items-start gap-4"
          >
            <div className="w-10 h-10 rounded-lg bg-[#ffb826]/15 flex items-center justify-center shrink-0">
              <Icon size={20} className="text-[#ffb826]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[#2a2520]/50 text-xs font-medium mb-2">{label}</p>
              <div className="h-6 w-16 bg-[#2a2520]/6 rounded animate-pulse" />
            </div>
          </div>
        ))}
      </div>

      {/* Chart Placeholder */}
      <div className="bg-white/40 border border-[#c9b89a]/30 rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-[#2a2520] text-sm font-medium">Watch Activity</p>
            <p className="text-[#2a2520]/40 text-xs mt-0.5">Last 30 days</p>
          </div>
          <div className="h-7 w-24 bg-[#2a2520]/5 rounded-lg" />
        </div>
        <div className="flex items-end gap-1 md:gap-1.5 h-36 md:h-48">
          {CHART_BARS.map((height, i) => (
            <div
              key={i}
              className="flex-1 rounded-t bg-[#ffb826]/10"
              style={{ height: `${height}%` }}
            />
          ))}
        </div>
        <div className="flex justify-between mt-3">
          {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => (
            <span key={day} className="text-[#2a2520]/30 text-[10px]">
              {day}
            </span>
          ))}
        </div>
      </div>

      {/* Bottom Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Recent Activity */}
        <div className="bg-white/40 border border-[#c9b89a]/30 rounded-xl p-5">
          <p className="text-[#2a2520] text-sm font-medium mb-4">Recent Activity</p>
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-[#2a2520]/5 shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3 bg-[#2a2520]/6 rounded w-3/4 animate-pulse" />
                  <div className="h-2.5 bg-[#2a2520]/4 rounded w-1/2 animate-pulse" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Watched */}
        <div className="bg-white/40 border border-[#c9b89a]/30 rounded-xl p-5">
          <p className="text-[#2a2520] text-sm font-medium mb-4">Top Watched</p>
          <div className="space-y-3">
            {TOP_WATCHED_WIDTHS.map((width, i) => (
              <div key={i} className="flex items-center gap-3">
                <span className="w-5 text-right text-[#2a2520]/25 text-xs font-medium shrink-0">
                  {i + 1}
                </span>
                <div className="flex-1">
                  <div
                    className="h-3 bg-[#2a2520]/6 rounded mb-1.5 animate-pulse"
                    style={{ width: `${width}%` }}
                  />
                  <div
                    className="h-2 bg-[#ffb826]/8 rounded"
                    style={{ width: `${width}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
