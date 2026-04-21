'use client';

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const navItems = [
  { href: "/", label: "홈" },
  { href: "/projects", label: "라이브러리" },
  { href: "/admin", label: "관리" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname.startsWith(href);
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-inner">
          <Link href="/" className="brand-mark">
            <span className="logo-dot" />
            <span>
              <span className="brand-name">Killing Time</span>{" "}
              <span className="brand-sub">Studio</span>
            </span>
          </Link>
          <nav className="nav-primary">
            {navItems.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={active ? "nav-link nav-link--active" : "nav-link"}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </header>
      <main className="main">{children}</main>
    </div>
  );
}
