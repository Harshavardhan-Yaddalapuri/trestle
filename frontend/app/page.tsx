"use client";

import Link from "next/link";

/* ─── Page sections ─── */
import Nav from "./_sections/Nav";
import Hero from "./_sections/Hero";
import Features from "./_sections/Features";
import Pricing from "./_sections/Pricing";
import Contact from "./_sections/Contact";
import Footer from "./_sections/Footer";

export default function HomePage() {
  return (
    <>
      <Nav />
      <main className="flex flex-col gap-0">
        <Hero />
        <Features />
        <Pricing />
        <Contact />
      </main>
      <Footer />
    </>
  );
}
