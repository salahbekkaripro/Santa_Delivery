import { RegisterForm } from "@/components/register-form";

export default function RegisterPage({ searchParams }: { searchParams?: { redirect?: string } }) {
  return <RegisterForm redirectTo={searchParams?.redirect} />;
}
