import { Menu } from "lucide-react";
import { useState } from "react";
import { Outlet } from "react-router-dom";
import Drawer from "@/components/common/Drawer";
import ThemeToggle from "@/components/common/ThemeToggle";
import AppSidebar from "./AppSidebar";
import ProfileMenu from "./ProfileMenu";

export default function AppLayout() {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-bg">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 shrink-0 border-r border-line lg:block">
        <AppSidebar />
      </aside>

      {/* Main column */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-line bg-bg/70 px-4 backdrop-blur">
          <button
            onClick={() => setDrawerOpen(true)}
            className="rounded-lg p-2 text-muted transition hover:bg-card2 lg:hidden"
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>
          <div className="lg:hidden">
            <span className="text-sm font-semibold text-content">Document AI</span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <ProfileMenu />
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>

      {/* Mobile drawer */}
      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} side="left" ariaLabel="Navigation">
        <AppSidebar onNavigate={() => setDrawerOpen(false)} />
      </Drawer>
    </div>
  );
}
