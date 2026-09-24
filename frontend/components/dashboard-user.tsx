"use client";

import { createContext, ReactNode, useContext } from "react";
import { User } from "@/lib/dashboard";

const DashboardUserContext = createContext<User | null>(null);

export function DashboardUserProvider({ children, user }: { children: ReactNode; user: User }) {
  return <DashboardUserContext.Provider value={user}>{children}</DashboardUserContext.Provider>;
}

export function useDashboardUser() {
  const user = useContext(DashboardUserContext);
  if (!user) throw new Error("Dashboard user is not loaded");
  return user;
}
