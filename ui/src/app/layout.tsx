import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Sidebar } from "@/components/sidebar";
import { I18nProvider } from "@/lib/i18n";

import "./globals.css";

export const metadata: Metadata = {
  title: "deer-rag 检索界面",
  description: "用于管理集合、摄入内容、执行检索和查看实验结果的本地操作界面。",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body>
        <I18nProvider>
          <div className="mx-auto flex min-h-screen max-w-[1700px] flex-col gap-4 p-4 md:gap-6 md:p-6 lg:flex-row">
            <Sidebar />
            <main className="flex-1">
              <div className="surface-card min-h-[calc(100vh-2rem)] overflow-hidden md:min-h-[calc(100vh-3rem)]">
                <div className="h-full bg-[linear-gradient(180deg,rgba(255,255,255,0.46),transparent_220px)] p-4 md:p-6">
                  {children}
                </div>
              </div>
            </main>
          </div>
        </I18nProvider>
      </body>
    </html>
  );
}
