/**
 * Axios API İstemcisi
 * Backend FastAPI (http://localhost:8000/api/v1) ile iletişim kurar.
 * Tüm isteklere JWT token'ı otomatik olarak Authorization header'ına ekler.
 */

import axios from "axios";

// Temel Axios instance'ı — baseURL backend adresine sabitlenmiş
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// İstek interceptor'ı: her istekten önce localStorage'dan token'ı okuyup ekler
api.interceptors.request.use((config) => {
  // Tarayıcı ortamında localStorage erişimi güvenli; SSR sırasında atlanır
  if (typeof window !== "undefined") {
    // Zustand persist middleware, localStorage'a ham string değil şu yapıyı yazar:
    // { "state": { "token": "eyJ..." }, "version": 0 }
    // Bu yüzden JSON.parse ile iç token'ı çıkarmak gerekiyor.
    try {
      const raw = localStorage.getItem("token");
      const token = raw ? (JSON.parse(raw) as { state?: { token?: string } })?.state?.token : null;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch {
      // Bozuk localStorage verisi — sessizce atla
    }
  }
  return config;
});

// Yanıt interceptor'ı: 401 hatalarında kullanıcıyı login sayfasına yönlendir
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (typeof window !== "undefined" && error.response?.status === 401) {
      // Token süresi dolmuş veya geçersiz — oturumu temizle
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
