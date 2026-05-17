"use client";

import { useState } from "react";
import { Mail, MapPin } from "lucide-react";

export default function Contact() {
  const [sent, setSent] = useState(false);

  return (
    <section id="contact" className="mx-auto max-w-[1440px] px-6 py-20 md:px-8">
      <div className="grid gap-12 md:grid-cols-2">
        {/* Left */}
        <div className="flex flex-col gap-6">
          <h2 className="font-[family-name:var(--font-plus-jakarta)] text-3xl text-on-surface">
            Get in Touch
          </h2>
          <p className="max-w-sm text-sm leading-relaxed text-on-surface-variant">
            Ready to build your bridge to success? Our team of experts is here
            to help you navigate the world of AI agents and custom workflows.
          </p>

          <div className="flex flex-col gap-4 pt-4">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary-container">
                <Mail className="h-4 w-4 text-on-secondary-container" />
              </div>
              <div className="text-sm">
                <p className="font-medium text-on-surface">Email Us</p>
                <p className="text-on-surface-variant">hello@trestle.ai</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary-container">
                <MapPin className="h-4 w-4 text-on-secondary-container" />
              </div>
              <div className="text-sm">
                <p className="font-medium text-on-surface">Head Office</p>
                <p className="text-on-surface-variant">Detroit, Michigan</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right: form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setSent(true);
            setTimeout(() => setSent(false), 3000);
          }}
          className="flex flex-col gap-4 rounded-[1.5rem] bg-surface-container p-6 md:p-8"
        >
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-on-surface">Name</label>
            <input
              type="text"
              placeholder="Your Name"
              className="rounded-[1rem] bg-surface-high px-4 py-3 text-sm outline-none ring-1 ring-outline-variant transition placeholder:text-on-surface-variant/50 focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-on-surface">Email</label>
            <input
              type="email"
              placeholder="your@email.com"
              className="rounded-[1rem] bg-surface-high px-4 py-3 text-sm outline-none ring-1 ring-outline-variant transition placeholder:text-on-surface-variant/50 focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-on-surface">Message</label>
            <textarea
              rows={4}
              placeholder="How can we help?"
              className="rounded-[1rem] bg-surface-high px-4 py-3 text-sm outline-none ring-1 ring-outline-variant transition placeholder:text-on-surface-variant/50 focus:ring-2 focus:ring-primary"
            />
          </div>
          <button
            type="submit"
            className="mt-2 w-full rounded-full bg-primary py-3 text-sm font-medium text-on-primary transition hover:bg-primary-container hover:text-primary"
          >
            {sent ? "Message Sent!" : "Send Message"}
          </button>
        </form>
      </div>
    </section>
  );
}
