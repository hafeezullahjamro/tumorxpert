import type { ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./card";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: ReactNode;
  actions?: ReactNode;
}

export function EmptyState({ title, description, icon, actions }: EmptyStateProps) {
  return (
    <Card className="border-dashed border-slate-300/90 bg-white/76">
      <CardHeader className="items-start">
        {icon ? <div className="rounded-xl bg-accent/70 p-2 text-primary">{icon}</div> : null}
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      {actions ? <CardContent className="flex flex-wrap gap-3">{actions}</CardContent> : null}
    </Card>
  );
}
