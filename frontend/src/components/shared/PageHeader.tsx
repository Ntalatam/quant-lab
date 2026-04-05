import type { ReactNode } from "react";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: ReactNode;
  meta?: ReactNode;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  meta,
}: PageHeaderProps) {
  return (
    <section className="panel-hero panel-grid mb-8 px-6 py-6 lg:px-8 lg:py-7">
      <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-3xl">
          {eyebrow ? <div className="page-kicker mb-4">{eyebrow}</div> : null}
          <h1 className="display-title text-4xl text-text-primary lg:text-5xl">
            {title}
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-text-secondary lg:text-[15px]">
            {description}
          </p>
          {meta ? (
            <div className="mt-5 flex flex-wrap gap-2">{meta}</div>
          ) : null}
        </div>
        {actions ? (
          <div className="relative z-10 shrink-0">{actions}</div>
        ) : null}
      </div>
    </section>
  );
}
