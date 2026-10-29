"use client";

import { useEffect } from "react";

export function SentryInit() {
  useEffect(() => {
    const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN?.trim();
    if (!dsn) {
      return;
    }
    let active = true;
    void import("@sentry/browser").then((Sentry) => {
      if (!active) {
        return;
      }
      Sentry.init({
        dsn,
        tracesSampleRate: 0,
        sendDefaultPii: false,
      });
    });
    return () => {
      active = false;
    };
  }, []);

  return null;
}
