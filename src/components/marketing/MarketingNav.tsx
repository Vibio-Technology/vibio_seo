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

  useEffect(() => {
    if (!open) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      toggleRef.current?.focus();
    };

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const closeMenu = () => setOpen(false);

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
          onClick={closeMenu}
        />
      )}
    </header>
  );
}
