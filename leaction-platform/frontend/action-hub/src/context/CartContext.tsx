"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
  Dispatch,
  SetStateAction,
} from "react";

type CartItem = {
  id: string | number;
  [key: string]: unknown;
};

type CartContextType = {
  cartItems: CartItem[];
  /** True after the initial read from localStorage (avoids false cart transitions on hydrate). */
  cartHydrated: boolean;
  addToCart: (product: CartItem) => void;
  removeFromCart: (id: string | number) => void;
  setCartItems: Dispatch<SetStateAction<CartItem[]>>;
};

const CART_STORAGE_KEY = "cartItems";

const CartContext = createContext<CartContextType | undefined>(undefined);

type CartProviderProps = {
  children: ReactNode;
};

export function CartProvider({ children }: CartProviderProps) {
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [cartHydrated, setCartHydrated] = useState(false);

  useEffect(() => {
    try {
      const storedCart = localStorage.getItem(CART_STORAGE_KEY);

      if (storedCart) {
        const parsedCart = JSON.parse(storedCart);

        if (Array.isArray(parsedCart)) {
          setCartItems(parsedCart as CartItem[]);
        }
      }
    } catch (error) {
      console.error("Error loading cart from localStorage:", error);
    } finally {
      setCartHydrated(true);
    }
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cartItems));
    } catch (error) {
      console.error("Error saving cart to localStorage:", error);
    }
  }, [cartItems]);

  const addToCart = (product: CartItem) => {
    setCartItems((prevItems) => {
      const itemAlreadyExists = prevItems.some((item) => item.id === product.id);

      if (itemAlreadyExists) {
        return prevItems;
      }

      return [...prevItems, product];
    });
  };

  const removeFromCart = (id: string | number) => {
    setCartItems((prevItems) => prevItems.filter((item) => item.id !== id));
  };

  return (
    <CartContext.Provider
      value={{ cartItems, cartHydrated, addToCart, removeFromCart, setCartItems }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart() {
  const context = useContext(CartContext);

  if (!context) {
    throw new Error("useCart must be used within a CartProvider");
  }

  return context;
}
