/**
 * Kök Sayfa — /login'e yönlendirme
 * next/navigation'ın redirect() fonksiyonu Server Component'te çalışır,
 * client-side JS yüklenmeden hemen yönlendirme sağlar.
 */

import { redirect } from "next/navigation";

export default function RootPage() {
  redirect("/login");
}
