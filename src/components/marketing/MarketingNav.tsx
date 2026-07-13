"use client";

import { ArrowRight, Menu, X } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import styles from "@/app/marketing.module.css";

const navItems = [
  { href: "/#how-it-works", label: "工作方式" },
  { href: "/#capabilities", label: "八种能力" },
  { href: "/#evidence", label: "证据方法" },
  { href: "/#security", label: "安全边界" },
  { href: "/#faq", label: "常见问题" },
] as const;

export function MarketingNav() {
  const [open, setOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const navRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        toggleRef.current?.focus();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = [
        toggleRef.current,
        ...Array.from(navRef.current?.querySelectorAll<HTMLElement>("a[href], button:not([disabled])") ?? []),
      ].filter((element): element is HTMLElement => element !== null);
      if (focusable.length === 0) return;
      const current = focusable.indexOf(document.activeElement as HTMLElement);
      const next = event.shiftKey
        ? (current <= 0 ? focusable.length - 1 : current - 1)
        : (current < 0 || current === focusable.length - 1 ? 0 : current + 1);
      event.preventDefault();
      focusable[next]?.focus();
    };

    const desktopQuery = window.matchMedia("(min-width: 861px)");
    const handleBreakpointChange = (event: MediaQueryListEvent) => {
      if (event.matches) setOpen(false);
    };
    const previousOverflow = document.body.style.overflow;
    if (desktopQuery.matches) {
      setOpen(false);
      return;
    }

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);
    desktopQuery.addEventListener("change", handleBreakpointChange);
    window.requestAnimationFrame(() => navRef.current?.querySelector<HTMLElement>("a[href]")?.focus());
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
      desktopQuery.removeEventListener("change", handleBreakpointChange);
    };
  }, [open]);

  const closeMenu = () => setOpen(false);
  const closeMenuAndRestoreFocus = () => {
    setOpen(false);
    window.requestAnimationFrame(() => toggleRef.current?.focus());
  };

  return (
    <header className={styles.marketingHeader}>
      <div className={styles.navInner}>
        <Link className={styles.marketingBrand} href="/" aria-label="Vibio SEO 首页" onClick={closeMenu}>
          <Image src="/vibio-logo.png" alt="" width={38} height={38} priority />
          <span>
            <strong>Vibio SEO</strong>
            <small>EVIDENCE WORKSPACE</small>
          </span>
        </Link>

        <button
          ref={toggleRef}
          className={styles.navToggle}
          type="button"
          aria-label={open ? "关闭导航" : "打开导航"}
          aria-expanded={open}
          aria-controls="marketing-navigation"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? <X size={21} /> : <Menu size={21} />}
        </button>

        <nav
          ref={navRef}
          id="marketing-navigation"
          className={`${styles.marketingNav}${open ? ` ${styles.marketingNavOpen}` : ""}`}
          aria-label="主导航"
        >
          <div className={styles.navLinks}>
            {navItems.map((item) => (
              <Link key={item.href} href={item.href} onClick={closeMenu}>
                {item.label}
              </Link>
            ))}
          </div>
          <Link className={styles.navCta} href="/workspace" onClick={closeMenu}>
            进入工作台
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
        </nav>
      </div>
      {open && (
        <button
          className={styles.navBackdrop}
          type="button"
          aria-label="关闭导航"
          tabIndex={-1}
          onClick={closeMenuAndRestoreFocus}
        />
      )}
    </header>
  );
}
