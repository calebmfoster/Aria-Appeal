import { SessionExpiredModal } from "@/components/auth/SessionExpiredModal";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {children}
      <SessionExpiredModal />
    </>
  );
}
