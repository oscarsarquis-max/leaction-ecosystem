"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ShoppingCart } from "lucide-react";
import { useCart } from "@/context/CartContext";
import { ActionHubBrandHeader } from "@/components/ActionHubBrandHeader";

function CartLinkInner({
  href,
  isAnonymous,
}: {
  href: string;
  /** Sem `?email=` na URL — animação chama atenção ao primeiro item. */
  isAnonymous: boolean;
}) {
  const { cartItems, cartHydrated } = useCart();
  const count = cartItems.length;
  const prevCountRef = useRef<number | null>(null);
  const [pulseCart, setPulseCart] = useState(false);

  useEffect(() => {
    if (!cartHydrated) return;
    const prev = prevCountRef.current;
    if (prev === null) {
      prevCountRef.current = count;
      return;
    }
    if (
      isAnonymous &&
      prev === 0 &&
      count === 1 &&
      typeof window !== "undefined" &&
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ) {
      setPulseCart(true);
    }
    prevCountRef.current = count;
  }, [count, isAnonymous, cartHydrated]);

  useEffect(() => {
    if (!pulseCart) return;
    const t = window.setTimeout(() => setPulseCart(false), 2000);
    return () => window.clearTimeout(t);
  }, [pulseCart]);

  return (
    <Link
      href={href}
      className="relative inline-flex items-center justify-center rounded-lg p-2 text-orange-200 transition hover:bg-white/10 hover:text-white"
      aria-label="Ir para o carrinho"
    >
      <span className={`inline-flex ${pulseCart ? "animate-cart-pulse" : ""}`}>
        <ShoppingCart className="size-6" />
      </span>
      {count > 0 && (
        <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-orange-500 px-1 text-[10px] font-bold leading-none text-white">
          {count > 99 ? "99+" : count}
        </span>
      )}
    </Link>
  );
}

function CartLinkWithEmailFromUrl() {
  const searchParams = useSearchParams();
  const { href, isAnonymous } = useMemo(() => {
    const email = searchParams.get("email")?.trim();
    if (email) {
      return {
        href: `/dashboard?email=${encodeURIComponent(email)}`,
        isAnonymous: false,
      };
    }
    return { href: "/dashboard", isAnonymous: true };
  }, [searchParams]);

  return <CartLinkInner href={href} isAnonymous={isAnonymous} />;
}

export function Header() {
  return (
    <ActionHubBrandHeader
      left={
        <Suspense fallback={<CartLinkInner href="/dashboard" isAnonymous />}>
          <CartLinkWithEmailFromUrl />
        </Suspense>
      }
    />
  );
}
