import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "RailPredict AI — Dynamic ETA Forecasting for Indian Railways",
  description:
    "AI-powered real-time ETA predictions for Indian coaching trains. Built for SIH 2026 problem statement SIH26028 by the Ministry of Railways.",
  keywords: [
    "Indian Railways",
    "train ETA",
    "delay prediction",
    "AI forecasting",
    "SIH 2026",
    "NTES",
  ],
  openGraph: {
    title: "RailPredict AI",
    description: "Dynamic ETA Forecasting for Indian Coaching Trains",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
