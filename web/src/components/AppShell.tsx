'use client';

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const navItems = [
  { href: "/", label: "Overview" },
  { href: "/orchestra", label: "Orchestra" },
  { href: "/harness", label: "Harness" },
  { href: "/registry", label: "Registry" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="eyebrow">Orchestra-First Subtitle Lab</div>
          <h1>Killing Time</h1>
          <p>
            중국어 원문 자막 확보부터 한국어·스페인어 패키징까지, 오케스트라가 하네스를
            총괄하는 로컬 워크스페이스입니다.
          </p>
        </div>
        <nav className="nav">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link key={item.href} href={item.href} className={active ? "nav-link nav-link--active" : "nav-link"}>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className="main">{children}</main>
    </div>
  );
}

