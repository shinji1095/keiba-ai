import React from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";

import { AppShell } from "./app/layout/AppShell";
import { RequireToken } from "./app/auth/RequireToken";
import { LoginPage } from "./features/auth/LoginPage";
import { RegisterPage } from "./features/auth/RegisterPage";
import { OverviewPage } from "./features/overview/OverviewPage";
import { VenuesPage } from "./features/venues/VenuesPage";
import { RacesPage } from "./features/races/RacesPage";
import { RaceDetailPage } from "./features/races/RaceDetailPage";
import { TodayRacesPage } from "./features/races/TodayRacesPage";
import { PastRacesPage } from "./features/races/PastRacesPage";
import { RaceResultsPage } from "./features/races/RaceResultsPage";
import { OAuthClientsPage } from "./features/admin/OAuthClientsPage";
import { ScrapeConsolePage } from "./features/scrape/ScrapeConsolePage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { TestDataPage } from "./features/testdata/TestDataPage";
import { NotFoundPage } from "./features/system/NotFoundPage";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    path: "/",
    element: (
      <RequireToken>
        <AppShell />
      </RequireToken>
    ),
    children: [
      { index: true, element: <OverviewPage /> },
      { path: "venues", element: <VenuesPage /> },
      { path: "races", element: <RacesPage /> },
      { path: "races/today", element: <TodayRacesPage /> },
      { path: "races/past", element: <PastRacesPage /> },
      { path: "races/:raceId", element: <RaceDetailPage /> },
      { path: "results", element: <RaceResultsPage /> },
      { path: "admin/oauth-clients", element: <OAuthClientsPage /> },
      { path: "scrape", element: <ScrapeConsolePage /> },
      { path: "test-data", element: <TestDataPage /> },
      { path: "settings", element: <SettingsPage /> },
    ],
  },
  { path: "/404", element: <NotFoundPage /> },
  { path: "*", element: <Navigate to="/404" replace /> },
]);
