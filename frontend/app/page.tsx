"use client";

import Nav from "./_sections/Nav";
import Hero from "./_sections/Hero";
import Features from "./_sections/Features";
import SocialProof from "./_sections/SocialProof";
import MobileNav from "./_sections/MobileNav";

export default function HomePage() {
  return (
    <>
      <Nav />
      <main className="pt-24 pb-12">
        <Hero />
        <Features />
        <SocialProof />
      </main>
      <MobileNav />
    </>
  );
}
