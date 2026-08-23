export const metadata = {
  title: "RedSite AI — Mars Site Intelligence",
  description: "AI-powered decision engine for selecting safe and resource-rich human landing sites on Mars",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, fontFamily: "system-ui, -apple-system, sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
