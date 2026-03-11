import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/sidebar";
import Header from "@/components/header";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "AirPredict | Delhi AQI Dashboard",
  description: "Real-time Air Quality Index monitoring and predictions for Delhi.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased bg-gray-50 text-gray-900 min-h-screen`}>
        <Sidebar />
        <div className="ml-64 flex flex-col min-h-screen">
          <Header />
          <main className="flex-1 p-8">
            <div className="max-w-7xl mx-auto">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
