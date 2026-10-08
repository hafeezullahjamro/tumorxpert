"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { AppToaster } from "./toaster";
import { useSettingsStore } from "../lib/store";
import { GuestModeContext } from "../lib/auth";

interface ProvidersProps {
  children: ReactNode;
  isGuest: boolean;
}

export function Providers({ children, isGuest }: ProvidersProps) {
  const [queryClient] = useState(() => new QueryClient());
  useEffect(() => {
    void useSettingsStore.persist.rehydrate();
  }, []);
  return (
    <QueryClientProvider client={queryClient}>
      <GuestModeContext.Provider value={isGuest}>
        {children}
        <AppToaster />
      </GuestModeContext.Provider>
    </QueryClientProvider>
  );
}
