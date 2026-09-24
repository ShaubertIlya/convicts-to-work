import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Еңбек — цифровая платформа трудоустройства",
  description: "Прозрачный процесс трудоустройства и заключения договоров",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
