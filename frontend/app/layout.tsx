export const metadata = {
  title: "Trestle",
  description: "Conversational personal assistant for startup founders",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
