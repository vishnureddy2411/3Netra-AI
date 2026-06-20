// ─────────────────────────────────────────────
// Root layout — wraps entire app
// Handles auth state and redirects
// ─────────────────────────────────────────────

import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '3Netra-AI — Your AI Engineering Team',
  description: 'AI-powered project advisor for engineers',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0d1117] text-[#e6edf3] antialiased">
        {children}
      </body>
    </html>
  )
}