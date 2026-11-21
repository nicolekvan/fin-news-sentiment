"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const [light, setLight] = useState(false);

  useEffect(() => {
    setLight(document.documentElement.dataset.theme === "light");
  }, []);

  function toggle() {
    const next = !light;
    setLight(next);
    if (next) document.documentElement.dataset.theme = "light";
    else delete document.documentElement.dataset.theme;
    try {
      localStorage.setItem("ml-theme", next ? "light" : "dark");
    } catch {
      /* storage unavailable: theme still switches for this visit */
    }
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggle}
      aria-label={light ? "Switch to dark theme" : "Switch to light theme"}
    >
      {light ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
    </Button>
  );
}

/** Runs before paint so a saved light preference doesn't flash dark. */
export const themeScript = `try{if(localStorage.getItem("ml-theme")==="light")document.documentElement.dataset.theme="light"}catch(e){}`;
