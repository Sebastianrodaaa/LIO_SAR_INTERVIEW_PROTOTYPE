"use client";

import { useEffect, useState } from "react";

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduced(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);
  return reduced;
}

export function Typewriter({
  text,
  className,
}: {
  text: string;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const [shown, setShown] = useState(reduced ? text.length : 0);

  useEffect(() => {
    if (reduced) {
      setShown(text.length);
      return;
    }
    setShown(0);
    const step = Math.max(1, Math.ceil(text.length / 90));
    const timer = window.setInterval(() => {
      setShown((n) => {
        const next = n + step;
        if (next >= text.length) {
          window.clearInterval(timer);
          return text.length;
        }
        return next;
      });
    }, 16);
    return () => window.clearInterval(timer);
  }, [text, reduced]);

  return <p className={className}>{text.slice(0, shown)}</p>;
}

export function NumberTicker({
  value,
  className,
}: {
  value: number;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const [current, setCurrent] = useState(reduced ? value : 0);

  useEffect(() => {
    if (reduced) {
      setCurrent(value);
      return;
    }
    const start = performance.now();
    const from = 0;
    const duration = 500;
    let frame = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - (1 - t) * (1 - t);
      setCurrent(Math.round(from + (value - from) * eased));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value, reduced]);

  return (
    <span className={`tabular-nums ${className ?? ""}`}>
      {current.toLocaleString()}
    </span>
  );
}
