"use client";

import { useEffect, useState } from "react";

type DesktopApi = {
  close: () => Promise<void> | void;
  minimize: () => Promise<void> | void;
  zoom: () => Promise<void> | void;
};

declare global {
  interface Window {
    pywebview?: { api?: DesktopApi };
  }
}

function desktopApi(): DesktopApi | null {
  if (typeof window === "undefined") return null;
  return window.pywebview?.api ?? null;
}

export function WindowControls() {
  const hit = (action: keyof DesktopApi) => {
    const api = desktopApi();
    if (!api) return;
    void api[action]();
  };

  return (
    <div className="no-drag flex w-[68px] items-center gap-2">
      <button
        type="button"
        aria-label="Close"
        onClick={() => hit("close")}
        className="h-3 w-3 rounded-full bg-[#FF5F57] hover:brightness-95"
      />
      <button
        type="button"
        aria-label="Minimize"
        onClick={() => hit("minimize")}
        className="h-3 w-3 rounded-full bg-[#FEBC2E] hover:brightness-95"
      />
      <button
        type="button"
        aria-label="Zoom"
        onClick={() => hit("zoom")}
        className="h-3 w-3 rounded-full bg-[#28C840] hover:brightness-95"
      />
    </div>
  );
}

export function useDesktopShell(): boolean {
  const [desktop, setDesktop] = useState(false);
  useEffect(() => {
    const mark = () => setDesktop(true);
    if (window.pywebview) mark();
    window.addEventListener("pywebviewready", mark);
    return () => window.removeEventListener("pywebviewready", mark);
  }, []);
  return desktop;
}
