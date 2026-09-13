import { Routes } from "@angular/router";
import { authGuard } from "./core/guards/auth.guard";

export const routes: Routes = [
  { path: "", pathMatch: "full", redirectTo: "dashboard" },
  {
    path: "login",
    loadComponent: () =>
      import("./features/auth/login/login.component").then(
        (m) => m.LoginComponent,
      ),
  },
  {
    path: "register",
    loadComponent: () =>
      import("./features/auth/register/register.component").then(
        (m) => m.RegisterComponent,
      ),
  },
  {
    path: "dashboard",
    canActivate: [authGuard],
    loadComponent: () =>
      import("./features/dashboard/dashboard.component").then(
        (m) => m.DashboardComponent,
      ),
  },
  {
    path: "videos",
    canActivate: [authGuard],
    loadComponent: () =>
      import("./features/videos/my-videos.component").then(
        (m) => m.MyVideosComponent,
      ),
  },
  {
    path: "videos/:id",
    canActivate: [authGuard],
    loadComponent: () =>
      import("./features/videos/video-details.component").then(
        (m) => m.VideoDetailsComponent,
      ),
  },
  { path: "**", redirectTo: "dashboard" },
];
