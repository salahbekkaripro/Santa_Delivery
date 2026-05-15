"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export type DebriefChartDatum = {
  metric: string;
  methodA: number;
  methodB: number;
  unit?: string;
};

type DebriefPerformanceChartProps = {
  data: DebriefChartDatum[];
  methodALabel?: string;
  methodBLabel?: string;
  height?: number;
};

function formatValue(value: number, unit?: string) {
  const rounded = Math.abs(value) >= 100 ? Math.round(value) : Number(value.toFixed(2));
  return unit ? `${rounded} ${unit}` : String(rounded);
}

export function DebriefPerformanceChart({
  data,
  methodALabel = "Méthode A",
  methodBLabel = "Méthode B",
  height = 280,
}: DebriefPerformanceChartProps) {
  const chartData = data.map((row) => ({
    ...row,
    [methodALabel]: row.methodA,
    [methodBLabel]: row.methodB,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 16, right: 24, left: 8, bottom: 6 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="metric" />
        <YAxis />
        <Tooltip
          formatter={(value, key, payload) => {
            const row = payload?.payload as DebriefChartDatum | undefined;
            return [formatValue(Number(value), row?.unit), key];
          }}
          labelFormatter={(label) => `Indicateur: ${label}`}
          contentStyle={{
            borderRadius: 12,
            border: "1px solid rgba(18, 50, 71, 0.16)",
          }}
        />
        <Legend />
        <Bar dataKey={methodALabel} fill="#9e2f3f" radius={[4, 4, 0, 0]} />
        <Bar dataKey={methodBLabel} fill="#17324d" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
