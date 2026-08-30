import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import Nav from "@/components/Nav";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "RailPredict AI — Dynamic ETA Forecasting",
  description:
    "Real-time AI-powered ETA predictions for Indian coaching trains. Physics + ML ensemble with SHAP explainability.",
  keywords: ["Indian Railways", "train ETA", "train prediction", "delay forecast"],
  openGraph: {
    title: "RailPredict AI",
    description: "Dynamic ETA forecasting for Indian coaching trains",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <Providers>
          <Nav />
          {children}
        </Providers>
      </body>
    </html>
  );
}
