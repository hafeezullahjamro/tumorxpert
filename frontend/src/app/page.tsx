import { redirect } from "next/navigation";
import { cookies } from "next/headers";

export default function RootRedirect() {
  const cookieStore = cookies();
  const hasAuth = cookieStore.get("tx_auth")?.value === "1";
  const hasGuest = cookieStore.get("tx_guest")?.value === "1";

  if (hasAuth || hasGuest) {
    redirect("/dashboard");
  }
  redirect("/auth/login");
}
