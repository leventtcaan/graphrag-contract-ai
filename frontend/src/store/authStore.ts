/**
 * Zustand Auth Store
 * JWT token'ını hem React state'inde hem de localStorage'da tutar.
 * persist middleware ile sayfa yenilemelerinde oturum korunur.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  /** Token'ı hem state'e hem localStorage'a yazar */
  setToken: (token: string) => void;
  /** Oturumu tamamen temizler */
  logout: () => void;
}

const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      isAuthenticated: false,

      setToken: (token) =>
        set({
          token,
          isAuthenticated: true,
        }),

      logout: () => {
        // Zustand state'ini sıfırla — persist middleware localStorage'ı da temizler
        set({ token: null, isAuthenticated: false });
      },
    }),
    {
      name: "token", // localStorage anahtarı: "token"
      // Sadece token'ı persist et, isAuthenticated token'dan türetiliyor
      partialize: (state) => ({ token: state.token }),
      // Sayfa yüklendiğinde token varsa isAuthenticated'ı true yap
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          state.isAuthenticated = true;
        }
      },
    }
  )
);

export default useAuthStore;
