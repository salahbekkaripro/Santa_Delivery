import { LoginForm } from "@/components/login-form";

export default function LoginPage({ searchParams }: { searchParams?: { redirect?: string } }) {
  return <LoginForm redirectTo={searchParams?.redirect} />;
}
